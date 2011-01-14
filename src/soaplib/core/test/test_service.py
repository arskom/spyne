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

import datetime
import unittest

from lxml import etree

from soaplib.core.model.clazz import ClassModel
from soaplib.core.model.clazz import Array
from soaplib.core.model.primitive import DateTime
from soaplib.core.model.primitive import Float
from soaplib.core.model.primitive import Integer
from soaplib.core.model.primitive import String

from soaplib.core import service
from soaplib.core import Application
Application.transport = 'test'

from soaplib.core.service import soap

class Address(ClassModel):
    __namespace__ = "TestService"

    street = String
    city = String
    zip = Integer
    since = DateTime
    laditude = Float
    longitude = Float

class Person(ClassModel):
    __namespace__ = "TestService"

    name = String
    birthdate = DateTime
    age = Integer
    addresses = Array(Address)
    titles = Array(String)

class Request(ClassModel):
    __namespace__ = "TestService"

    param1 = String
    param2 = Integer

class Response(ClassModel):
    __namespace__ = "TestService"

    param1 = Float

class TypeNS1(ClassModel):
    __namespace__ = "TestService.NS1"

    s = String
    i = Integer

class TypeNS2(ClassModel):
    __namespace__ = "TestService.NS2"

    d = DateTime
    f = Float

class MultipleNamespaceService(service.DefinitionBase):
    @soap(TypeNS1, TypeNS2)
    def a(self, t1, t2):
        return "OK"

class MultipleNamespaceValidatingService(MultipleNamespaceService):
    def __init__(self):
        MultipleNamespaceService.__init__(self)

        self.validating_service = True

class TestService(service.DefinitionBase):
    @soap(String, _returns=String)
    def aa(self, s):
        return s

    @soap(String, Integer, _returns=DateTime)
    def a(self, s, i):
        return datetime.datetime.now()

    @soap(Person, String, Address, _returns=Address)
    def b(self, p, s, a):
        return Address()

    @soap(Person, isAsync=True)
    def d(self, Person):
        pass

    @soap(Person, isCallback=True)
    def e(self, Person):
        pass

    @soap(String, String, String, _returns=String,
        _in_variable_names={'_from': 'from', '_self': 'self',
            '_import': 'import'},
        _out_variable_name="return")
    def f(self, _from, _self, _import):
        return '1234'

class MultipleReturnService(service.DefinitionBase):
    @soap(String, _returns=(String, String, String))
    def multi(self, s):
        return s, 'a', 'b'

class Test(unittest.TestCase):
    '''Most of the service tests are performed through the interop tests.'''

    def test_ctor_saves_environ(self):
        environ = {}
        service = TestService(environ)
        self.failUnless(service.environ is environ)

    def test_portypes(self):
        app = Application([TestService], 'tns')
        _wsdl = app.get_wsdl('')
        wsdl = etree.fromstring(_wsdl)
        porttype = wsdl.find('{http://schemas.xmlsoap.org/wsdl/}portType')
        srv = TestService()
        self.assertEquals(
            len(srv.public_methods), len(porttype.getchildren()))

    def test_override_param_names(self):
        app = Application([TestService], 'tns')
        _wsdl = app.get_wsdl('')
        for n in ['self', 'import', 'return', 'from']:
            self.assertTrue(n in _wsdl, '"%s" not in _wsdl' % n)

    def test_multiple_return(self):
        app = Application([MultipleReturnService], 'tns')
        app.get_wsdl('')
        srv = MultipleReturnService()
        message = srv.public_methods[0].out_message()

        self.assertEquals(len(message._type_info), 3)

        sent_xml = etree.Element('test')
        message.to_parent_element( ('a','b','c'), srv.get_tns(), sent_xml )
        sent_xml = sent_xml[0]

        response_data = message.from_xml(sent_xml)

        self.assertEquals(len(response_data), 3)
        self.assertEqual(response_data[0], 'a')
        self.assertEqual(response_data[1], 'b')
        self.assertEqual(response_data[2], 'c')

    def test_multiple_ns(self):
        svc = Application([MultipleNamespaceService], 'tns')
        wsdl = svc.get_wsdl("URL")

if __name__ == '__main__':
    unittest.main()
