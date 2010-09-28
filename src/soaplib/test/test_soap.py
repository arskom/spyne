#!/usr/bin/env python
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

import unittest

from lxml import etree

from soaplib.serializers.clazz import ClassSerializer

from soaplib.serializers.exception import Fault
from soaplib.serializers.clazz import Array
from soaplib.serializers.primitive import DateTime
from soaplib.serializers.primitive import Float
from soaplib.serializers.primitive import Integer
from soaplib.serializers.primitive import String

from soaplib.soap import Message
from soaplib.soap import from_soap

class Address(ClassSerializer):
    street = String
    city = String
    zip = Integer
    since = DateTime
    laditude = Float
    longitude = Float

class Person(ClassSerializer):
    name = String
    birthdate = DateTime
    age = Integer
    addresses = Array(Address)
    titles = Array(String)

class TestSoap(unittest.TestCase):
    def test_simple_message(self):
        m = Message.produce(
            namespace=None,
            type_name='myMessage',
            members={'s': String, 'i': Integer}
        )
        m.resolve_namespace(m,'test')

        m_inst = m(s="a", i=43)

        e = etree.Element('test')
        m.to_xml(m_inst,m.get_namespace(),e)
        e=e[0]
        
        self.assertEquals(e.tag, '{%s}myMessage' % m.get_namespace())

        self.assertEquals(e.find('{%s}s' % m.get_namespace()).text, 'a')
        self.assertEquals(e.find('{%s}i' % m.get_namespace()).text, '43')

        values = m.from_xml(e)

        self.assertEquals('a', values.s)
        self.assertEquals(43, values.i)

    def test_href(self):
        # the template. Start at pos 0, some servers complain if
        # xml tag is not in the first line.
        a = '''<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
xmlns:xsd="http://www.w3.org/2001/XMLSchema"
xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/"
xmlns:tns="http://tempuri.org/"
xmlns:types="http://example.com/encodedTypes"
xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body soap:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
    <tns:myResponse xsi:type="tns:myResponse">
      <myResult href="#id1" />
    </tns:myResponse>
    <soapenc:Array id="id1" soapenc:arrayType="tns:MyData[2]">
      <Item href="#id2" />
      <Item href="#id3" />
    </soapenc:Array>
    <tns:MyData id="id2" xsi:type="tns:MyData">
      <Machine xsi:type="xsd:string">somemachine</Machine>
      <UserName xsi:type="xsd:string">someuser</UserName>
    </tns:MyData>
    <tns:MyData id="id3" xsi:type="tns:MyData">
      <Machine xsi:type="xsd:string">machine2</Machine>
      <UserName xsi:type="xsd:string">user2</UserName>
    </tns:MyData>
  </soap:Body>
</soap:Envelope>'''

        payload, header = from_soap(a, 'utf8')
        # quick and dirty test href reconstruction
        self.assertEquals(len(payload.getchildren()[0].getchildren()), 2)

    def test_namespaces(self):
        m = Message.produce(
            namespace="some_namespace",
            type_name='myMessage',
            members={'s': String, 'i': Integer},
        )

        mi = m()
        mi.s = 'a'

        e = etree.Element('test')
        m.to_xml(mi,m.get_namespace(),e)
        e=e[0]

        self.assertEquals(e.tag, '{some_namespace}myMessage')

    def test_class_to_xml(self):
        m = Message.produce(
            namespace=None,
            type_name='myMessage',
            members={'p': Person}
        )

        m.resolve_namespace(m,"punk")

        m_inst = m()
        m_inst.p = Person()
        m_inst.p.name = 'steve-o'
        m_inst.p.age = 2
        m_inst.p.addresses = []

        element=etree.Element('test')
        m.to_xml(m_inst,m.get_namespace(),element)
        element=element[0]

        self.assertEquals(element.tag, '{%s}myMessage' % m.get_namespace())
        self.assertEquals(element.getchildren()[0].find('{%s}name' % m.get_namespace()).text,
            'steve-o')
        self.assertEquals(element.getchildren()[0].find('{%s}age' % m.get_namespace()).text, '2')
        self.assertEquals(
            len(element.getchildren()[0].find('{%s}addresses' % m.get_namespace()).getchildren()), 0)

        p1 = m.from_xml(element)[0]

        self.assertEquals(p1.name, m_inst.p.name)
        self.assertEquals(p1.age, m_inst.p.age)
        self.assertEquals(p1.addresses, [])

    def test_to_xml_nested(self):
        m = Message.produce(
            namespace=None,
            type_name='myMessage',
            members={'p':Person}
        )

        m.resolve_namespace(m,"m")

        p = Person()
        p.name = 'steve-o'
        p.age = 2
        p.addresses = []

        for i in range(0, 100):
            a = Address()
            a.street = '123 happy way'
            a.zip = i
            a.laditude = '45.22'
            a.longitude = '444.234'
            p.addresses.append(a)

        m_inst = m(p=p)

        element=etree.Element('test')
        m.to_xml(m_inst,m.get_namespace(),element)
        element=element[0]

        #print etree.tostring(element, pretty_print=True)
        self.assertEquals('{%s}myMessage' % m.get_namespace(), element.tag)

        addresses = element.getchildren()[0].find('{%s}addresses' % m.get_namespace()).getchildren()
        self.assertEquals(100, len(addresses))
        self.assertEquals('0', addresses[0].find('{%s}zip' % m.get_namespace()).text)

if __name__ == '__main__':
    unittest.main()
