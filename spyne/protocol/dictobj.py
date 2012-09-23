
#
# spyne - Copyright (C) Spyne contributors.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301
#

"""The ``spyne.protocol.dictobj.DictObject`` module contains an abstract
protocol that deals with hierarchical dicts as {in,out}_documents.
"""

import logging
logger = logging.getLogger(__name__)

from spyne.error import ValidationError

from spyne.model.binary import ByteArray
from spyne.model.binary import File
from spyne.model.fault import Fault
from spyne.model.complex import ComplexModelBase
from spyne.model.complex import Array
from spyne.model.primitive import DateTime
from spyne.model.primitive import Decimal
from spyne.model.primitive import String
from spyne.model.primitive import Unicode

from spyne.protocol import ProtocolBase
from spyne.protocol._base import unwrap_messages


def _unwrap_dict(d, skip_depth):
    for _ in range(skip_depth):
        print d
        if isinstance(d, dict) and len(d) == 1:
            d, = d.values()
        else:
            break
    return d


class DictObject(ProtocolBase):
    """An abstract protocol that uses dicts as input and output documents.

    Implement ``create_in_document`` and ``create_out_string`` to use this.
    """

    def create_in_document(self, ctx, in_string_encoding=None):
        raise NotImplementedError()

    def create_out_string(self, ctx, out_string_encoding='utf8'):
        raise NotImplementedError()

    def set_validator(self, validator):
        """Sets the validator for the protocol.

        :param validator: one of ('soft', None)
        """

        if validator == 'soft' or validator is self.SOFT_VALIDATION:
            self.validator = self.SOFT_VALIDATION
        elif validator is None:
            self.validator = None
        else:
            raise ValueError(validator)

    def decompose_incoming_envelope(self, ctx, message):
        """Sets ``ctx.in_body_doc``, ``ctx.in_header_doc`` and
        ``ctx.method_request_string`` using ``ctx.in_document``.
        """

        assert message in (ProtocolBase.REQUEST, ProtocolBase.RESPONSE)

        # set ctx.in_header
        ctx.transport.in_header_doc = None # use an rpc protocol if you want headers.

        doc = ctx.in_document

        ctx.in_header_doc = None
        ctx.in_body_doc = doc

        if len(doc) == 0:
            raise Fault("Client", "Empty request")

        # set ctx.method_request_string
        ctx.method_request_string = '{%s}%s' % (self.app.interface.get_tns(),
                                                                doc.keys()[0])

        logger.debug('\theader : %r' % (ctx.in_header_doc))
        logger.debug('\tbody   : %r' % (ctx.in_body_doc))

    def _doc_to_object(self, cls, doc):
        if doc is None:
            return []

        if issubclass(cls, Array):
            retval = [ ]
            (serializer,) = cls._type_info.values()

            for child in doc:
                retval.append(self._from_dict_value(serializer, child))

            return retval

        inst = cls.get_deserialization_instance()

        # get all class attributes, including the ones coming from parent classes.
        flat_type_info = cls.get_flat_type_info(cls)

        # initialize instance
        for k in flat_type_info:
            setattr(inst, k, None)

        # this is for validating cls.Attributes.{min,max}_occurs
        frequencies = {}

        try:
            items = doc.items()
        except AttributeError:
            items = zip(cls._type_info.keys(), doc)

        # parse input to set incoming data to related attributes.
        for k,v in items:
            freq = frequencies.get(k, 0)
            freq += 1
            frequencies[k] = freq

            member = flat_type_info.get(k, None)
            if member is None:
                continue

            mo = member.Attributes.max_occurs
            if mo > 1:
                value = getattr(inst, k, None)
                if value is None:
                    value = []

                for a in v:
                    value.append(self._from_dict_value(member, a))

            else:
                value = self._from_dict_value(member, v)

            setattr(inst, k, value)

        if self.validator is self.SOFT_VALIDATION:
            for k, v in flat_type_info.items():
                val = frequencies.get(k, 0)
                if (val < v.Attributes.min_occurs or val > v.Attributes.max_occurs):
                    raise Fault('Client.ValidationError',
                        '%r member does not respect frequency constraints.' % k)

        return inst

    def deserialize(self, ctx, message):
        assert message in (self.REQUEST, self.RESPONSE)

        self.event_manager.fire_event('before_deserialize', ctx)

        if ctx.descriptor is None:
            raise Fault("Client", "Method %r not found." %
                                                      ctx.method_request_string)

        # instantiate the result message
        if message is self.REQUEST:
            body_class = unwrap_messages(ctx.descriptor.in_message,
                                                                self.skip_depth)
        elif message is self.RESPONSE:
            body_class = unwrap_messages(ctx.descriptor.out_message,
                                                                self.skip_depth)
        if body_class:
            # assign raw result to its wrapper, result_message
            result_message_class = ctx.descriptor.in_message
            value = ctx.in_body_doc.get(result_message_class.get_type_name(), None)
            result_message = self._doc_to_object(result_message_class, value)

            ctx.in_object = result_message

        else:
            ctx.in_object = []

        self.event_manager.fire_event('after_deserialize', ctx)

    def serialize(self, ctx, message):
        assert message in (self.REQUEST, self.RESPONSE)

        self.event_manager.fire_event('before_serialize', ctx)

        if ctx.out_error is not None:
            ctx.out_document = [ctx.out_error.to_dict(ctx.out_error)]

        else:
            # get the result message
            if message is self.REQUEST:
                out_type = ctx.descriptor.in_message
            elif message is self.RESPONSE:
                out_type = ctx.descriptor.out_message
            if out_type is None:
                return

            out_type_info = out_type._type_info

            # instantiate the result message
            out_instance = out_type()

            # assign raw result to its wrapper, result_message
            for i in range(len(out_type_info)):
                attr_name = out_type_info.keys()[i]
                setattr(out_instance, attr_name, ctx.out_object[i])

            # arrays get wrapped in [], whereas other objects get wrapped in
            # {object_name: ...}
            wrapper_name = None
            if not issubclass(out_type, Array):
                wrapper_name = out_type.get_type_name()

            # serialize the results
            if out_type.Attributes.max_occurs > 1:
                ctx.out_document = (_unwrap_dict(self._to_value(out_type,
                                        inst, wrapper_name), self.skip_depth)
                                                       for inst in out_instance)
            else:
                ctx.out_document = [_unwrap_dict(self._to_value(out_type,
                                out_instance, wrapper_name), self.skip_depth)]

            self.event_manager.fire_event('after_serialize', ctx)

    def _from_dict_value(self, cls, value):
        # validate raw input
        if self.validator is self.SOFT_VALIDATION:
            if issubclass(cls, Unicode) and not isinstance(value, unicode):
                if not (issubclass(cls, String) and isinstance(value, str)):
                    raise ValidationError(value)

            elif issubclass(cls, Decimal) and not isinstance(value, (int, long, float)):
                raise ValidationError(value)

            elif issubclass(cls, DateTime) and not (isinstance(value, unicode) and
                                            cls.validate_string(cls, value)):
                raise ValidationError(value)

        # get native type
        if issubclass(cls, ComplexModelBase):
            retval = self._doc_to_object(cls, value)

        elif issubclass(cls, DateTime):
            retval = cls.from_string(value)

        else:
            retval = value

        # validate native type
        if self.validator is self.SOFT_VALIDATION and \
                not cls.validate_native(cls, retval):
            raise ValidationError(retval)

        return retval

    def _get_member_pairs(self, cls, inst):
        parent_cls = getattr(cls, '__extends__', None)
        if not (parent_cls is None):
            for r in self._get_member_pairs(parent_cls, inst):
                yield r

        for k, v in cls._type_info.items():
            try:
                sub_value = getattr(inst, k, None)
            except Exception, e: # to guard against e.g. sqlalchemy throwing NoSuchColumnError
                logger.error("Error getting %r: %r" %(k,e))
                sub_value = None

            if v.Attributes.max_occurs > 1:
                if sub_value != None:
                    yield (k, [self._to_value(v,sv) for sv in sub_value])

            else:
                yield (k, self._to_value(v, sub_value))

    def _to_value(self, cls, value, k=None):
        if issubclass(cls, ComplexModelBase):
            return self._to_dict(cls, value, k)

        if issubclass(cls, DateTime):
            return cls.to_string(value)

        if issubclass(cls, Decimal):
            if cls.Attributes.format is None:
                return value
            else:
                return cls.to_string(value)

        return value

    def _to_dict(self, cls, inst, field_name=None):
        inst = cls.get_serialization_instance(inst)

        retval = dict(self._get_member_pairs(cls, inst))
        if field_name is None:
            return retval
        else:
            return {field_name: retval}

    def flat_dict_to_object(self, doc, inst_class):
        """Converts a flat dict to a native python object.

        See :func:`spyne.model.complex.ComplexModelBase.get_flat_type_info`.
        """

        simple_type_info = inst_class.get_simple_type_info(inst_class)
        inst = inst_class.get_deserialization_instance()

        # this is for validating cls.Attributes.{min,max}_occurs
        frequencies = {}

        for k, v in doc.items():
            member = simple_type_info.get(k, None)
            if member is None:
                logger.debug("discarding field %r" % k)
                continue

            mo = member.type.Attributes.max_occurs
            value = getattr(inst, k, None)
            if value is None:
                value = []

            # extract native values from the list of strings that comes from the
            # http dict.
            for v2 in v:
                if (self.validator is self.SOFT_VALIDATION and not
                            member.type.validate_string(member.type, v2)):
                    raise ValidationError(v2)

                if issubclass(member.type, (File, ByteArray)):
                    if isinstance(v2, str) or isinstance(v2, unicode):
                        native_v2 = member.type.from_string(v2)
                    else:
                        native_v2 = v2
                else:
                    native_v2 = member.type.from_string(v2)

                if (self.validator is self.SOFT_VALIDATION and not
                            member.type.validate_native(member.type, native_v2)):
                    raise ValidationError(v2)

                value.append(native_v2)

                # set frequencies of parents.
                if not (member.path[:-1] in frequencies):
                    for i in range(1,len(member.path)):
                        logger.debug("\tset freq %r = 1" % (member.path[:i],))
                        frequencies[member.path[:i]] = 1

                freq = frequencies.get(member.path, 0)
                freq += 1
                frequencies[member.path] = freq
                logger.debug("\tset freq %r = %d" % (member.path, freq))

            if mo == 1:
                value = value[0]

            # assign the native value to the relevant class in the nested object
            # structure.
            cinst = inst
            ctype_info = inst_class.get_flat_type_info(inst_class)
            pkey = member.path[0]
            for i in range(len(member.path) - 1):
                pkey = member.path[i]
                if not (ctype_info[pkey].Attributes.max_occurs in (0,1)):
                    raise Exception("non-primitives with max_occurs > 1 are not"
                                    "supported")

                ninst = getattr(cinst, pkey, None)
                if ninst is None:
                    ninst = ctype_info[pkey].get_deserialization_instance()
                    setattr(cinst, pkey, ninst)
                cinst = ninst

                ctype_info = ctype_info[pkey]._type_info

            if isinstance(cinst, list):
                cinst.extend(value)
                logger.debug("\tset array   %r(%r) = %r" %
                                                    (member.path, pkey, value))
            else:
                setattr(cinst, member.path[-1], value)
                logger.debug("\tset default %r(%r) = %r" %
                                                    (member.path, pkey, value))

        if self.validator is self.SOFT_VALIDATION:
            sti = simple_type_info.values()
            sti.sort(key=lambda x: (len(x.path), x.path))
            pfrag = None
            for s in sti:
                if len(s.path) > 1 and pfrag != s.path[:-1]:
                    pfrag = s.path[:-1]
                    ctype_info = inst_class.get_flat_type_info(inst_class)
                    for i in range(len(pfrag)):
                        f = pfrag[i]
                        ntype_info = ctype_info[f]

                        min_o = ctype_info[f].Attributes.min_occurs
                        max_o = ctype_info[f].Attributes.max_occurs
                        val = frequencies.get(pfrag[:i+1], 0)
                        if val < min_o:
                            raise Fault('Client.ValidationError',
                                '"%s" member must occur at least %d times'
                                              % ('_'.join(pfrag[:i+1]), min_o))

                        if val > max_o:
                            raise Fault('Client.ValidationError',
                                '"%s" member must occur at most %d times'
                                              % ('_'.join(pfrag[:i+1]), max_o))

                        ctype_info = ntype_info.get_flat_type_info(ntype_info)

                val = frequencies.get(s.path, 0)
                min_o = s.type.Attributes.min_occurs
                max_o = s.type.Attributes.max_occurs
                if val < min_o:
                    raise Fault('Client.ValidationError',
                                '"%s" member must occur at least %d times'
                                                    % ('_'.join(s.path), min_o))
                if val > max_o:
                    raise Fault('Client.ValidationError',
                                '"%s" member must occur at most %d times'
                                                    % ('_'.join(s.path), max_o))

        return inst


    def object_to_flat_dict(self, inst_cls, value, hier_delim="_", retval=None,
                                                    prefix=None, parent=None):
        """Converts a native python object to a flat dict.

        See :func:`spyne.model.complex.ComplexModelBase.get_flat_type_info`.
        """

        if retval is None:
            retval = {}
        if prefix is None:
            prefix = []

        fti = inst_cls.get_flat_type_info(inst_cls)
        for k, v in fti.items():
            new_prefix = list(prefix)
            new_prefix.append(k)
            subvalue = getattr(value, k, None)
            if getattr(v, 'get_flat_type_info', None) is None: # Not a ComplexModel
                key = hier_delim.join(new_prefix)

                if retval.get(key, None) is not None:
                    raise ValueError("%r.%s conflicts with previous value %r" %
                                                        (inst_cls, k, retval[key]))

                try:
                    retval[key] = subvalue
                except:
                    retval[key] = None

            else:
                self.object_to_flat_dict(fti[k], subvalue, hier_delim,
                                             retval, new_prefix, parent=inst_cls)

        return retval
