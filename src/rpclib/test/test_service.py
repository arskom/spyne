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

import datetime
import unittest

import rpclib.interface.wsdl
import rpclib.protocol.soap

from lxml import etree

from rpclib import Application
from rpclib import service
from rpclib.model.clazz import Array
from rpclib.model.clazz import ClassSerializer
from rpclib.model.primitive import DateTime
from rpclib.model.primitive import Float
from rpclib.model.primitive import Integer
from rpclib.model.primitive import String

Application.transport = 'test'

from rpclib.service import rpc

class Address(ClassSerializer):
    __namespace__ = "TestService"

    street = String
    city = String
    zip = Integer
    since = DateTime
    laditude = Float
    longitude = Float

class Person(ClassSerializer):
    __namespace__ = "TestService"

    name = String
    birthdate = DateTime
    age = Integer
    addresses = Array(Address)
    titles = Array(String)

class Request(ClassSerializer):
    __namespace__ = "TestService"

    param1 = String
    param2 = Integer

class Response(ClassSerializer):
    __namespace__ = "TestService"

    param1 = Float

class TypeNS1(ClassSerializer):
    __namespace__ = "TestService.NS1"

    s = String
    i = Integer

class TypeNS2(ClassSerializer):
    __namespace__ = "TestService.NS2"

    d = DateTime
    f = Float

class MultipleNamespaceService(service.DefinitionBase):
    @rpc(TypeNS1, TypeNS2)
    def a(self, t1, t2):
        return "OK"

class MultipleNamespaceValidatingService(MultipleNamespaceService):
    def __init__(self):
        MultipleNamespaceService.__init__(self)

        self.validating_service = True

class TestService(service.DefinitionBase):
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

class MultipleReturnService(service.DefinitionBase):
    @rpc(String, _returns=(String, String, String))
    def multi(self, s):
        return s, 'a', 'b'

class Test(unittest.TestCase):
    '''Most of the service tests are performed through the interop tests.'''

    def setUp(self):
        self.app = Application([TestService], rpclib.interface.wsdl.Wsdl11,
                                        rpclib.protocol.soap.Soap11, tns='tns')
        self.srv = TestService()
        self._wsdl = self.app.interface.get_interface_document('')
        self.wsdl = etree.fromstring(self._wsdl)

    def test_portypes(self):
        porttype = self.wsdl.find('{http://schemas.xmlsoap.org/wsdl/}portType')
        self.assertEquals(
            len(self.srv.public_methods), len(porttype.getchildren()))

    def test_override_param_names(self):
        for n in ['self', 'import', 'return', 'from']:
            self.assertTrue(n in self._wsdl, '"%s" not in self._wsdl' % n)

    def test_multiple_return(self):
        app = Application([MultipleReturnService], rpclib.interface.wsdl.Wsdl11,
                                        rpclib.protocol.soap.Soap11, tns='tns')
        app.interface.get_interface_document('')
        srv = MultipleReturnService()
        message = srv.public_methods[0].out_message()

        self.assertEquals(len(message._type_info), 3)

        sent_xml = etree.Element('test')
        message.to_parent_element( ('a','b','c'), srv.get_tns(), sent_xml )
        sent_xml = sent_xml[0]

        print etree.tostring(sent_xml, pretty_print=True)
        response_data = message.from_xml(sent_xml)

        self.assertEquals(len(response_data), 3)
        self.assertEqual(response_data[0], 'a')
        self.assertEqual(response_data[1], 'b')
        self.assertEqual(response_data[2], 'c')

    def test_multiple_ns(self):
        svc = Application([MultipleNamespaceService],rpclib.interface.wsdl.Wsdl11,
                                         rpclib.protocol.soap.Soap11,tns='tns')
        wsdl = svc.interface.get_interface_document("URL")

if __name__ == '__main__':
    unittest.main()
