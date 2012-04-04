
#
# rpclib - Copyright (C) Rpclib contributors.
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

"""This module contains the HttpRpc protocol implementation. This is not exactly
Rest, because it ignores Http verbs.
"""

import logging
logger = logging.getLogger(__name__)

import tempfile
TEMPORARY_DIR = None

try:
    import simplejson as json
    from simplejson.decoder import JSONDecodeError
except ImportError:
    import json
    JSONDecodeError = ValueError

try:
    from cStringIO import StringIO
except ImportError:
    try:
        from StringIO import StringIO
    except ImportError: # Python 3
        from io import StringIO

from rpclib.error import ValidationError
from rpclib.model.fault import Fault
from rpclib.model.complex import ComplexModelBase
from rpclib.model.complex import Array
from rpclib.model.primitive import DateTime
from rpclib.model.primitive import Decimal
from rpclib.model.primitive import Unicode
from rpclib.protocol import ProtocolBase


def _unwrap_messages(cls, skip_depth):
    out_type = cls
    for i in range(skip_depth):
        if len(out_type._type_info) == 1:
            out_type = out_type._type_info[0]

    return out_type


class JsonObject(ProtocolBase):
    """An implementation of the json protocol that uses simplejson or json
    packages.
    """

    mime_type = 'application/json'

    def __init__(self, app=None, validator=None, skip_depth=0):
        """
        :param app: The Application definition.
        :param validator: Validator type. One of ('soft', None).
        :param skip_depth: Number of wrapper classes to ignore. This is
        typically one of (0, 1, 2) but higher numbers may also work for your
        case.
        """

        ProtocolBase.__init__(self, app, validator)

        self.skip_depth = skip_depth

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

    def create_in_document(self, ctx, in_string_encoding=None):
        """Sets ``ctx.in_document``,  using ``ctx.in_string``."""

        if in_string_encoding is None:
            in_string_encoding = 'UTF-8'

        try:
            ctx.in_document = json.loads(''.join(ctx.in_string).decode(
                                                            in_string_encoding))
        except JSONDecodeError, e:
            raise Fault('Client.JsonDecodeError', repr(e))

    def decompose_incoming_envelope(self, ctx):
        """Sets ``ctx.in_body_doc``, ``ctx.in_header_doc`` and
        ``ctx.method_request_string`` using ``ctx.in_document``.
        """

        # set ctx.in_header
        ctx.transport.in_header_doc = None # use an rpc protocol if you want headers.

        # set ctx.in_body
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

    def doc_to_object(self, cls, doc):
        if doc is None:
            return []

        if issubclass(cls, Array):
            retval = [ ]
            (serializer,) = cls._type_info.values()

            for child in doc:
                retval.append(self.from_dict_value(serializer, child))

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
                    value.append(self.from_dict_value(member, a))

            else:
                value = self.from_dict_value(member, v)

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
            in_type = _unwrap_messages(ctx.descriptor.in_message,
                                                                self.skip_depth)
        elif message is self.RESPONSE:
            in_type = _unwrap_messages(ctx.descriptor.out_message,
                                                                self.skip_depth)
        if in_type:
            # assign raw result to its wrapper, result_message
            result_message_class = ctx.descriptor.in_message
            value = ctx.in_body_doc.get(result_message_class.get_type_name(), None)
            result_message = self.doc_to_object(result_message_class, value)

            ctx.in_object = result_message
            self.event_manager.fire_event('after_deserialize', ctx)

        else:
            ctx.in_object = []

    def serialize(self, ctx, message):
        assert message in (self.REQUEST, self.RESPONSE)

        self.event_manager.fire_event('before_serialize', ctx)

        if ctx.out_error is not None:
            # FIXME: There's no way to alter soap response headers for the user.
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

            # strip the wrappers if asked for
            for i in range(self.skip_depth):
                if len(out_type._type_info) == 1:
                    (k,out_type), = out_type._type_info.items()
                    if issubclass(out_type, ComplexModelBase):
                        out_instance = getattr(out_instance, k)
                else:
                    break

            wrapper_name = None
            if not issubclass(out_type, Array):
                wrapper_name = out_type.get_type_name()

            # transform the results into a dict:
            if out_type.Attributes.max_occurs > 1:
                ctx.out_document = (self.to_value(out_type, inst, wrapper_name) for inst in out_instance)
            else:
                ctx.out_document = [self.to_value(out_type, out_instance, wrapper_name)]

            self.event_manager.fire_event('after_serialize', ctx)

    def create_out_string(self, ctx, out_string_encoding='utf8'):
        ctx.out_string = (json.dumps(o) for o in ctx.out_document)

    def from_dict_value(self, cls, value):
        # validate raw input
        if self.validator is self.SOFT_VALIDATION:
            if issubclass(cls, Unicode) and not isinstance(value, unicode):
                raise ValidationError(value)

            if issubclass(cls, Decimal) and not isinstance(value, (int, long, float)):
                raise ValidationError(value)

            if issubclass(cls, DateTime) and not (isinstance(value, unicode) and
                                            cls.validate_string(cls, value)):
                raise ValidationError(value)

        # get native type
        if issubclass(cls, ComplexModelBase):
            retval = self.doc_to_object(cls, value)

        elif issubclass(cls, DateTime):
            retval = cls.from_string(value)

        else:
            retval = value

        # validate native type
        if self.validator is self.SOFT_VALIDATION and \
                not cls.validate_native(cls, retval):
            raise ValidationError(retval)

        return retval

    def get_member_pairs(self, cls, inst):
        parent_cls = getattr(cls, '__extends__', None)
        if not (parent_cls is None):
            for r in self.get_member_pairs(parent_cls, inst):
                yield r

        for k, v in cls._type_info.items():
            try:
                sub_value = getattr(inst, k, None)
            except: # to guard against e.g. sqlalchemy throwing NoSuchColumnError
                sub_value = None

            if v.Attributes.max_occurs > 1:
                if sub_value != None:
                    yield (k, [self.to_value(v,sv) for sv in sub_value])

            else:
                yield (k, self.to_value(v, sub_value))

    def to_value(self, cls, value, k=None):
        if issubclass(cls, ComplexModelBase):
            return self.to_dict(cls, value, k)

        if issubclass(cls, DateTime):
            return cls.to_string(value)

        if issubclass(cls, Decimal):
            if cls.Attributes.format is None:
                return value
            else:
                return cls.to_string(value)

        return value

    def to_dict(self, cls, inst, field_name=None):
        inst = cls.get_serialization_instance(inst)

        retval = dict(self.get_member_pairs(cls, inst))
        if field_name is None:
            return retval
        else:
            return {field_name: retval}
