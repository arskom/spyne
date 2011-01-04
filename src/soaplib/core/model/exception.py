
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

from soaplib.core import namespaces
from lxml import etree
from soaplib.core.model import Base

_ns_xsd = namespaces.ns_xsd
_pref_soap_env = namespaces.const_prefmap[namespaces.ns_soap_env]

class Fault(Exception, Base):
    __type_name__ = "Fault"

    def __init__(self, faultcode='Server', faultstring="",
                 faultactor="", detail=None):
        if faultcode.startswith('%s:' % _pref_soap_env):
            self.faultcode = faultcode
        else:
            self.faultcode = '%s:%s' % (_pref_soap_env, faultcode)

        self.faultstring = faultstring or self.get_type_name()
        self.faultactor = faultactor
        self.detail = detail

    def __repr__(self):
        return "%s: %r" % (self.faultcode, self.faultstring)

    @classmethod
    def to_parent_element(cls, value, tns, parent_elt, name=None):
        assert name is None
        element = etree.SubElement(parent_elt,
                                   "{%s}Fault" % namespaces.ns_soap_env)

        etree.SubElement(element, 'faultcode').text = value.faultcode
        etree.SubElement(element, 'faultstring').text = value.faultstring
        etree.SubElement(element, 'faultactor').text = value.faultactor
        if value.detail != None:
            etree.SubElement(element, 'detail').append(value.detail)

    def add_to_parent_element(self, tns, parent):
        self.__class__.to_parent_element(self, tns, parent, name=None)

    @classmethod
    def from_xml(cls, element):
        code = element.find('faultcode').text
        string = element.find('faultstring').text
        factor = element.find('faultactor').text
        detail = element.find('detail')

        return cls(faultcode=code, faultstring=string,
                   faultactor=factor, detail=detail)

    @classmethod
    def add_to_schema(cls, schema_dict):
        app = schema_dict.app
        complex_type = etree.Element('{%s}complexType' % _ns_xsd)
        complex_type.set('name', '%sFault' % cls.get_type_name())

        extends = getattr(cls, '__extends__', None)
        if extends is not None:
            complex_content = etree.SubElement(complex_type,
                                            '{%s}complexContent' % _ns_xsd)
            extension = etree.SubElement(complex_content, "{%s}extension"
                                                            % namespaces.ns_xsd)
            extension.set('base', extends.get_type_name_ns(app))
            sequence_parent = extension
        else:
            sequence_parent = complex_type

        seq = etree.SubElement(sequence_parent, '{%s}sequence' % _ns_xsd)

        schema_dict.add_complex_type(cls, complex_type)

        top_level_element = etree.Element('{%s}element' % _ns_xsd)
        top_level_element.set('name', cls.get_type_name())
        top_level_element.set('{%s}type' % _ns_xsd,
                              '%sFault' % cls.get_type_name_ns(app))

        schema_dict.add_element(cls, top_level_element)
