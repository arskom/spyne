
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

import rpclib.const.xml_ns

from rpclib.error import ValidationError
from lxml import etree

_ns_xsi = rpclib.const.xml_ns.xsi
_ns_xsd = rpclib.const.xml_ns.xsd

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
            if prot.validator is prot.SOFT_VALIDATION and (
                        not cls.Attributes.nillable or
                                    cls.Attributes._has_non_nillable_children):
                raise ValidationError('')
            else:
                return cls.Attributes.default
        else:
            return func(prot, cls, element)
    return wrapper

@nillable_element
def base_from_element(prot, cls, element):
    if prot.validator is prot.SOFT_VALIDATION and not (
                                        cls.validate_string(cls, element.text)):
        raise ValidationError(element.text)
    retval = cls.from_string(element.text)
    if prot.validator is prot.SOFT_VALIDATION and not (
                                        cls.validate_native(cls, retval)):
        raise ValidationError(element.text)
    return retval

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
