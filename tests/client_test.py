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
from threading import Thread

from soaplib.client import SimpleSoapClient, ServiceClient
from soaplib.serializers.primitive import (Array, DateTime, Float,
    Integer, String, Fault)
from soaplib.serializers.clazz import ClassSerializer
from soaplib.service import rpc
from soaplib.soap import MethodDescriptor, Message
from soaplib.wsgi_soap import SimpleWSGIApp

try:
    from wsgiref.simple_server import make_server
except ImportError:
    raise Exception("UnitTests require Python >= 2.5")


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


class TestService(SimpleWSGIApp):

    @rpc(String, Integer, _returns=DateTime)
    def a(self, s, i):
        return datetime.datetime(1901, 12, 15)

    @rpc(Person, String, Integer, _returns=Address)
    def b(self, p, s, i):
        a = Address()
        a.zip = 4444
        a.street = 'wsgi way'
        a.laditude = 123.3

        return a

    @rpc(Person, _isAsync=True)
    def d(self, person):
        pass

    @rpc(Person, _isCallback=True)
    def e(self, person):
        pass

    @rpc()
    def fault(self):
        raise Exception('Testing faults')


class test(unittest.TestCase):

    def setUp(self):
        self.server = make_server('127.0.0.1', 9191, TestService())
        self.server.allow_reuse_address = True
        Thread(target=self.server.serve_forever).start()

    def tearDown(self):
        self.server.shutdown()
        del self.server

    def test_simple(self):
        inMessage = Message('a', [('s', String), ('i', Integer)])
        outMessage = Message('aResponse', [('retval', DateTime)])

        desc = MethodDescriptor('a', 'a', inMessage, outMessage, '')

        client = SimpleSoapClient('127.0.0.1:9191', '/', desc)
        results = client('abc', 54)
        self.assertEquals(results, datetime.datetime(1901, 12, 15))

    def test_nested(self):
        inMessage = Message('b',
            [('p', Person), ('s', String), ('i', Integer)])
        outMessage = Message('bResponse', [('retval', Address)])

        desc = MethodDescriptor('b', 'b', inMessage, outMessage, '')

        client = SimpleSoapClient('127.0.0.1:9191', '/', desc)
        p = Person()
        p.name = 'wilson'
        p.addresses = []
        for i in range(0, 123):
            a = Address()
            a.zip = i
            p.addresses.append(a)
        res = client(p, 'abc', 123)
        self.assertEquals(res.longitude, None)
        self.assertEquals(res.zip, 4444)
        self.assertEquals(res.street, 'wsgi way')

    def test_async(self):
        inMessage = Message('d', [('person', Person)])
        outMessage = Message('dResponse', [])

        desc = MethodDescriptor('d', 'd', inMessage, outMessage, '')

        client = SimpleSoapClient('127.0.0.1:9191', '/', desc)
        p = Person()
        p.name = 'wilson'
        r = client(p)
        self.assertEquals(r, None)

    def test_fault(self):
        inMessage = Message('fault', [])
        outMessage = Message('faultResponse', [])
        desc = MethodDescriptor('fault', 'fault', inMessage, outMessage, '')

        client = SimpleSoapClient('127.0.0.1:9191', '/', desc)
        try:
            client()
        except Fault, f:
            self.assertEquals(f.faultcode, 'faultFault')
            self.assertEquals(f.faultstring, 'Testing faults')
            self.assertTrue(f.detail.find('client_test.py') > -1)
        else:
            raise

    def _test_callback(self):
        inputs = [MethodDescriptor('person', Person)]

        client = SimpleSoapClient('127.0.0.1:9191', '/', 'e', inputs, None)
        p = Person()
        p.name = 'wilson'
        r = client(p)
        self.assertEquals(r, None)

    def test_service_client(self):
        client = ServiceClient('127.0.0.1:9191', '/', TestService())

        r = client.a('bobo', 23)
        self.assertEquals(r, datetime.datetime(1901, 12, 15))

        p = Person()
        p.name = 'wilson'
        p.addresses = []
        for i in range(0, 123):
            a = Address()
            a.zip = i
            p.addresses.append(a)
        res = client.b(p, 'abc', 123)
        self.assertEquals(res.longitude, None)
        self.assertEquals(res.zip, 4444)
        self.assertEquals(res.street, 'wsgi way')

        request = Request()
        request.param1 = 'asdf'

        p = Person()
        p.name = 'wilson'
        r = client.d(p)
        self.assertEquals(r, None)

        p = Person()
        p.name = 'wilson'
        r = client.e(p)
        self.assertEquals(r, None)


def test_suite():
    #debug(True)
    loader = unittest.TestLoader()
    #log_debug(True)
    return loader.loadTestsFromTestCase(test)


if __name__== '__main__':
    unittest.TextTestRunner().run(test_suite())
