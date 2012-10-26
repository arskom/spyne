#!/usr/bin/env python
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

#
# Most of the service tests are performed through the interop tests.
#

import datetime
import unittest

from lxml import etree

from spyne.application import Application
from spyne.decorator import rpc
from spyne.interface.wsdl import Wsdl11
from spyne.model.complex import Array
from spyne.model.complex import ComplexModel
from spyne.model.primitive import DateTime
from spyne.model.primitive import Float
from spyne.model.primitive import Integer
from spyne.model.primitive import String
from spyne.protocol.soap import Soap11
from spyne.service import ServiceBase

from spyne.protocol.soap import _from_soap
from spyne.protocol.soap import _parse_xml_string

Application.transport = 'test'


def start_response(code, headers):
    print(code, headers)


class Address(ComplexModel):
    __namespace__ = "TestService"

    street = String
    city = String
    zip = Integer
    since = DateTime
    laditude = Float
    longitude = Float

class Person(ComplexModel):
    __namespace__ = "TestService"

    name = String
    birthdate = DateTime
    age = Integer
    addresses = Array(Address)
    titles = Array(String)

class Request(ComplexModel):
    __namespace__ = "TestService"

    param1 = String
    param2 = Integer

class Response(ComplexModel):
    __namespace__ = "TestService"

    param1 = Float

class TypeNS1(ComplexModel):
    __namespace__ = "TestService.NS1"

    s = String
    i = Integer

class TypeNS2(ComplexModel):
    __namespace__ = "TestService.NS2"

    d = DateTime
    f = Float

class MultipleNamespaceService(ServiceBase):
    @rpc(TypeNS1, TypeNS2)
    def a(ctx, t1, t2):
        return "OK"

class TestService(ServiceBase):
    @rpc(String, _returns=String)
    def aa(ctx, s):
        return s

    @rpc(String, Integer, _returns=DateTime)
    def a(ctx, s, i):
        return datetime.datetime.now()

    @rpc(Person, String, Address, _returns=Address)
    def b(ctx, p, s, a):
        return Address()

    @rpc(Person, isAsync=True)
    def d(ctx, Person):
        pass

    @rpc(Person, isCallback=True)
    def e(ctx, Person):
        pass

    @rpc(String, String, String, _returns=String,
        _in_variable_names={'_from': 'from', '_self': 'self',
            '_import': 'import'},
        _out_variable_name="return")
    def f(ctx, _from, _self, _import):
        return '1234'

class MultipleReturnService(ServiceBase):
    @rpc(String, _returns=(String, String, String))
    def multi(ctx, s):
        return s, 'a', 'b'

class TestSingle(unittest.TestCase):
    def setUp(self):
        self.app = Application([TestService], 'tns', in_protocol=Soap11(), out_protocol=Soap11())
        self.app.transport = 'null.spyne'
        self.srv = TestService()

        wsdl = Wsdl11(self.app.interface)
        wsdl.build_interface_document('URL')
        self.wsdl_str = wsdl.get_interface_document()
        self.wsdl_doc = etree.fromstring(self.wsdl_str)

    def test_portypes(self):
        porttype = self.wsdl_doc.find('{http://schemas.xmlsoap.org/wsdl/}portType')
        self.assertEquals(
            len(self.srv.public_methods), len(porttype.getchildren()))

    def test_override_param_names(self):
        for n in ['self', 'import', 'return', 'from']:
            assert n in self.wsdl_str, '"%s" not in self.wsdl_str'

class TestMultiple(unittest.TestCase):
    def setUp(self):
        self.app = Application([MultipleReturnService], 'tns', in_protocol=Soap11(), out_protocol=Soap11())
        self.app.transport = 'none'
        self.wsdl = Wsdl11(self.app.interface)
        self.wsdl.build_interface_document('URL')

    def test_multiple_return(self):
        message_class = list(MultipleReturnService.public_methods.values())[0].out_message
        message = message_class()

        self.assertEquals(len(message._type_info), 3)

        sent_xml = etree.Element('test')
        self.app.out_protocol.to_parent_element(message_class, ('a', 'b', 'c'),
                                    MultipleReturnService.get_tns(), sent_xml)
        sent_xml = sent_xml[0]

        print((etree.tostring(sent_xml, pretty_print=True)))
        response_data = self.app.out_protocol.from_element(message_class, sent_xml)

        self.assertEquals(len(response_data), 3)
        self.assertEqual(response_data[0], 'a')
        self.assertEqual(response_data[1], 'b')
        self.assertEqual(response_data[2], 'c')


class TestSoap(unittest.TestCase):
    def test_simple_message(self):
        m = ComplexModel.produce(
            namespace=None,
            type_name='myMessage',
            members={'s': String, 'i': Integer}
        )
        m.resolve_namespace(m, 'test')

        m_inst = m(s="a", i=43)

        e = etree.Element('test')
        Soap11().to_parent_element(m, m_inst, m.get_namespace(), e)
        e=e[0]

        self.assertEquals(e.tag, '{%s}myMessage' % m.get_namespace())

        self.assertEquals(e.find('{%s}s' % m.get_namespace()).text, 'a')
        self.assertEquals(e.find('{%s}i' % m.get_namespace()).text, '43')

        values = Soap11().from_element(m, e)

        self.assertEquals('a', values.s)
        self.assertEquals(43, values.i)

    def test_href(self):
        # the template. Start at pos 0, some servers complain if
        # xml tag is not in the first line.
        envelope_string = '''
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

        root, xmlids = _parse_xml_string(envelope_string, 'utf8')
        header, payload = _from_soap(root, xmlids)

        # quick and dirty test href reconstruction
        self.assertEquals(len(payload[0]), 2)

    def test_namespaces(self):
        m = ComplexModel.produce(
            namespace="some_namespace",
            type_name='myMessage',
            members={'s': String, 'i': Integer},
        )

        mi = m()
        mi.s = 'a'

        e = etree.Element('test')
        Soap11().to_parent_element(m, mi, m.get_namespace(), e)
        e=e[0]

        self.assertEquals(e.tag, '{some_namespace}myMessage')

    def test_class_to_parent_element(self):
        m = ComplexModel.produce(
            namespace=None,
            type_name='myMessage',
            members={'p': Person}
        )

        m.resolve_namespace(m, "punk")

        m_inst = m()
        m_inst.p = Person()
        m_inst.p.name = 'steve-o'
        m_inst.p.age = 2
        m_inst.p.addresses = []

        element=etree.Element('test')
        Soap11().to_parent_element(m, m_inst, m.get_namespace(), element)
        element=element[0]

        self.assertEquals(element.tag, '{%s}myMessage' % m.get_namespace())
        self.assertEquals(element[0].find('{%s}name' % Person.get_namespace()).text,
                                                                    'steve-o')
        self.assertEquals(element[0].find('{%s}age' % Person.get_namespace()).text, '2')
        self.assertEquals(
              len(element[0].find('{%s}addresses' % Person.get_namespace())), 0)

        p1 = Soap11().from_element(m,element)[0]

        self.assertEquals(p1.name, m_inst.p.name)
        self.assertEquals(p1.age, m_inst.p.age)
        self.assertEquals(p1.addresses, [])

    def test_to_parent_element_nested(self):
        m = ComplexModel.produce(
            namespace=None,
            type_name='myMessage',
            members={'p':Person}
        )

        m.resolve_namespace(m, "m")

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
        Soap11().to_parent_element(m, m_inst, m.get_namespace(), element)
        element=element[0]

        self.assertEquals('{%s}myMessage' % m.get_namespace(), element.tag)

        addresses = element[0].find('{%s}addresses' % Person.get_namespace())
        self.assertEquals(100, len(addresses))
        self.assertEquals('0', addresses[0].find('{%s}zip' % Address.get_namespace()).text)

if __name__ == '__main__':
    unittest.main()
