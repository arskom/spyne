import unittest
import cElementTree as ElementTree
import datetime

from soaplib.serializers.primitive import *
from soaplib.serializers.clazz import *
from soaplib.service import *
from soaplib.wsgi_soap import *

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

    @soapmethod(String,_returns=String)
    def aa(self,s):
        return s

    @soapmethod(String, Integer, _returns=DateTime)
    def a(self, s, i):
        return datetime.datetime.now()

    @soapmethod(Person, String, Address, _returns=Address)
    def b(self, p,s,a):
        return Address()

    @soapmethod(Person, isAsync=True)
    def d(self, Person):
        pass

    @soapmethod(Person, isCallback=True)
    def e(self, Person):
        pass

class OverrideNamespaceService(SimpleWSGISoapApp):
    __tns__ = "http://someservice.com/override"
    
    @soapmethod(String,_returns=String)
    def mymethod(self,s):
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
        self.assertEquals(len(self.service._soap_methods),len(porttype.getchildren()))

    def test_override_default_names(self):
        wsdl = ElementTree.fromstring(OverrideNamespaceService().wsdl(''))
        self.assertEquals(wsdl.get('targetNamespace'),"http://someservice.com/override")
        

def test_suite():
    loader = unittest.TestLoader()
    return loader.loadTestsFromTestCase(test)

if __name__== '__main__':
    unittest.TextTestRunner().run(test_suite())

