
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

from __future__ import print_function

import logging
logger = logging.getLogger(__name__)

import re
RE_HTTP_ARRAY_INDEX = re.compile("\\[([0-9]+)\\]")

from mmap import mmap
from collections import defaultdict

from spyne.util import six
from spyne.util.six.moves.collections_abc import Iterable as AbcIterable

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

    VALID_UNICODE_SOURCES = (six.text_type, six.binary_type, memoryview,
                                                                mmap, bytearray)

    from_serstr = DictDocument.from_unicode
    to_serstr = DictDocument.to_unicode

    def get_class_name(self, cls):
        class_name = cls.get_type_name()
        if not six.PY2:
            if isinstance(class_name, bytes):
                class_name = class_name.decode('utf8')

        return class_name

    def get_complex_as(self, attr):
        if attr.complex_as is None:
            return self.complex_as
        return attr.complex_as

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
        else:
            raise ValueError(message)  # should be impossible

        if body_class:
            # assign raw result to its wrapper, result_message
            doc = ctx.in_body_doc

            logger.debug("Request: %r", doc)

            class_name = self.get_class_name(body_class)
            if self.ignore_wrappers:
                doc = doc.get(class_name, None)

            result_message = self._doc_to_object(ctx, body_class, doc,
                                                                 self.validator)
            ctx.in_object = result_message

        else:
            ctx.in_object = []

        self.event_manager.fire_event('after_deserialize', ctx)

    def _fault_to_doc(self, inst, cls=None):
        if cls is None:
            cls = Fault

        if self.complex_as is list:
            return [cls.to_list(inst.__class__, inst, self)]

        elif self.complex_as is tuple:
            fault_as_list = [Fault.to_list(inst.__class__, inst, self)]
            return tuple(fault_as_list)

        else:
            return [Fault.to_dict(inst.__class__, inst, self)]

    def serialize(self, ctx, message):
        assert message in (self.REQUEST, self.RESPONSE)

        self.event_manager.fire_event('before_serialize', ctx)

        if ctx.out_error is not None:
            ctx.out_document = self._fault_to_doc(ctx.out_error)
            return

        # get the result message
        if message is self.REQUEST:
            out_type = ctx.descriptor.in_message

        elif message is self.RESPONSE:
            out_type = ctx.descriptor.out_message

        else:
            assert False

        if out_type is None:
            return

        # assign raw result to its wrapper, result_message
        if ctx.descriptor.is_out_bare():
            out_instance, = ctx.out_object

        else:
            out_type_info = out_type.get_flat_type_info(out_type)

            # instantiate the result message
            out_instance = out_type()

            for i, (k, v) in enumerate(out_type_info.items()):
                attrs = self.get_cls_attrs(v)
                out_instance._safe_set(k, ctx.out_object[i], v, attrs)

        ctx.out_document = self._object_to_doc(out_type, out_instance, set()),

        logger.debug("Response: %r", ctx.out_document)
        self.event_manager.fire_event('after_serialize', ctx)

    def validate(self, key, cls, inst):
        if inst is None and self.get_cls_attrs(cls).nullable:
            pass

        elif issubclass(cls, Unicode) and not isinstance(inst,
                                                    self.VALID_UNICODE_SOURCES):
            raise ValidationError([key, inst])

    def _from_dict_value(self, ctx, key, cls, inst, validator):
        if validator is self.SOFT_VALIDATION:
            self.validate(key, cls, inst)

        cls_attrs = self.get_cls_attrs(cls)
        complex_as = self.get_complex_as(cls_attrs)
        if complex_as is list or complex_as is tuple:
            check_complex_as = (list, tuple)
        else:
            check_complex_as = complex_as

        # get native type
        if issubclass(cls, File):
            if isinstance(inst, check_complex_as):
                cls = cls_attrs.type or cls
                inst = self._parse(cls_attrs, inst)
                retval = self._doc_to_object(ctx, cls, inst, validator)

            else:
                retval = self.from_serstr(cls, inst, self.binary_encoding)

        else:
            inst = self._parse(cls_attrs, inst)

            if issubclass(cls, (Any, AnyDict)):
                retval = inst

            elif issubclass(cls, ComplexModelBase):
                retval = self._doc_to_object(ctx, cls, inst, validator)

            else:
                if cls_attrs.empty_is_none and inst in (u'', b''):
                    inst = None

                if (validator is self.SOFT_VALIDATION
                                        and isinstance(inst, six.string_types)
                                        and not cls.validate_string(cls, inst)):
                    raise ValidationError([key, inst])

                if issubclass(cls, (ByteArray, Uuid)):
                    retval = self.from_serstr(cls, inst, self.binary_encoding)

                elif issubclass(cls, Unicode):
                    if isinstance(inst, bytearray):
                        retval = six.text_type(inst,
                                encoding=cls_attrs.encoding or 'ascii',
                                                errors=cls_attrs.unicode_errors)

                    elif isinstance(inst, memoryview):
                        # FIXME: memoryview needs a .decode() function to avoid
                        #        needless copying here
                        retval = inst.tobytes().decode(
                            cls_attrs.encoding or 'ascii',
                                                errors=cls_attrs.unicode_errors)

                    elif isinstance(inst, mmap):
                        # FIXME: mmap needs a .decode() function to avoid
                        #        needless copying here
                        retval = mmap[:].decode(cls_attrs.encoding,
                                                errors=cls_attrs.unicode_errors)

                    elif isinstance(inst, six.binary_type):
                        retval = self.unicode_from_bytes(cls, inst)

                    else:
                        retval = inst

                else:
                    retval = self.from_serstr(cls, inst)

        # validate native type
        if validator is self.SOFT_VALIDATION:
            if not cls.validate_native(cls, retval):
                raise ValidationError([key, retval])

        return retval

    def _doc_to_object(self, ctx, cls, doc, validator=None):
        if doc is None:
            return []

        if issubclass(cls, Any):
            doc = self._cast(self.get_cls_attrs(cls), doc)
            return doc

        if issubclass(cls, Array):
            doc = self._cast(self.get_cls_attrs(cls), doc)
            retval = []
            (serializer,) = cls._type_info.values()

            if not isinstance(doc, AbcIterable):
                raise ValidationError(doc)

            for i, child in enumerate(doc):
                retval.append(self._from_dict_value(ctx, i, serializer, child,
                                                                     validator))

            return retval

        cls_attrs = self.get_cls_attrs(cls)
        if not self.ignore_wrappers and not cls_attrs.not_wrapped:
            if not isinstance(doc, dict):
                raise ValidationError(doc, "Wrapper documents must be dicts")

            if len(doc) == 0:
                return None

            if len(doc) > 1:
                raise ValidationError(doc, "There can be only one entry in a "
                                                                 "wrapper dict")

            subclasses = cls.get_subclasses()
            (class_name, doc), = doc.items()
            if not six.PY2 and isinstance(class_name, bytes):
                class_name = class_name.decode('utf8')

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

        inst = cls.get_deserialization_instance(ctx)

        # get all class attributes, including the ones coming from
        # parent classes.
        flat_type_info = cls.get_flat_type_info(cls)
        if flat_type_info is None:
            logger.critical("No flat_type_info found for type %r", cls)
            raise TypeError(cls)

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
            except TypeError as e:
                logger.error("Invalid document %r for %r", doc, cls)
                raise ValidationError(doc)

        # parse input to set incoming data to related attributes.
        for k, v in items:
            if self.key_encoding is not None and isinstance(k, bytes):
                try:
                    k = k.decode(self.key_encoding)
                except UnicodeDecodeError:
                    raise ValidationError(k)

            member = flat_type_info.get(k, None)
            if member is None:
                member, k = flat_type_info.alt.get(k, (None, k))
                if member is None:
                    continue

            member_attrs = self.get_cls_attrs(member)

            if member_attrs.exc:
                continue

            mo = member_attrs.max_occurs
            if mo > 1:
                subinst = getattr(inst, k, None)
                if subinst is None:
                    subinst = []

                for a in v:
                    subinst.append(
                            self._from_dict_value(ctx, k, member, a, validator))

            else:
                subinst = self._from_dict_value(ctx, k, member, v, validator)

            inst._safe_set(k, subinst, member, member_attrs)

            frequencies[k] += 1

        attrs = self.get_cls_attrs(cls)
        if validator is self.SOFT_VALIDATION and attrs.validate_freq:
            self._check_freq_dict(cls, frequencies, flat_type_info)

        return inst

    def _object_to_doc(self, cls, inst, tags=None):
        if inst is None:
            return None

        if tags is None:
            tags = set()

        retval = None

        if isinstance(inst, Fault):
            retval = None
            inst_id = id(inst)
            if not (inst_id in tags):
                retval = self._fault_to_doc(inst, cls)
                tags.add(inst_id)
            return retval

        cls_attrs = self.get_cls_attrs(cls)
        if cls_attrs.exc:
            return

        cls_orig = None
        if cls_attrs.out_type is not None:
            cls_orig = cls
            cls = cls_attrs.out_type
            # remember to do this if cls_attrs are needed below
            # (currently cls_attrs is not used so we don't do this)
            # cls_attrs = self.get_cls_attrs(cls)

        elif cls_attrs.type is not None:
            cls_orig = cls
            cls = cls_attrs.type
            # remember to do this if cls_attrs are needed below
            # (currently cls_attrs is not used so we don't do this)
            # cls_attrs = self.get_cls_attrs(cls)

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
                retval = []

                for subinst in inst:
                    if id(subinst) in tags:
                        # even when there is ONE already-serialized instance,
                        # we throw the whole thing away.
                        logger.debug("Throwing the whole array away because "
                                                        "found %d", id(subinst))

                        # this is DANGEROUS
                        #logger.debug("Said array: %r", inst)

                        return None

                    retval.append(self._to_dict_value(cls, subinst, tags,
                                                      cls_orig=cls_orig or cls))

        else:
            retval = self._to_dict_value(cls, inst, tags,
                                                       cls_orig=cls_orig or cls)

        return retval

    def _get_member_pairs(self, cls, inst, tags):
        old_len = len(tags)
        tags = tags | {id(inst)}
        assert len(tags) > old_len, ("Offending instance: %r" % inst)

        for k, v in self.sort_fields(cls):
            subattr = self.get_cls_attrs(v)

            if subattr.exc:
                continue

            try:
                subinst = getattr(inst, k, None)

            # to guard against e.g. sqlalchemy throwing NoSuchColumnError
            except Exception as e:
                logger.error("Error getting %r: %r" % (k, e))
                subinst = None

            if subinst is None:
                subinst = subattr.default
            else:
                if id(subinst) in tags:
                    continue

            logger.debug("%s%r type is %r", "  " * len(tags), k, v)

            val = self._object_to_doc(v, subinst, tags)
            min_o = subattr.min_occurs

            complex_as = self.get_complex_as(subattr)
            if val is not None or min_o > 0 or complex_as is list:
                sub_name = subattr.sub_name
                if sub_name is None:
                    sub_name = k

                yield (sub_name, val)

    def _to_dict_value(self, cls, inst, tags, cls_orig=None):
        if cls_orig is None:
            cls_orig = cls
        cls, switched = self.get_polymorphic_target(cls, inst)
        cls_attrs = self.get_cls_attrs(cls)

        inst = self._sanitize(cls_attrs, inst)

        if issubclass(cls_orig, File):
            cls_orig_attrs = self.get_cls_attrs(cls_orig)
            if not isinstance(inst, cls_orig_attrs.type):
                return self.to_serstr(cls_orig, inst, self.binary_encoding)

            retval = self._complex_to_doc(cls_orig_attrs.type, inst, tags)
            complex_as = self.get_complex_as(cls_orig_attrs)

            if complex_as is dict and not self.ignore_wrappers:
                retval = next(iter(retval.values()))

            return retval

        if issubclass(cls, (Any, AnyDict)):
            return inst

        if issubclass(cls, Array):
            st, = cls._type_info.values()
            return self._object_to_doc(st, inst, tags)

        if issubclass(cls, ComplexModelBase):
            return self._complex_to_doc(cls, inst, tags)

        if issubclass(cls, (ByteArray, Uuid)):
            return self.to_serstr(cls, inst, self.binary_encoding)

        return self.to_serstr(cls, inst)

    def _complex_to_doc(self, cls, inst, tags):
        cls_attrs = self.get_cls_attrs(cls)
        sf = cls_attrs.simple_field
        if sf is not None:
            # we want this to throw when sf does not exist
            subcls = cls.get_flat_type_info(cls)[sf]

            subinst = getattr(inst, sf, None)

            logger.debug("Render complex object %s to the value %r of its "
                         "field '%s'", cls.get_type_name(), subinst, sf)

            return self.to_unicode(subcls, subinst)

        cls_attr = self.get_cls_attrs(cls)
        complex_as = self.get_complex_as(cls_attr)
        if complex_as is list or \
                         getattr(cls.Attributes, 'serialize_as', False) is list:
            return list(self._complex_to_list(cls, inst, tags))
        return self._complex_to_dict(cls, inst, tags)

    def _complex_to_dict(self, cls, inst, tags):
        inst = cls.get_serialization_instance(inst)
        cls_attr = self.get_cls_attrs(cls)
        complex_as = self.get_complex_as(cls_attr)

        if self.key_encoding is None:
            d = complex_as(self._get_member_pairs(cls, inst, tags))

            if (self.ignore_wrappers or cls_attr.not_wrapped) \
                                                 and not bool(cls_attr.wrapper):
                return d

            else:
                if isinstance(cls_attr.wrapper,
                                              (six.text_type, six.binary_type)):
                    return {cls_attr.wrapper: d}
                else:
                    return {cls.get_type_name(): d}
        else:
            d = complex_as( (k.encode(self.key_encoding), v) for k, v in
                                       self._get_member_pairs(cls, inst, tags) )

            if (self.ignore_wrappers or cls_attr.not_wrapped) \
                                                 and not bool(cls_attr.wrapper):
                return d

            else:
                if isinstance(cls_attr.wrapper, six.text_type):
                    return {cls_attr.wrapper.encode(self.key_encoding): d}
                elif isinstance(cls_attr.wrapper, six.binary_type):
                    return {cls_attr.wrapper: d}
                else:
                    return {cls.get_type_name().encode(self.key_encoding): d}

    def _complex_to_list(self, cls, inst, tags):
        inst = cls.get_serialization_instance(inst)

        for k, v in self._get_member_pairs(cls, inst, tags):
            yield v
