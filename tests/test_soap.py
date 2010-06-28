
#
# soaplib - Copyright (C) 2009 Aaron Bickell, Jamie Kirkpatrick
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

from soaplib.serializers.primitive import Array
from soaplib.serializers.primitive import DateTime
from soaplib.serializers.primitive import Float
from soaplib.serializers.primitive import Integer
from soaplib.serializers.primitive import String

from soaplib.soap import Message
from soaplib.soap import from_soap
from soaplib.soap import make_soap_envelope
from soaplib.soap import make_soap_fault

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
        m = Message.c(
            namespace=None,
            type_name='myMessage',
            members={'s': String, 'i': Integer}
        )

        m_inst = m(s="a", i=43)
        e = m.to_xml(m_inst)

        self.assertEquals(e.tag, 'myMessage')

        self.assertEquals(e.getchildren()[0].tag, 's')
        self.assertEquals(e.getchildren()[1].tag, 'i')

        self.assertEquals(e.getchildren()[0].text, 'a')
        self.assertEquals(e.getchildren()[1].text, '43')

        values = m.from_xml(e)

        self.assertEquals('a', values[0])
        self.assertEquals(43, values[1])

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

        payload, header = from_soap(a)
        # quick and dirty test href reconstruction
        self.assertEquals(len(payload.getchildren()[0].getchildren()), 2)

    def test_namespaces(self):
        m = Message.c(
            namespace="some_namespace",
            type_name='myMessage',
            members={'s': String, 'i': Integer}
        )

        e = m.to_xml('a')
        self.assertEquals(e.tag, '{some_namespace}myMessage')

        m1 = Message.c(
            namespace="some_namespace",
            type_name='myMessage',
            members={'{some_namespace}s': String, 'i': Integer}
        )
        e2 = m1.to_xml('a', 43)
        self.assertEquals(e2.nsmap[None], 'some_namespace')

    def test_class_to_xml(self):
        m = Message.c(
            namespace=None,
            type_name='myMessage',
            members={'p': Person}
        )

        p = Person()
        p.name = 'steve-o'
        p.age = 2

        element = m.to_xml(p)

        self.assertEquals(element.tag, 'myMessage')
        self.assertEquals(element.getchildren()[0].find('name').text,
            'steve-o')
        self.assertEquals(element.getchildren()[0].find('age').text, '2')
        self.assertEquals(
            len(element.getchildren()[0].find('addresses').getchildren()), 0)

        p1 = m.from_xml(element)[0]

        self.assertEquals(p1.name, p.name)
        self.assertEquals(p1.age, p.age)
        self.assertEquals(p1.addresses, [])

    def test_to_xml_nested(self):
        m = Message.c(
            namespace=None,
            type_name='myMessage',
            members={'p':Person}
        )

        p = Person()
        p.name = 'steve-o'
        p.age = 2
        p.addresses = []

        for i in range(0, 1000):
            a = Address()
            a.street = '123 happy way'
            a.zip = i
            a.laditude = '45.22'
            a.longitude = '444.234'
            p.addresses.append(a)

        element = m.to_xml(p)

        self.assertEquals('myMessage', element.tag)

        addresses = element.getchildren()[0].find('addresses').getchildren()
        self.assertEquals(1000, len(addresses))
        self.assertEquals('0', addresses[0].find('zip').text)

    def test_soap_envelope(self):
        m = Message.c(
            namespace=None,
            type_name='myMessage',
            members={'p': Person}
        )
        env = make_soap_envelope(m.to_xml(Person()))

        self.assertTrue(env.tag.endswith('Envelope'))
        self.assertTrue(env.getchildren()[0].tag.endswith('Body'))

        m = Message.c(
            namespace=None,
            type_name='myMessage',
            members={'p': Person}
        )
        env = make_soap_envelope(m.to_xml(Person()),
            header_elements=[etree.Element('header1'), etree.Element('header2')])

        env = etree.fromstring(etree.tostring(env))

        self.assertTrue(env.getchildren()[0].tag.endswith('Header'))
        self.assertEquals(len(env.getchildren()[0].getchildren()), 2)
        self.assertTrue(env.getchildren()[1].tag.endswith('Body'))

    def test_soap_fault(self):
        fault = make_soap_fault('something happened')
        fault = etree.fromstring(etree.tostring(fault))

        self.assertTrue(fault.getchildren()[0].tag.endswith, 'Body')
        self.assertTrue(
            fault.getchildren()[0].getchildren()[0].tag.endswith('Fault'))
        f = fault.getchildren()[0].getchildren()[0]

        self.assertEquals(f.find('faultstring').text, 'something happened')
        self.assertEquals(f.find('faultcode').text, 'Server')
        self.assertEquals(f.find('detail').text, None)

        fault = make_soap_fault('something happened', 'DatabaseError',
            'error on line 12')

        fault = etree.fromstring(etree.tostring(fault))

        f = fault.getchildren()[0].getchildren()[0]
        self.assertEquals(f.find('faultstring').text, 'something happened')
        self.assertEquals(f.find('faultcode').text, 'DatabaseError')
        self.assertEquals(f.find('detail').text, 'error on line 12')

def test_suite():
    loader = unittest.TestLoader()
    return loader.loadTestsFromTestCase(TestSoap)

if __name__== '__main__':
    unittest.TextTestRunner().run(test_suite())
