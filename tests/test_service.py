
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

import datetime
import unittest

from lxml import etree

from soaplib.serializers.clazz import ClassSerializer
from soaplib.serializers.primitive import Array
from soaplib.serializers.primitive import DateTime
from soaplib.serializers.primitive import Float
from soaplib.serializers.primitive import Integer
from soaplib.serializers.primitive import String

from soaplib.service import ServiceBase
from soaplib.service import rpc

from soaplib.wsgi_soap import SimpleWSGIApp

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

class Request(ClassSerializer):
    param1 = String
    param2 = Integer

class Response(ClassSerializer):
    param1 = Float

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

class TestMultipleReturnService(ServiceBase):
    @rpc(String, _returns=(String, String, String))
    def multi(self, s):
        return s, 'a', 'b'

class OverrideNamespaceService(SimpleWSGIApp):
    __tns__ = "http://someservice.com/override"

    @rpc(String, _returns=String)
    def mymethod(self, s):
        return s

class Test(unittest.TestCase):
    '''
    Most of the service tests are excersized through the interop tests
    '''

    def setUp(self):
        self.service = TestService()
        self._wsdl = self.service.wsdl('')
        self.wsdl = etree.fromstring(self._wsdl)

    def test_portypes(self):
        porttype = self.wsdl.find('{http://schemas.xmlsoap.org/wsdl/}portType')
        self.assertEquals(
            len(self.service._remote_methods), len(porttype.getchildren()))

    def test_override_default_names(self):
        wsdl = etree.fromstring(OverrideNamespaceService().wsdl(''))
        self.assertEquals(wsdl.get('targetNamespace'),
            "http://someservice.com/override")

    def test_override_param_names(self):
        for n in ['self', 'import', 'return', 'from']:
            self.assertTrue(n in self._wsdl, '"%s" not in self._wsdl' % n)

    def test_multiple_return(self):
        service = TestMultipleReturnService()
        service.wsdl('')

        message = service.methods()[0].out_message
        self.assertEquals(len(message._type_info), 3)

        sent_xml = message.to_xml( ('a','b','c') )
        response_data = message.from_xml(sent_xml)

        self.assertEquals(len(response_data), 3)
        self.assertEqual(response_data[0], 'a')
        self.assertEqual(response_data[1], 'b')
        self.assertEqual(response_data[2], 'c')

def test_suite():
    loader = unittest.TestLoader()
    return loader.loadTestsFromTestCase(Test)

if __name__== '__main__':
    unittest.TextTestRunner().run(test_suite())
