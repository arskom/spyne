
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

"""The ``spyne.protocol.xml.model`` module contains type-specific serialization
logic.
"""

import logging
logger = logging.getLogger(__name__)

from inspect import isgenerator
from collections import defaultdict

from lxml import etree
from lxml import html
from lxml.builder import E

from spyne.const.xml_ns import xsi as _ns_xsi
from spyne.const.xml_ns import soap_env as _ns_soap_env
from spyne.const.xml_ns import const_prefmap
_pref_soap_env = const_prefmap[_ns_soap_env]

from spyne.error import Fault
from spyne.error import ValidationError
from spyne.model import PushBase
from spyne.model import File
from spyne.model import ByteArray
from spyne.model import XmlData
from spyne.model import XmlAttribute
from spyne.util import coroutine, Break
from spyne.util.etreeconv import etree_to_dict
from spyne.util.etreeconv import dict_to_etree


def append(elt, child_elt):
    if isinstance(elt, etree._Element):
        elt.append(child_elt)
    else:
        elt.write(child_elt)


def base_from_element(prot, cls, element):
    if prot.validator is prot.SOFT_VALIDATION and not (
                                        cls.validate_string(cls, element.text)):
        raise ValidationError(element.text)

    retval = prot.from_string(cls, element.text)

    if prot.validator is prot.SOFT_VALIDATION and not (
                                        cls.validate_native(cls, retval)):
        raise ValidationError(retval)

    return retval


def byte_array_from_element(prot, cls, element):
    if prot.validator is prot.SOFT_VALIDATION and not (
                                        cls.validate_string(cls, element.text)):
        raise ValidationError(element.text)

    retval = prot.from_string(cls, element.text, prot.default_binary_encoding)

    if prot.validator is prot.SOFT_VALIDATION and not (
                                        cls.validate_native(cls, retval)):
        raise ValidationError(retval)

    return retval


def byte_array_to_parent(prot, cls, value, tns, parent, name='retval'):
    append(parent, E("{%s}%s" % (tns, name),
                    prot.to_string(cls, value, prot.default_binary_encoding)))


def base_to_parent(prot, cls, value, tns, parent, name='retval'):
    """Creates a lxml.etree SubElement as a child of a 'parent' Element

    :param prot:  The protocol that will be used to serialize the given value.
    :param cls:   The type of the value that's going to determine how to pack
                  the given value.
    :param value: The value to be set for the 'text' element of the newly
                  created SubElement
    :param tns:   The target namespace of the new SubElement, used with 'name'
                  to set the tag.
    :param parent: The parent Element to which the new child will be
                  appended.
    :param name:  The tag name of the new SubElement, 'retval' by default.
    """

    append(parent, E("{%s}%s" % (tns, name), prot.to_string(cls, value)))


def null_to_parent(prot, cls, value, tns, parent, name='retval'):
    append(parent, E("{%s}%s" % (tns, name), **{'{%s}nil' % _ns_xsi: 'true'}))


def null_from_element(prot, cls, element):
    return None


def xmlattribute_to_parent(prot, cls, inst, tns, parent, name):
    ns = cls._ns
    if ns is None:
        ns = cls.Attributes.sub_ns

    if ns is not None:
        name = "{%s}%s" % (ns, name)

    if inst is not None:
        if issubclass(cls.type, (ByteArray, File)):
            parent.set(name, prot.to_string(cls.type, inst,
                                                prot.default_binary_encoding))
        else:
            parent.set(name, prot.to_string(cls.type, inst))


def attachment_to_parent(prot, cls, inst, tns, parent, name='retval'):
    """This class method takes the data from the attachment and base64 encodes
    it as the text of an Element. An attachment can specify a file_name and if
    no data is given, it will read the data from the file.
    """

    append(parent, E("{%s}%s" % (tns, name),
                    ''.join([b.decode('ascii') for b in cls.to_base64(inst)])))


def attachment_from_element(prot, cls, element):
    """This method returns an Attachment object that contains the base64
    decoded string of the text of the given element.
    """

    return cls.from_base64([element.text])

@coroutine
def gen_members_parent(prot, cls, inst, parent, tag_name, subelts):
    delay = set()

    if isinstance(parent, etree._Element):
        elt = E(tag_name, *subelts)
        append(parent, elt)
        ret = _get_members_etree(prot, cls, inst, elt, delay)
        if isgenerator(ret):
            try:
                while True:
                    y = (yield) # may throw Break
                    ret.send(y)

            except Break:
                try:
                    ret.throw(Break())
                except StopIteration:
                    pass

    else:
        with parent.element(tag_name):
            for e in subelts:
                parent.write(e)
            ret = _get_members_etree(prot, cls, inst, parent, delay)
            if isgenerator(ret):
                try:
                    while True:
                        y = (yield) # may throw Break
                        ret.send(y)

                except Break:
                    try:
                        ret.throw(Break())
                    except StopIteration:
                        pass


@coroutine
def _get_members_etree(prot, cls, inst, parent, delay):
    try:
        parent_cls = getattr(cls, '__extends__', None)

        if not (parent_cls is None):
            ret = _get_members_etree(prot, parent_cls, inst, parent)
            if ret is not None:
                while True:
                    sv2 = (yield)
                    ret.send(sv2)

        for k, v in cls._type_info.items():
            try:
                subvalue = getattr(inst, k, None)
            except: # to guard against e.g. SqlAlchemy throwing NoSuchColumnError
                subvalue = None

            # This is a tight loop, so enable this only when necessary.
            # logger.debug("get %r(%r) from %r: %r" % (k, v, inst, subvalue))

            sub_ns = v.Attributes.sub_ns
            if sub_ns is None:
                sub_ns = cls.get_namespace()

            sub_name = v.Attributes.sub_name
            if sub_name is None:
                sub_name = k

            if issubclass(v, XmlAttribute):
                if v.attribute_of in cls._type_info.keys():
                    delay.add(k)
                    continue

            elif issubclass(v, XmlData):
                v.marshall(prot, sub_name, subvalue, parent)
                continue

            mo = v.Attributes.max_occurs
            if subvalue is not None and mo > 1:
                if isinstance(subvalue, PushBase):
                    while True:
                        sv = (yield)
                        ret = prot.to_parent(v, sv, sub_ns, parent, sub_name)
                        if ret is not None:
                            while True:
                                sv2 = (yield)
                                ret.send(sv2)

                else:
                    for sv in subvalue:
                        ret = prot.to_parent(v, sv, sub_ns, parent, sub_name)

                        if ret is not None:
                            while True:
                                sv2 = (yield)
                                ret.send(sv2)

            # Don't include empty values for non-nillable optional attributes.
            elif subvalue is not None or v.Attributes.min_occurs > 0:
                ret = prot.to_parent(v, subvalue, sub_ns, parent, sub_name)
                if ret is not None:
                    while True:
                        sv2 = (yield)
                        ret.send(sv2)

    except Break:
        pass

    # attribute_of won't work with async.
    if isinstance(parent, etree._Element):
        for k in delay:
            v = cls._type_info[k]

            subvalue = getattr(inst, k, None)
            sub_name = v.Attributes.sub_name
            if sub_name is None:
                sub_name = k

            a_of = v.attribute_of
            attr_parents = parent.findall("{%s}%s" % (cls.__namespace__, a_of))

            if cls._type_info[a_of].Attributes.max_occurs > 1:
                for subsubvalue, attr_parent in zip(subvalue, attr_parents):
                    prot.to_parent(v, subsubvalue, v.get_namespace(), attr_parent,k)

            else:
                for attr_parent in attr_parents:
                    prot.to_parent(v, subvalue, v.get_namespace(), attr_parent, k)

def complex_to_parent(prot, cls, value, tns, parent, name=None):
    if name is None:
        name = cls.get_type_name()

    tag_name = "{%s}%s" % (tns, name)
    inst = cls.get_serialization_instance(value)

    return gen_members_parent(prot, cls, inst, parent, tag_name, subelts=[])


def fault_to_parent(prot, cls, inst, tns, parent):
    tag_name = "{%s}Fault" % _ns_soap_env

    subelts = [
        E("faultcode", '%s:%s' % (_pref_soap_env, inst.faultcode)),
        E("faultstring", inst.faultstring),
        E("faultactor", inst.faultactor),
    ]
    if inst.detail != None:
        append(subelts, E('detail', inst.detail))

    # add other nonstandard fault subelements with get_members_etree
    return gen_members_parent(prot, cls, inst, parent, tag_name, subelts=subelts)


def enum_to_parent(prot, cls, value, tns, parent, name='retval'):
    base_to_parent(prot, cls, str(value), tns, parent, name)


def xml_to_parent(prot, cls, value, tns, parent, name):
    if isinstance(value, str) or isinstance(value, unicode):
        value = etree.fromstring(value)

    append(parent, E('{%s}%s' % (tns, name), value))


def html_to_parent(prot, cls, value, tns, parent, name):
    if isinstance(value, str) or isinstance(value, unicode):
        value = html.fromstring(value)

    append(parent, E('{%s}%s' % (tns, name), value))


def dict_to_parent(prot, cls, value, tns, parent, name):
    elt = E('{%s}%s' % (tns, name))
    dict_to_etree(value, elt)

    append(parent, elt)


def complex_from_element(prot, cls, element):
    inst = cls.get_deserialization_instance()

    flat_type_info = cls.get_flat_type_info(cls)

    # this is for validating cls.Attributes.{min,max}_occurs
    frequencies = defaultdict(int)

    xtba_key, xtba_type = cls.Attributes._xml_tag_body_as
    if xtba_key is not None:
        if issubclass(xtba_type.type, (ByteArray, File)):
            value = prot.from_string(xtba_type.type, element.text,
                                                prot.default_binary_encoding)
        else:
            value = prot.from_string(xtba_type.type, element.text)
        setattr(inst, xtba_key, value)

    # parse input to set incoming data to related attributes.
    for c in element:
        key = c.tag.split('}')[-1]
        frequencies[key] += 1

        member = flat_type_info.get(key, None)
        if member is None:
            member, key = cls._type_info_alt.get(key, (None, key))
            if member is None:
                member, key = cls._type_info_alt.get(c.tag, (None, key))
                if member is None:
                    continue

        mo = member.Attributes.max_occurs
        if mo > 1:
            value = getattr(inst, key, None)
            if value is None:
                value = []

            value.append(prot.from_element(member, c))

        else:
            value = prot.from_element(member, c)

        setattr(inst, key, value)

        for key, value_str in c.attrib.items():
            member = flat_type_info.get(key, None)
            if member is None:
                member, key = cls._type_info_alt.get(key, (None, key))
                if member is None:
                    continue

            if (not issubclass(member, XmlAttribute)) or \
                                                     member.attribute_of == key:
                continue

            if mo > 1:
                value = getattr(inst, key, None)
                if value is None:
                    value = []

                value.append(prot.from_string(member.type, value_str))

            else:
                value = prot.from_string(member.type, value_str)

            setattr(inst, key, value)

    for key, value_str in element.attrib.items():
        member = flat_type_info.get(key, None)
        if member is None:
            member, key = cls._type_info_alt.get(key, (None, key))
            if member is None:
                continue

        if (not issubclass(member, XmlAttribute)) or member.attribute_of == key:
            continue

        if issubclass(member.type, (ByteArray, File)):
            value = prot.from_string(member.type, value_str,
                                                   prot.default_binary_encoding)
        else:
            value = prot.from_string(member.type, value_str)

        setattr(inst, key, value)

    if prot.validator is prot.SOFT_VALIDATION:
        for key, c in flat_type_info.items():
            val = frequencies.get(key, 0)
            if (val < c.Attributes.min_occurs or val > c.Attributes.max_occurs):
                raise Fault('Client.ValidationError',
                    '%r member does not respect frequency constraints.' % key)

    return inst


def array_from_element(prot, cls, element):
    retval = [ ]
    (serializer,) = cls._type_info.values()

    for child in element.getchildren():
        retval.append(prot.from_element(serializer, child))

    return retval


def iterable_from_element(prot, cls, element):
    (serializer,) = cls._type_info.values()

    for child in element.getchildren():
        yield prot.from_element(serializer, child)


def enum_from_element(prot, cls, element):
    if prot.validator is prot.SOFT_VALIDATION and not (
                                        cls.validate_string(cls, element.text)):
        raise ValidationError(element.text)
    return getattr(cls, element.text)


def fault_from_element(prot, cls, element):
    code = element.find('faultcode').text
    string = element.find('faultstring').text
    factor = element.find('faultactor')
    if factor is not None:
        factor = factor.text
    detail = element.find('detail')

    return cls(faultcode=code, faultstring=string, faultactor=factor,
                                                                  detail=detail)


def xml_from_element(prot, cls, element):
    children = element.getchildren()
    retval = None

    if children:
        retval = element.getchildren()[0]

    return retval


def dict_from_element(prot, cls, element):
    children = element.getchildren()
    if children:
        return etree_to_dict(element)

    return None


def unicode_from_element(prot, cls, element):
    if prot.validator is prot.SOFT_VALIDATION and not (
                                        cls.validate_string(cls, element.text)):
        raise ValidationError(element.text)

    s = element.text
    if s is None:
        s = ''

    retval = prot.from_string(cls, s)

    if prot.validator is prot.SOFT_VALIDATION and not (
                                              cls.validate_native(cls, retval)):
        raise ValidationError(retval)

    return retval
