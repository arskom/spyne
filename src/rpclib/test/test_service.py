#!/usr/bin/env python
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

#
# Most of the service tests are performed through the interop tests.
#
import datetime
import unittest

from rpclib.interface.wsdl import Wsdl11
from rpclib.protocol.soap import Soap11

from lxml import etree

from rpclib.application import Application
from rpclib.decorator import rpc
from rpclib.service import ServiceBase
from rpclib.model.complex import Array
from rpclib.model.complex import ComplexModel
from rpclib.model.primitive import DateTime
from rpclib.model.primitive import Float
from rpclib.model.primitive import Integer
from rpclib.model.primitive import String

Application.transport = 'test'


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
    def a(self, t1, t2):
        return "OK"

class MultipleNamespaceValidatingService(MultipleNamespaceService):
    def __init__(self):
        MultipleNamespaceService.__init__(self)

        self.validating_service = True

class TestService(ServiceBase):
    @rpc(String, _returns=String)
    def aa(self, s):
        return s

    @rpc(String, Integer, _returns=DateTime)
    def a(self, s, i):
        return datetime.datetime.now()

    @rpc(Person, String, Address, _returns=Address)
    def b(self, p, s, a):
        return Address()

    @rpc(Person, isAsync=True)
    def d(self, Person):
        pass

    @rpc(Person, isCallback=True)
    def e(self, Person):
        pass

    @rpc(String, String, String, _returns=String,
        _in_variable_names={'_from': 'from', '_self': 'self',
            '_import': 'import'},
        _out_variable_name="return")
    def f(self, _from, _self, _import):
        return '1234'

class MultipleReturnService(ServiceBase):
    @rpc(String, _returns=(String, String, String))
    def multi(self, s):
        return s, 'a', 'b'

class TestSingle(unittest.TestCase):
    def setUp(self):
        self.app = Application([TestService], 'tns', Wsdl11(), Soap11(), Soap11())
        self.srv = TestService()

        self.app.interface.build_interface_document('URL')
        self.wsdl_str = self.app.interface.get_interface_document()
        self.wsdl_doc = etree.fromstring(self.wsdl_str)

    def test_portypes(self):
        porttype = self.wsdl_doc.find('{http://schemas.xmlsoap.org/wsdl/}portType')
        self.assertEquals(
            len(self.srv.public_methods), len(porttype.getchildren()))

    def test_override_param_names(self):
        # FIXME: This test must be rewritten.

        for n in ['self', 'import', 'return', 'from']:
            self.assertTrue(n in self.wsdl_str, '"%s" not in self.wsdl_str' % n)

class TestMultiple(unittest.TestCase):
    def setUp(self):
        self.app = Application([MultipleReturnService], 'tns', Wsdl11(), Soap11(), Soap11())
        self.app.interface.build_interface_document('url')

    def test_multiple_return(self):
        message_class = MultipleReturnService.public_methods.values()[0].out_message
        message = message_class()

        self.assertEquals(len(message._type_info), 3)

        sent_xml = etree.Element('test')
        self.app.out_protocol.to_parent_element(message_class, ('a','b','c'),
                                    MultipleReturnService.get_tns(), sent_xml)
        sent_xml = sent_xml[0]

        print etree.tostring(sent_xml, pretty_print=True)
        response_data = self.app.out_protocol.from_element(message_class, sent_xml)

        self.assertEquals(len(response_data), 3)
        self.assertEqual(response_data[0], 'a')
        self.assertEqual(response_data[1], 'b')
        self.assertEqual(response_data[2], 'c')

if __name__ == '__main__':
    unittest.main()
