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
import datetime
from soaplib.etimport import ElementTree

from soaplib.serializers.primitive import (String, Integer, DateTime, Float,
    Array)
from soaplib.serializers.clazz import ClassSerializer
from soaplib.service import soapmethod, SoapServiceBase
from soaplib.wsgi_soap import SimpleWSGISoapApp


class Address(ClassSerializer):

    class types:
        street = String
        city = String
        zip = Integer
        since = DateTime
        laditude = Float
        longitude = Float


class Person(ClassSerializer):

    class types:
        name = String
        birthdate = DateTime
        age = Integer
        addresses = Array(Address)
        titles = Array(String)


class Request(ClassSerializer):

    class types:
        param1 = String
        param2 = Integer


class Response(ClassSerializer):

    class types:
        param1 = Float


class TestService(SoapServiceBase):

    @soapmethod(String, _returns=String)
    def aa(self, s):
        return s

    @soapmethod(String, Integer, _returns=DateTime)
    def a(self, s, i):
        return datetime.datetime.now()

    @soapmethod(Person, String, Address, _returns=Address)
    def b(self, p, s, a):
        return Address()

    @soapmethod(Person, isAsync=True)
    def d(self, Person):
        pass

    @soapmethod(Person, isCallback=True)
    def e(self, Person):
        pass

    @soapmethod(String, String, String, _returns=String,
        _inputVariableNames={'_from': 'from', '_self': 'self',
            '_import': 'import'},
        _outVariableName="return")
    def f(self, _from, _self, _import):
        return '1234'


class OverrideNamespaceService(SimpleWSGISoapApp):
    __tns__ = "http://someservice.com/override"

    @soapmethod(String, _returns=String)
    def mymethod(self, s):
        return s


class test(unittest.TestCase):
    '''
    Most of the service tests are excersized through the interop tests
    '''

    def setUp(self):
        self.service = TestService()
        self._wsdl = self.service.wsdl('')
        self.wsdl = ElementTree.fromstring(self._wsdl)

    def test_portypes(self):
        porttype = self.wsdl.find('{http://schemas.xmlsoap.org/wsdl/}portType')
        self.assertEquals(
            len(self.service._soap_methods), len(porttype.getchildren()))

    def test_override_default_names(self):
        wsdl = ElementTree.fromstring(OverrideNamespaceService().wsdl(''))
        self.assertEquals(wsdl.get('targetNamespace'),
            "http://someservice.com/override")

    def test_override_param_names(self):
        for n in ['self', 'import', 'return', 'from']:
            self.assertTrue(n in self._wsdl, '"%s" not in self._wsdl' % n)


def test_suite():
    loader = unittest.TestLoader()
    return loader.loadTestsFromTestCase(test)

if __name__== '__main__':
    unittest.TextTestRunner().run(test_suite())
