
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

import cStringIO
import soaplib
from lxml import etree
from soaplib.serializers import Base

_ns_xs = soaplib.nsmap['xs']
_ns_xsi = soaplib.nsmap['xsi']

class Fault(Exception, Base):
    def __init__(self, faultcode = 'Server', faultstring = None,
                 detail = None, name = 'ExceptionFault'):
        self.faultcode = faultcode
        self.faultstring = faultstring
        self.detail = detail
        self.name = name

    @classmethod
    def to_xml(cls, value, tns, name):
        fault = etree.Element("{%s}%s" % (tns,name))

        etree.SubElement(fault, '{%s}faultcode' % tns).text = value.faultcode
        etree.SubElement(fault, '{%s}faultstring' % tns).text = value.faultstring
        etree.SubElement(fault, '{%s}detail' % tns).text = value.detail

        return fault

    @classmethod
    def from_xml(cls, element):
        code = element.find('faultcode').text
        string = element.find('faultstring').text
        detail_element = element.find('detail')
        if detail_element is not None:
            if len(detail_element.getchildren()):
                detail = etree.tostring(detail_element)
            else:
                detail = element.find('detail').text
        else:
            detail = ''
        return Fault(faultcode=code, faultstring=string, detail=detail)

    @classmethod
    def add_to_schema(cls, schema_dict):
        complex_type = etree.Element('complexType')
        complex_type.set('name', cls.get_datatype())
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

    def __str__(self):
        io = cStringIO.StringIO()
        io.write("*" * 80)
        io.write("\r\n")
        io.write(" Recieved soap fault \r\n")
        io.write(" FaultCode            %s \r\n" % self.faultcode)
        io.write(" FaultString          %s \r\n" % self.faultstring)
        io.write(" FaultDetail          \r\n")

        if self.detail is not None:
            io.write(self.detail)

        return io.getvalue()
