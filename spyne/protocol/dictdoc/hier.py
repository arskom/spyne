
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

import logging
logger = logging.getLogger(__name__)

import re
RE_HTTP_ARRAY_INDEX = re.compile("\\[([0-9]+)\\]")

from collections import defaultdict

from spyne.util import six
from spyne.error import ValidationError
from spyne.error import ResourceNotFoundError

from spyne.model import ByteArray, File, Fault, ComplexModelBase, Array, Any, \
    AnyDict, Uuid, Unicode

from spyne.protocol.dictdoc import DictDocument


class HierDictDocument(DictDocument):
    """This protocol contains logic for protocols that serialize and deserialize
    hierarchical dictionaries. Examples include: Json, MessagePack and Yaml.

    Implement ``create_in_document()`` and ``create_out_string()`` to use this.
    """

    def deserialize(self, ctx, message):
        assert message in (self.REQUEST, self.RESPONSE)

        self.event_manager.fire_event('before_deserialize', ctx)

        if ctx.descriptor is None:
            raise ResourceNotFoundError(ctx.method_request_string)

        # instantiate the result message
        if message is self.REQUEST:
            body_class = ctx.descriptor.in_message
        elif message is self.RESPONSE:
            body_class = ctx.descriptor.out_message

        if body_class:
            # assign raw result to its wrapper, result_message
            doc = ctx.in_body_doc
            if self.ignore_wrappers:
                doc = doc.get(body_class.get_type_name(), None)
            result_message = self._doc_to_object(body_class, doc,
                                                                 self.validator)
            ctx.in_object = result_message

        else:
            ctx.in_object = []

        self.event_manager.fire_event('after_deserialize', ctx)

    def serialize(self, ctx, message):
        assert message in (self.REQUEST, self.RESPONSE)

        self.event_manager.fire_event('before_serialize', ctx)

        if ctx.out_error is not None:
            ctx.out_document = [Fault.to_dict(ctx.out_error.__class__,
                                                                 ctx.out_error)]
            return

        # get the result message
        if message is self.REQUEST:
            out_type = ctx.descriptor.in_message
        elif message is self.RESPONSE:
            out_type = ctx.descriptor.out_message
        if out_type is None:
            return

        out_type_info = out_type.get_flat_type_info(out_type)

        # instantiate the result message
        out_instance = out_type()

        # assign raw result to its wrapper, result_message
        for i, (k, v) in enumerate(out_type_info.items()):
            attr_name = k
            out_instance._safe_set(attr_name, ctx.out_object[i], v)

        ctx.out_document = self._object_to_doc(out_type, out_instance),

        self.event_manager.fire_event('after_serialize', ctx)

    def validate(self, key, cls, inst):
        if inst is None and self.get_cls_attrs(cls).nullable:
            pass

        elif issubclass(cls, Unicode) and not isinstance(inst, six.string_types):
            raise ValidationError((key, inst))

    def _from_dict_value(self, key, cls, inst, validator):
        if validator is self.SOFT_VALIDATION:
            self.validate(key, cls, inst)

        if issubclass(cls, (Any, AnyDict)):
            retval = inst

        # get native type
        elif issubclass(cls, File) and isinstance(inst, self.complex_as):
            retval = self._doc_to_object(cls.Attributes.type, inst, validator)

        elif issubclass(cls, ComplexModelBase):
            retval = self._doc_to_object(cls, inst, validator)

        else:
            if cls.Attributes.empty_is_none and inst in (u'', b''):
                inst = None

            if (validator is self.SOFT_VALIDATION
                                and isinstance(inst, six.string_types)
                                and not cls.validate_string(cls, inst)):
                raise ValidationError((key, inst))

            if issubclass(cls, (ByteArray, File, Uuid)):
                retval = self.from_unicode(cls, inst, self.binary_encoding)
            else:
                retval = self.from_unicode(cls, inst)

        # validate native type
        if validator is self.SOFT_VALIDATION and \
                                           not cls.validate_native(cls, retval):
            raise ValidationError((key, retval))

        return retval

    def _doc_to_object(self, cls, doc, validator=None):
        if doc is None:
            return []

        if issubclass(cls, Any):
            return doc

        if issubclass(cls, Array):
            retval = []
            (serializer,) = cls._type_info.values()

            for i, child in enumerate(doc):
                retval.append(self._from_dict_value(i, serializer, child,
                                                                    validator))

            return retval

        if not self.ignore_wrappers:
            if not isinstance(doc, dict):
                raise ValidationError("Wrapper documents must be dicts")
            if len(doc) == 0:
                return None
            if len(doc) > 1:
                raise ValidationError(doc, "There can be only one entry in a "
                                                                 "wrapper dict")

            subclasses = cls.get_subclasses()
            (class_name, doc), = doc.items()
            if cls.get_type_name() != class_name and subclasses is not None \
                                                        and len(subclasses) > 0:
                for subcls in subclasses:
                    if subcls.get_type_name() == class_name:
                        break
                else:
                    raise ValidationError(class_name,
                         "Class name %%r is not registered as a subclass of %r" %
                                                            cls.get_type_name())

                if not self.issubclass(subcls, cls):
                    raise ValidationError(class_name,
                             "Class name %%r is not a subclass of %r" %
                                                            cls.get_type_name())
                cls = subcls

        inst = cls.get_deserialization_instance()

        # get all class attributes, including the ones coming from parent classes.
        flat_type_info = cls.get_flat_type_info(cls)

        # this is for validating cls.Attributes.{min,max}_occurs
        frequencies = defaultdict(int)

        try:
            items = doc.items()
        except AttributeError:
            # Input is not a dict, so we assume it's a sequence that we can pair
            # with the incoming sequence with field names.
            # TODO: cache this
            try:
                items = zip([k for k, v in flat_type_info.items()
                                         if not self.get_cls_attrs(v).exc], doc)
            except TypeError:
                logger.error("Invalid document %r for %r", doc, cls)
                raise

        # parse input to set incoming data to related attributes.
        for k, v in items:
            member = flat_type_info.get(k, None)
            if member is None:
                member, k = flat_type_info.alt.get(k, (None, k))
                if member is None:
                    continue

            attr = self.get_cls_attrs(member)

            mo = attr.max_occurs
            if mo > 1:
                subinst = getattr(inst, k, None)
                if subinst is None:
                    subinst = []

                for a in v:
                    subinst.append(self._from_dict_value(k, member, a, validator))

            else:
                subinst = self._from_dict_value(k, member, v, validator)

            inst._safe_set(k, subinst, member)

            frequencies[k] += 1

        attrs = self.get_cls_attrs(cls)
        if validator is self.SOFT_VALIDATION and attrs.validate_freq:
            self._check_freq_dict(cls, frequencies, flat_type_info)

        return inst

    def _object_to_doc(self, cls, inst):
        retval = None

        if self.ignore_wrappers:
            ti = getattr(cls, '_type_info', {})

            while cls.Attributes._wrapper and len(ti) == 1:
                # Wrappers are auto-generated objects that have exactly one
                # child type.
                key, = ti.keys()
                if not issubclass(cls, Array):
                    inst = getattr(inst, key, None)
                cls, = ti.values()
                ti = getattr(cls, '_type_info', {})

        # transform the results into a dict:
        if cls.Attributes.max_occurs > 1:
            if inst is not None:
                retval = [self._to_dict_value(cls, inst) for inst in inst]
        else:
            retval = self._to_dict_value(cls, inst)

        return retval

    def _get_member_pairs(self, cls, inst):
        parent_cls = getattr(cls, '__extends__', None)
        if parent_cls is not None:
            for r in self._get_member_pairs(parent_cls, inst):
                yield r

        for k, v in cls._type_info.items():
            attr = self.get_cls_attrs(v)

            if getattr(attr, 'exc', None):
                continue

            try:
                subinst = getattr(inst, k, None)
            # to guard against e.g. sqlalchemy throwing NoSuchColumnError
            except Exception as e:
                logger.error("Error getting %r: %r" % (k, e))
                subinst = None

            if subinst is None:
                subinst = attr.default

            val = self._object_to_doc(v, subinst)
            min_o = attr.min_occurs

            if val is not None or min_o > 0 or self.complex_as is list:
                sub_name = attr.sub_name
                if sub_name is None:
                    sub_name = k

                yield (sub_name, val)

    def _to_dict_value(self, cls, inst):
        cls, switched = self.get_polymorphic_target(cls, inst)

        if issubclass(cls, (Any, AnyDict)):
            return inst

        if issubclass(cls, Array):
            st, = cls._type_info.values()
            return self._object_to_doc(st, inst)

        if issubclass(cls, ComplexModelBase):
            return self._complex_to_doc(cls, inst)

        if issubclass(cls, File) and isinstance(inst, cls.Attributes.type):
            retval = self._complex_to_doc(cls.Attributes.type, inst)
            if self.complex_as is dict and not self.ignore_wrappers:
                retval = iter(retval.values()).next()

            return retval

        if issubclass(cls, (ByteArray, File, Uuid)):
            return self.to_string(cls, inst, self.binary_encoding)

        return self.to_unicode(cls, inst)

    def _complex_to_doc(self, cls, inst):
        if self.complex_as is list or \
                        getattr(cls.Attributes, 'serialize_as', False) is list:
            return list(self._complex_to_list(cls, inst))
        else:
            return self._complex_to_dict(cls, inst)

    def _complex_to_dict(self, cls, inst):
        inst = cls.get_serialization_instance(inst)

        d = self.complex_as(self._get_member_pairs(cls, inst))
        if self.ignore_wrappers:
            return d
        else:
            return {cls.get_type_name(): d}

    def _complex_to_list(self, cls, inst):
        inst = cls.get_serialization_instance(inst)

        for k, v in self._get_member_pairs(cls, inst):
            yield v
