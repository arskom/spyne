
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

from lxml import etree
from collections import defaultdict

from spyne.const.xml_ns import xsi as _ns_xsi
from spyne.const.xml_ns import soap_env as _ns_soap_env
from spyne.error import Fault
from spyne.error import ValidationError
from spyne.model.complex import XmlAttribute
from spyne.util.etreeconv import etree_to_dict
from spyne.util.etreeconv import dict_to_etree

import spyne.const.xml_ns
_pref_soap_env = spyne.const.xml_ns.const_prefmap[_ns_soap_env]

"""The ``spyne.protocol.xml.model`` module contains type-specific serialization
logic.
"""

def nillable_value(func):
    def wrapper(prot, cls, value, tns, parent_elt, *args, **kwargs):
        if value is None:
            if cls.Attributes.default is None:
                null_to_parent_element(prot, cls, value, tns, parent_elt,
                                                                *args, **kwargs)
            else:
                func(prot, cls, cls.Attributes.default, tns, parent_elt,
                                                                *args, **kwargs)
        else:
            func(prot, cls, value, tns, parent_elt, *args, **kwargs)
    return wrapper


def nillable_element(func):
    def wrapper(prot, cls, element):
        if bool(element.get('{%s}nil' % _ns_xsi)):
            if prot.validator is prot.SOFT_VALIDATION and not \
                                                      cls.Attributes.nillable:
                raise ValidationError('')
            else:
                return cls.Attributes.default
        else:
            return func(prot, cls, element)
    return wrapper


def TBaseFromElement(callable):
    @nillable_element
    def base_from_element(prot, cls, element):
        if prot.validator is prot.SOFT_VALIDATION and not (
                                            cls.validate_string(cls, element.text)):
            raise ValidationError(element.text)

        retval = callable(cls, element.text)

        if prot.validator is prot.SOFT_VALIDATION and not (
                                            cls.validate_native(cls, retval)):
            raise ValidationError(retval)
        return retval

    return base_from_element

base_from_element = TBaseFromElement(lambda cls, s: cls.from_string(s))

@nillable_value
def base_to_parent_element(prot, cls, value, tns, parent_elt, name='retval'):
    '''Creates a lxml.etree SubElement as a child of a 'parent' Element

    :param prot:  The protocol that will be used to serialize the given value.
    :param cls:   The type of the value that's going to determine how to pack
                  the given value.
    :param value: The value to be set for the 'text' element of the newly
                  created SubElement
    :param tns:   The target namespace of the new SubElement, used with 'name'
                  to set the tag.
    :param parent_elt: The parent Element to which the new child will be
                  appended.
    :param name:  The tag name of the new SubElement, 'retval' by default.
    '''

    elt = etree.SubElement(parent_elt, "{%s}%s" % (tns, name))
    elt.text = cls.to_string(value)


def null_to_parent_element(prot, cls, value, tns, parent_elt, name='retval'):
    element = etree.SubElement(parent_elt, "{%s}%s" % (tns, name))
    element.set('{%s}nil' % _ns_xsi, 'true')


def null_from_element(prot, cls, element):
    return None


@nillable_value
def binary_to_parent_element(prot, cls, value, tns, parent_elt, name='retval'):
    '''This class method takes the data from the attachment and
    base64 encodes it as the text of an Element. An attachment can
    specify a file_name and if no data is given, it will read the data
    from the file
    '''
    element = etree.SubElement(parent_elt, "{%s}%s" % (tns, name))
    element.text = ''.join([b.decode('ascii') for b in cls.to_base64(value)])


@nillable_element
def binary_from_element(prot, cls, element):
    '''This method returns an Attachment object that contains
    the base64 decoded string of the text of the given element
    '''
    return cls.from_base64([element.text])


def get_members_etree(prot, cls, inst, parent):
    delay = set()
    parent_cls = getattr(cls, '__extends__', None)
    if not (parent_cls is None):
        get_members_etree(prot, parent_cls, inst, parent)

    for k, v in cls._type_info.items():
        try:
            subvalue = getattr(inst, k, None)
        except: # to guard against sqlalchemy throwing NoSuchColumnError
            subvalue = None

        # This is a tight loop, so enable this only when necessary.
        # logger.debug("get %r(%r) from %r: %r" % (k, v, inst, subvalue))

        if issubclass(v, XmlAttribute):
            a_of = v._attribute_of
            if a_of is not None and a_of in cls._type_info.keys():
                attr_parent=parent.find("{%s}%s"%(cls.__namespace__,a_of))
                if attr_parent is None:
                    delay.add(k)
                else:
                    v.marshall(k,subvalue,attr_parent)
            else:
                v.marshall(k, subvalue, parent)
            continue

        mo = v.Attributes.max_occurs
        if subvalue is not None and mo > 1:
            for sv in subvalue:
                prot.to_parent_element(v, sv, cls.get_namespace(), parent, k)

        # Don't include empty values for non-nillable optional attributes.
        elif subvalue is not None or v.Attributes.min_occurs > 0:
            prot.to_parent_element(v, subvalue, cls.get_namespace(), parent, k)

    for k in delay:
        v = cls._type_info[k]
        subvalue = getattr(inst, k, None)
        a_of = v._attribute_of
        attr_parent = parent.find("{%s}%s"%(cls.__namespace__,a_of))
        v.marshall(k,subvalue,attr_parent)


@nillable_value
def complex_to_parent_element(prot, cls, value, tns, parent_elt, name=None):
    if name is None:
        name = cls.get_type_name()
    element = etree.SubElement(parent_elt, "{%s}%s" % (tns, name))
    inst = cls.get_serialization_instance(value)
    get_members_etree(prot, cls, inst, element)


@nillable_value
def alias_to_parent_element(prot, cls, value, tns, parent_elt, name=None):
    if name is None:
        name = cls.get_type_name()

    (k,t), = cls._type_info.items()
    if t is not None:
        subvalue = getattr(value, k, None)
        # Don't include empty values for non-nillable optional attributes.
        if subvalue is not None:
            prot.to_parent_element(t, subvalue, tns, parent_elt, name)


@nillable_element
def alias_from_element(prot, cls, element):
    t, = cls._type_info.values()
    if t is not None:
        return prot.from_element(t, element)


@nillable_element
def complex_from_element(prot, cls, element):
    inst = cls.get_deserialization_instance()

    flat_type_info = cls.get_flat_type_info(cls)

    # this is for validating cls.Attributes.{min,max}_occurs
    frequencies = defaultdict(int)

    # parse input to set incoming data to related attributes.
    for c in element:
        key = c.tag.split('}')[-1]
        frequencies[key] += 1

        member = flat_type_info.get(key, None)
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

    for key in element.attrib:
        member = flat_type_info.get(key, None)
        if member is None:
            continue

        value = member._typ.from_string(element.attrib[key])

        setattr(inst, key, value)

    if prot.validator is prot.SOFT_VALIDATION:
        for key, c in flat_type_info.items():
            val = frequencies.get(key, 0)
            if (val < c.Attributes.min_occurs or val > c.Attributes.max_occurs):
                raise Fault('Client.ValidationError',
                    '%r member does not respect frequency constraints.' % key)

    return inst


@nillable_element
def array_from_element(prot, cls, element):
    retval = [ ]
    (serializer,) = cls._type_info.values()

    for child in element.getchildren():
        retval.append(prot.from_element(serializer, child))

    return retval


@nillable_element
def iterable_from_element(prot, cls, element):
    (serializer,) = cls._type_info.values()

    for child in element.getchildren():
        yield prot.from_element(serializer, child)


@nillable_value
def enum_to_parent_element(prot, cls, value, tns, parent_elt, name='retval'):
    if name is None:
        name = cls.get_type_name()
    base_to_parent_element(prot, cls, str(value), tns, parent_elt, name)


@nillable_element
def enum_from_element(prot, cls, element):
    if prot.validator is prot.SOFT_VALIDATION and not (
                                        cls.validate_string(cls, element.text)):
        raise ValidationError(element.text)
    return getattr(cls, element.text)


def fault_to_parent_element(prot, cls, value, tns, parent_elt, name=None):
    element = etree.SubElement(parent_elt, "{%s}Fault" % _ns_soap_env)

    etree.SubElement(element, 'faultcode').text = '%s:%s' % (_pref_soap_env,
                                                                value.faultcode)
    etree.SubElement(element, 'faultstring').text = value.faultstring
    etree.SubElement(element, 'faultactor').text = value.faultactor
    if value.detail != None:
        etree.SubElement(element, 'detail').append(value.detail)


def fault_from_element(prot, cls, element):
    code = element.find('faultcode').text
    string = element.find('faultstring').text
    factor = element.find('faultactor')
    if factor is not None:
        factor = factor.text
    detail = element.find('detail')

    return cls(faultcode=code, faultstring=string, faultactor=factor,
                                                                  detail=detail)


@nillable_element
def xml_from_element(prot, cls, element):
    children = element.getchildren()
    retval = None

    if children:
        retval = element.getchildren()[0]

    return retval


@nillable_value
def xml_to_parent_element(prot, cls, value, tns, parent_elt, name='retval'):
    if isinstance(value, str) or isinstance(value, unicode):
        value = etree.fromstring(value)

    e = etree.SubElement(parent_elt, '{%s}%s' % (tns, name))
    e.append(value)


@nillable_value
def dict_to_parent_element(prot, cls, value, tns, parent_elt, name='retval'):
    e = etree.SubElement(parent_elt, '{%s}%s' % (tns, name))
    dict_to_etree(value, e)


@nillable_element
def dict_from_element(prot, cls, element):
    children = element.getchildren()
    if children:
        return etree_to_dict(element)

    return None


@nillable_element
def unicode_from_element(prot, cls, element):
    if prot.validator is prot.SOFT_VALIDATION and not (
                                        cls.validate_string(cls, element.text)):
        raise ValidationError(element.text)

    s = element.text
    if s is None:
        s = ''

    retval = cls.from_string(s)

    if prot.validator is prot.SOFT_VALIDATION and not (
                                        cls.validate_native(cls, retval)):
        raise ValidationError(retval)
    return retval
