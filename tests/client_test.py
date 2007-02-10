import unittest
import cElementTree as ElementTree
import datetime

from soaplib.serializers.primitive import *
from soaplib.serializers.clazz import *
from soaplib.service import *
from soaplib.wsgi_soap import *
from soaplib.client import *
from soaplib.util import *
from soaplib.soap import *

import BaseHTTPServer, cgi
import cStringIO 
import sys
from threading import Thread
import socket
import time
import httplib

from threading import Thread
from cherrypy._cpwsgiserver import CherryPyWSGIServer

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
      
class TestService(SimpleWSGISoapApp):

    @soapmethod(String, Integer, _returns=DateTime)
    def a(self, s, i):
        return datetime.datetime(1901,12,15)

    @soapmethod(Person, String, Address, _returns=Address)
    def b(self, p,s,a):
        a = Address()
        a.zip = 4444
        a.street = 'wsgi way'
        a.laditude = 123.3
        
        return a
        
    @soapmethod(Person, _isAsync=True)
    def d(self, person):
        pass

    @soapmethod(Person, _isCallback=True)
    def e(self, person):
        pass
        
    @soapmethod()
    def fault(self):
        raise Exception('Testing faults')

class test(unittest.TestCase):

    def setUp(self):
        self.server = CherryPyWSGIServer(('127.0.0.1',9191),TestService())
        t = Thread(target=self.server.start)
        t.start()
        time.sleep(3)

    def tearDown(self):
        self.server.stop()
        time.sleep(3)

    def test_simple(self):
        inMessage = Message('a',[('s',String),('i',Integer)])
        outMessage = Message('aResponse',[('retval',DateTime)])
        
        desc = MethodDescriptor('a',inMessage,outMessage)

        client = SimpleSoapClient('127.0.0.1:9191','/',desc)
        results = client('abc',54)
        self.assertEquals(results,datetime.datetime(1901,12,15))    

    def test_nested(self):
        inMessage = Message('b',[('p',Person),('s',String),('a',Integer)])
        outMessage = Message('bResponse',[('retval',Address)])
        
        desc = MethodDescriptor('b',inMessage,outMessage)

        client = SimpleSoapClient('127.0.0.1:9191','/',desc)
        p = Person()
        p.name = 'wilson'
        p.addresses = []
        for i in range(0,123):
            a = Address()
            a.zip = i
            p.addresses.append(a)
        res = client(p,'abc',123)
        self.assertEquals(res.longitude,None)
        self.assertEquals(res.zip,4444)
        self.assertEquals(res.street,'wsgi way')

    def test_async(self):
        inMessage = Message('d',[('person',Person)])
        outMessage = Message('dResponse',[])

        desc = MethodDescriptor('d',inMessage,outMessage)
        
        client = SimpleSoapClient('127.0.0.1:9191','/',desc)
        p = Person()
        p.name = 'wilson'
        r = client(p)
        self.assertEquals(r,None)
        
    def test_fault(self):
        inMessage = Message('fault',[])
        outMessage = Message('faultResponse',[])
        desc = MethodDescriptor('fault',inMessage,outMessage)
        
        client = SimpleSoapClient('127.0.0.1:9191','/',desc)
        try:
            client()
        except Fault, f:
            self.assertEquals(f.faultcode,'faultFault')
            self.assertEquals(f.faultstring,'Testing faults')
            #self.assertTrue(f.detail.find('client_test.py') > -1)
        else:
            raise 

    def _test_callback(self):
        inputs = [ParameterDescriptor('person',Person)]
        
        client = SimpleSoapClient('127.0.0.1:9191','/','e',inputs,None)
        p = Person()
        p.name = 'wilson'
        r = client(p)
        self.assertEquals(r,None)

    def test_service_client(self):        
        client = ServiceClient('127.0.0.1:9191','/',TestService())

        r = client.a('bobo',23)
        self.assertEquals(r,datetime.datetime(1901,12,15))    

        p = Person()
        p.name = 'wilson'
        p.addresses = []
        for i in range(0,123):
            a = Address()
            a.zip = i
            p.addresses.append(a)
        res = client.b(p,'abc',123)
        self.assertEquals(res.longitude,None)
        self.assertEquals(res.zip,4444)
        self.assertEquals(res.street,'wsgi way')

        request = Request()
        request.param1 = 'asdf'

        p = Person()
        p.name = 'wilson'
        r = client.d(p)
        self.assertEquals(r,None)

        p = Person()
        p.name = 'wilson'
        r = client.e(p)
        self.assertEquals(r,None)

def test_suite():
    #debug(True)
    loader = unittest.TestLoader()
    #log_debug(True)
    return loader.loadTestsFromTestCase(test)

if __name__== '__main__':
    unittest.TextTestRunner().run(test_suite())



    
