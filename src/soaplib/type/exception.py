
#
# soaplib - Copyright (C) Soaplib contributors.
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

import soaplib
from lxml import etree
from soaplib.type import Base

_ns_xsi = soaplib.ns_xsi
_pref_soap_env = soaplib.const_prefmap[soaplib.ns_soap_env]

class Fault(Exception, Base):
    __type_name__ = "Fault"

    def __init__(self, faultcode='Server', faultstring="", faultactor="",
                                                                detail=None):
        if faultcode.startswith('%s:' % _pref_soap_env):
            self.faultcode = faultcode
        else:
            self.faultcode = '%s:%s' % (_pref_soap_env, faultcode)

        self.faultstring = faultstring
        self.faultactor = faultactor
        self.detail = detail

    def __repr__(self):
        return "%s: %r" % (self.faultcode, self.faultstring)

    @classmethod
    def to_xml(cls, value, tns, parent_elt, name=None):
        if name is None:
            name = cls.get_type_name()
        element = etree.SubElement(parent_elt, "{%s}%s" %
                                                    (soaplib.ns_soap_env,name))

        etree.SubElement(element, 'faultcode').text = value.faultcode
        etree.SubElement(element, 'faultstring').text = value.faultstring
        etree.SubElement(element, 'faultactor').text = value.faultactor
        if value.detail != None:
            etree.SubElement(element, 'detail').append(value.detail)

    @classmethod
    def from_xml(cls, element):
        code = element.find('faultcode').text
        string = element.find('faultstring').text
        factor = element.find('faultactor').text
        detail = element.find('detail')

        return cls(faultcode=code, faultstring=string, faultactor=factor,
                                                                detail=detail)

    @classmethod
    def add_to_schema(cls, schema_dict):
        complex_type = etree.Element('complexType')
        complex_type.set('name', cls.get_type_name())
        sequenceNode = etree.SubElement(complex_type, 'sequence')

        element = etree.SubElement(sequenceNode, 'element')
        element.set('name', 'detail')
        element.set('{%s}type' % _ns_xsi, 'xs:string')

        element = etree.SubElement(sequenceNode, 'element')
        element.set('name', 'message')
        element.set('{%s}type' % _ns_xsi, 'xs:string')

        schema_dict.add_complex_type(cls, complex_type)

        top_level_element = etree.Element('element')
        top_level_element.set('name', 'ExceptionFaultType')
        top_level_element.set('{%s}type' % _ns_xsi, cls.get_type_name_ns())

        schema_dict.add_element(cls, top_level_element)
