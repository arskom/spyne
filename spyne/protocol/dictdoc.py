
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

"""The ``spyne.protocol.dictdoc`` module contains an abstract
protocol that deals with hierarchical and flat dicts as {in,out}_documents.

This module is EXPERIMENTAL. You may not recognize the code here next time you
look at it.

Flattening
==========

Plain HTTP does not support hierarchical key-value stores. Spyne makes plain
HTTP fake hierarchical dicts via two small hacks.

Let's look at the following object hierarchy: ::

    class Inner(ComplexModel):
        c = Integer
        d = Array(Integer)

    class Outer(ComplexModel):
        a = Integer
        b = Inner

For example, the ``Outer(a=1, b=Inner(c=2))`` object would correspond to the
following hierarchichal dict representation: ::

    {'a': 1, 'b': { 'c': 2 }}

We do two hacks to deserialize the above object structure from a flat dict:

1. Object hierarchies are flattened. e.g. the flat representation of the above
   dict is: ``{'a': 1, 'b_c': 2}``.
2. Arrays of objects are sent using variables with array indexes in square
   brackets. So the request with the following query object: ::

      {'a': 1, 'b_d[0]': 1, 'b_d[1]': 2}}

  ... corresponds to: ::

      {'a': 1, 'b': { 'd': [1,2] }}

  If we had: ::

      class Inner(ComplexModel):
          c = Integer

      class Outer(ComplexModel):
          a = Integer
          b = Array(SomeObject)

  Or the following object: ::

      {'a': 1, 'b[0]_c': 1, 'b[1]_c': 2}}

  ... would correspond to: ::

      {'a': 1, 'b': [{ 'c': 1}, {'c': 2}]}

  ... which would deserialize as: ::

      Outer(a=1, b=[Inner(c=1), Inner(c=2)])

These hacks are both slower to process and bulkier on wire, so use class
hierarchies with HTTP only when performance is not that much of a concern.

Cookies
=======

Cookie headers are parsed and fields within HTTP requests are assigned to
fields in the ``in_header`` class, if defined.

It's also possible to get the ``Cookie`` header intact by defining an
``in_header`` object with a field named ``Cookie`` (case sensitive).

As an example, let's assume the following HTTP request: ::

    GET / HTTP/1.0
    Cookie: v1=4;v2=8
    (...)

The keys ``v1`` and ``v2`` are passed to the instance of the ``in_header``
class if it has fields named ``v1`` or ``v2``\.

Wrappers
========

Wrapper objects are an artifact of the Xml world, which don't really make sense
in other protocols. Let's look at the following object: ::

    v = Permission(application='app', feature='f1'),

Here's how it would be serialized to XML: ::

    <Permission>
      <application>app</application>
      <feature>f1</feature>
    </Permission>

With ``ignore_wrappers=True`` (which is the default) This gets serialized to
dict as follows: ::

    {
        "application": "app",
        "feature": "f1"
    }

When ``ignore_wrappers=False``, the same value/type combination would result in
the following dict: ::

    {"Permission": {
        {
            "application": "app",
            "feature": "f1"
        }
    },

This could become useful when you call a don't know what type to expect, which
is never the case with Spyne. This functionality is kept for compatibility
purposes.
"""

import logging
logger = logging.getLogger(__name__)

import re
RE_HTTP_ARRAY_INDEX = re.compile("\\[([0-9]+)\\]")

from collections import deque
from collections import defaultdict

from spyne.error import ValidationError
from spyne.error import ResourceNotFoundError

from spyne.model import ByteArray
from spyne.model import String
from spyne.model import File
from spyne.model import Fault
from spyne.model import ComplexModelBase
from spyne.model import Array
from spyne.model import SimpleModel
from spyne.model import AnyDict
from spyne.model import AnyXml
from spyne.model import AnyHtml
from spyne.model import Uuid
from spyne.model import DateTime
from spyne.model import Date
from spyne.model import Time
from spyne.model import Duration
from spyne.model import Unicode

from spyne.protocol import ProtocolBase


def check_freq_dict(cls, d, fti=None):
    if fti is None:
        fti = cls.get_flat_type_info(cls)

    if cls.Attributes.validate_freq:
        for k,v in fti.items():
            val = d[k]

            min_o, max_o = v.Attributes.min_occurs, v.Attributes.max_occurs
            if issubclass(v, Array) and v.Attributes.max_occurs == 1:
                v, = v._type_info.values()
                min_o, max_o = v.Attributes.min_occurs, v.Attributes.max_occurs

            if val < min_o:
                raise ValidationError(k,
                            '%%r member must occur at least %d times.' % min_o)
            elif val > max_o:
                raise ValidationError(k,
                            '%%r member must occur at most %d times.' % max_o)


class DictDocument(ProtocolBase):
    """An abstract protocol that can use hierarchical or flat dicts as input
    and output documents.

    Implement ``serialize()``, ``deserialize()``, ``create_in_document()`` and
    ``create_out_string()`` to use this.
    """

    # flags to be used in tests
    _decimal_as_string = False
    _huge_numbers_as_string = False

    def __init__(self, app=None, validator=None, mime_type=None,
            ignore_uncap=False, ignore_wrappers=True, complex_as=dict,
                                                                ordered=False):
        super(DictDocument, self).__init__(app, validator, mime_type, ignore_uncap)

        self.ignore_wrappers = ignore_wrappers
        self.complex_as = complex_as
        self.ordered = ordered
        if ordered:
            raise NotImplementedError('ordered == False')

        self.stringified_types = (DateTime, Date, Time, Uuid, Duration,
                                                                AnyXml, AnyHtml)

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

        logger.debug('\theader : %r' % (ctx.in_header_doc))
        logger.debug('\tbody   : %r' % (ctx.in_body_doc))

        if not isinstance(doc, dict) or len(doc) != 1:
            raise ValidationError("Need a dictionary with exactly one key "
                                  "as method name.")

        mrs, = doc.keys()
        ctx.method_request_string = '{%s}%s' % (self.app.interface.get_tns(),
                                                                            mrs)

    def deserialize(self, ctx, message):
        raise NotImplementedError()

    def serialize(self, ctx, message):
        raise NotImplementedError()

    def create_in_document(self, ctx, in_string_encoding=None):
        raise NotImplementedError()

    def create_out_string(self, ctx, out_string_encoding='utf8'):
        raise NotImplementedError()


class SimpleDictDocument(DictDocument):
    """This protocol contains logic for protocols that serialize and deserialize
    flat dictionaries. The only example as of now is Http.
    """

    def simple_dict_to_object(self, doc, inst_class, validator=None,
                                                hier_delim="_", req_enc=None):
        """Converts a flat dict to a native python object.

        See :func:`spyne.model.complex.ComplexModelBase.get_flat_type_info`.
        """

        simple_type_info = inst_class.get_simple_type_info(inst_class)

        # this is for validating cls.Attributes.{min,max}_occurs
        frequencies = defaultdict(lambda: defaultdict(int))
        if validator is self.SOFT_VALIDATION:
            _fill(simple_type_info, inst_class, frequencies)

        retval = inst_class.get_deserialization_instance()

        for orig_k, v in sorted(doc.items(), key=lambda k: k[0]):
            k = RE_HTTP_ARRAY_INDEX.sub("", orig_k)

            member = simple_type_info.get(k, None)
            if member is None:
                logger.debug("discarding field %r" % k)
                continue

            # extract native values from the list of strings in the flat dict
            # entries.
            value = []
            for v2 in v:
                # some wsgi implementations pass unicode strings, some pass str
                # strings. we get unicode here when we can and should.
                if v2 is not None and req_enc is not None \
                                        and not issubclass(member.type, String) \
                                        and issubclass(member.type, Unicode) \
                                        and not isinstance(v2, unicode):
                    v2 = v2.decode(req_enc)

                if (validator is self.SOFT_VALIDATION and not
                                  member.type.validate_string(member.type, v2)):
                    raise ValidationError((orig_k, v2))

                if issubclass(member.type, File):
                    if isinstance(v2, File.Value):
                        native_v2 = v2
                    else:
                        native_v2 = self.from_string(member.type, v2,
                                                   self.default_binary_encoding)

                elif issubclass(member.type, ByteArray):
                    native_v2 = self.from_string(member.type, v2,
                                                   self.default_binary_encoding)
                else:
                    native_v2 = self.from_string(member.type, v2)

                if (validator is self.SOFT_VALIDATION and not
                           member.type.validate_native(member.type, native_v2)):
                    raise ValidationError((orig_k, v2))

                value.append(native_v2)

            # assign the native value to the relevant class in the nested object
            # structure.
            cinst = retval
            ctype_info = inst_class.get_flat_type_info(inst_class)

            idx, nidx = 0, 0
            pkey = member.path[0]
            cfreq_key = inst_class, idx

            indexes = deque(RE_HTTP_ARRAY_INDEX.findall(orig_k))

            for pkey in member.path[:-1]:
                nidx = 0
                ncls, ninst = ctype_info[pkey], getattr(cinst, pkey, None)
                if issubclass(ncls, Array):
                    ncls, = ncls._type_info.values()

                mo = ncls.Attributes.max_occurs
                if ninst is None:
                    ninst = ncls.get_deserialization_instance()
                    if mo > 1:
                        ninst = [ninst]
                    cinst._safe_set(pkey, ninst, ncls)
                    frequencies[cfreq_key][pkey] += 1

                if mo > 1:
                    if len(indexes) == 0:
                        nidx = 0
                    else:
                        nidx = int(indexes.popleft())

                    if nidx > len(ninst):
                        raise ValidationError(orig_k,
                                            "%%r Invalid array index %d." % idx)

                    if nidx == len(ninst):
                        ninst.append(ncls.get_deserialization_instance())
                        frequencies[cfreq_key][pkey] += 1

                    cinst = ninst[nidx]

                else:
                    cinst = ninst

                cfreq_key = cfreq_key + (ncls, nidx)
                idx = nidx
                ctype_info = ncls._type_info

            frequencies[cfreq_key][member.path[-1]] += len(value)

            if member.type.Attributes.max_occurs > 1:
                _v = getattr(cinst, member.path[-1], None)
                if _v is None:
                    cinst._safe_set(member.path[-1], value, member.type)
                else:
                    _v.extend(value)
                logger.debug("\tset array   %r(%r) = %r" %
                                                    (member.path, pkey, value))
            else:
                cinst._safe_set(member.path[-1], value[0], member.type)
                logger.debug("\tset default %r(%r) = %r" %
                                                    (member.path, pkey, value))

        if validator is self.SOFT_VALIDATION:
            for k, d in frequencies.items():
                check_freq_dict(k[-2], d)

        return retval

    def object_to_simple_dict(self, inst_cls, value, hier_delim="_", retval=None,
                     prefix=None, parent=None, subvalue_eater=lambda prot,v,t:v):
        """Converts a native python object to a flat dict.

        See :func:`spyne.model.complex.ComplexModelBase.get_flat_type_info`.
        """

        if retval is None:
            retval = {}

        if prefix is None:
            prefix = []

        if value is None and inst_cls.Attributes.min_occurs == 0:
            return retval

        if issubclass(inst_cls, ComplexModelBase):
            fti = inst_cls.get_flat_type_info(inst_cls)

            for k, v in fti.items():
                new_prefix = list(prefix)
                new_prefix.append(k)
                subvalue = getattr(value, k, None)

                if (issubclass(v, Array) or v.Attributes.max_occurs > 1) and \
                                                           subvalue is not None:
                    if issubclass(v, Array):
                        subtype, = v._type_info.values()
                    else:
                        subtype = v

                    if issubclass(subtype, SimpleModel):
                        key = hier_delim.join(new_prefix)
                        l = []
                        for ssv in subvalue:
                            l.append(subvalue_eater(self, ssv, subtype))
                        retval[key] = l

                    else:
                        last_prefix = new_prefix[-1]
                        for i, ssv in enumerate(subvalue):
                            new_prefix[-1] = '%s[%d]' % (last_prefix, i)
                            self.object_to_simple_dict(subtype, ssv, hier_delim,
                                        retval, new_prefix, parent=inst_cls,
                                        subvalue_eater=subvalue_eater)

                else:
                    self.object_to_simple_dict(v, subvalue, hier_delim,
                                            retval, new_prefix, parent=inst_cls,
                                            subvalue_eater=subvalue_eater)

        else:
            key = hier_delim.join(prefix)

            if key in retval:
                raise ValueError("%r.%s conflicts with previous value %r" %
                                                    (inst_cls, key, retval[key]))

            retval[key] = subvalue_eater(self, value, inst_cls)

        return retval


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
            result_class = ctx.descriptor.in_message
            value = ctx.in_body_doc.get(result_class.get_type_name(), None)
            result_message = self._doc_to_object(result_class, value,
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
            for i, (k, v) in enumerate(out_type_info.items()):
                attr_name = k
                out_instance._safe_set(attr_name, ctx.out_object[i], v)

            ctx.out_document = self._object_to_doc(out_type, out_instance),

            self.event_manager.fire_event('after_serialize', ctx)

    def validate(self, key, class_, value):
        # validate raw input
        if issubclass(class_, Unicode) and not isinstance(value, basestring):
            raise ValidationError((key, value))

    def _from_dict_value(self, key, class_, value, validator):
        if validator is self.SOFT_VALIDATION:
            self.validate(key, class_, value)

        if issubclass(class_, AnyDict):
            return value

        # get native type
        if issubclass(class_, ComplexModelBase):
            retval = self._doc_to_object(class_, value, validator)

        else:
            if (validator is self.SOFT_VALIDATION
                                and isinstance(value, basestring)
                                and not class_.validate_string(class_, value)):
                raise ValidationError((key, value))

            if issubclass(class_, (ByteArray, file)):
                retval = self.from_string(class_, value,
                                                   self.default_binary_encoding)

            else:
                retval = self.from_string(class_, value)

        # validate native type
        if validator is self.SOFT_VALIDATION and \
                                     not class_.validate_native(class_, retval):
            raise ValidationError((key, retval))

        return retval

    def _doc_to_object(self, class_, doc, validator=None):
        if doc is None:
            return []

        if issubclass(class_, Array):
            retval = [ ]
            (serializer,) = class_._type_info.values()

            for i,child in enumerate(doc):
                retval.append(self._from_dict_value(i, serializer, child,
                                                                    validator))

            return retval

        inst = class_.get_deserialization_instance()

        # get all class attributes, including the ones coming from parent classes.
        flat_type_info = class_.get_flat_type_info(class_)

        # this is for validating class_.Attributes.{min,max}_occurs
        frequencies = defaultdict(int)

        try:
            items = doc.items()
        except AttributeError:
            items = zip(class_._type_info.keys(), doc)

        # parse input to set incoming data to related attributes.
        for k,v in items:
            member = flat_type_info.get(k, None)
            if member is None:
                continue

            mo = member.Attributes.max_occurs
            if mo > 1:
                value = getattr(inst, k, None)
                if value is None:
                    value = []

                for a in v:
                    value.append(self._from_dict_value(k, member, a, validator))

            else:
                value = self._from_dict_value(k, member, v, validator)

            inst._safe_set(k, value, member)

            frequencies[k] += 1

        if validator is self.SOFT_VALIDATION:
            check_freq_dict(class_, frequencies, flat_type_info)

        return inst

    def _object_to_doc(self, class_, value):
        retval = None

        if self.ignore_wrappers:
            ti = getattr(class_, '_type_info', {})

            while class_.Attributes._wrapper and len(ti) == 1:
                # Wrappers are auto-generated objects that have exactly one
                # child type.
                key, = ti.keys()
                if not issubclass(class_, Array):
                    value = getattr(value, key, None)
                class_, = ti.values()
                ti = getattr(class_, '_type_info', {})

        # transform the results into a dict:
        if class_.Attributes.max_occurs > 1:
            if value is not None:
                retval = [self._to_value(class_, inst) for inst in value]
        else:
            retval = self._to_value(class_, value)

        return retval

    def _get_member_pairs(self, class_, inst):
        parent_cls = getattr(class_, '__extends__', None)
        if parent_cls is not None:
            for r in self._get_member_pairs(parent_cls, inst):
                yield r

        for k, v in class_._type_info.items():
            try:
                sub_value = getattr(inst, k, None)
            # to guard against e.g. sqlalchemy throwing NoSuchColumnError
            except Exception, e:
                logger.error("Error getting %r: %r" %(k,e))
                sub_value = None

            val = self._object_to_doc(v, sub_value)
            if val is not None or v.Attributes.min_occurs > 0:
                yield (k, val)

    def _to_value(self, class_, value):
        if issubclass(class_, AnyDict):
            return value

        if issubclass(class_, Array):
            st, = class_._type_info.values()
            return self._object_to_doc(st, value)

        if issubclass(class_, ComplexModelBase):
            if self.complex_as is list:
                return list(self._complex_to_list(class_, value))
            else:
                return self._complex_to_dict(class_, value)

        if issubclass(class_, (ByteArray, File)):
            return self.to_string(class_, value, self.default_binary_encoding)

        return self.to_string(class_, value)

    def _complex_to_dict(self, class_, inst):
        inst = class_.get_serialization_instance(inst)

        d = self.complex_as(self._get_member_pairs(class_, inst))
        if self.ignore_wrappers:
            return d
        else:
            return {class_.get_type_name(): d}

    def _complex_to_list(self, class_, inst):
        inst = class_.get_serialization_instance(inst)

        for k,v in self._get_member_pairs(class_, inst):
            yield v


def _fill(simple_type_info, inst_class, frequencies):
    for k, member in simple_type_info.items():
        if member.type.Attributes.min_occurs == 0:
            continue

        ctype_info = inst_class.get_flat_type_info(inst_class)

        idx, nidx = 0, 0
        pkey = member.path[0]
        cfreq_key = inst_class, idx

        for i in range(len(member.path) - 1):
            pkey = member.path[i]
            nidx = 0

            ncls = ctype_info[pkey]

            frequencies[cfreq_key][pkey] += 0

            cfreq_key = cfreq_key + (ncls, nidx)
            idx = nidx
            ctype_info = ncls._type_info

        frequencies[cfreq_key][member.path[-1]] += 0
