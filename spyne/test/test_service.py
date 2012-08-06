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
from spyne.auxproc.thread import ThreadAuxProc
from spyne.auxproc.sync import SyncAuxProc
from spyne.decorator import rpc
from spyne.decorator import srpc
from spyne.interface.wsdl import Wsdl11
from spyne.model.complex import Array
from spyne.model.complex import ComplexModel
from spyne.model.primitive import DateTime
from spyne.model.primitive import Float
from spyne.model.primitive import Integer
from spyne.model.primitive import String
from spyne.protocol.soap import Soap11
from spyne.protocol.http import HttpRpc
from spyne.server.null import NullServer
from spyne.server.wsgi import WsgiApplication
from spyne.service import ServiceBase

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

class MultipleMethods1(ServiceBase):
    @srpc(String)
    def multi(s):
        return "%r multi 1" % s

class MultipleMethods2(ServiceBase):
    @srpc(String)
    def multi(s):
        return "%r multi 2" % s

class TestMultipleMethods(unittest.TestCase):
    def test_single_method(self):
        try:
            app = Application([MultipleMethods1,MultipleMethods2], 'tns', in_protocol=Soap11(), out_protocol=Soap11())

        except ValueError:
            pass
        else:
            raise Exception('must fail.')


    def test_simple_aux_nullserver(self):
        data = []

        class Service(ServiceBase):
            @srpc(String)
            def call(s):
                data.append(s)

        class AuxService(ServiceBase):
            __aux__ = SyncAuxProc()

            @srpc(String)
            def call(s):
                data.append(s)

        app = Application([Service, AuxService], 'tns', in_protocol=Soap11(), out_protocol=Soap11())
        server = NullServer(app)
        server.service.call("hey")

        assert data == ['hey', 'hey']

    def test_simple_aux_wsgi(self):
        data = []

        class Service(ServiceBase):
            @srpc(String, _returns=String)
            def call(s):
                data.append(s)

        class AuxService(ServiceBase):
            __aux__ = SyncAuxProc()

            @srpc(String, _returns=String)
            def call(s):
                data.append(s)

        app = Application([Service, AuxService], 'tns', in_protocol=HttpRpc(), out_protocol=HttpRpc())
        server = WsgiApplication(app)
        server({
            'QUERY_STRING': 's=hey',
            'PATH_INFO': '/call',
            'REQUEST_METHOD': 'GET',
        }, start_response, "http://null")

        assert data == ['hey', 'hey']

    def test_thread_aux_wsgi(self):
        import logging
        logging.basicConfig(level=logging.DEBUG)
        data = set()

        class Service(ServiceBase):
            @srpc(String, _returns=String)
            def call(s):
                data.add(s)

        class AuxService(ServiceBase):
            __aux__ = ThreadAuxProc()

            @srpc(String, _returns=String)
            def call(s):
                data.add(s + "aux")

        app = Application([Service, AuxService], 'tns', in_protocol=HttpRpc(), out_protocol=HttpRpc())
        server = WsgiApplication(app)
        server({
            'QUERY_STRING': 's=hey',
            'PATH_INFO': '/call',
            'REQUEST_METHOD': 'GET',
        }, start_response, "http://null")

        import time
        time.sleep(1)

        assert data == set(['hey', 'heyaux'])

    def test_mixing_primary_and_aux_methods(self):
        try:
            class Service(ServiceBase):
                @srpc(String, _returns=String, _aux=ThreadAuxProc())
                def call(s):
                    pass

                @srpc(String, _returns=String)
                def mall(s):
                    pass
        except Exception:
            pass
        else:
            raise Exception("must fail with 'Exception: you can't mix aux and non-aux methods in a single service definition.'")

    def __run_service(self, SomeService):
        app = Application([SomeService], 'tns', in_protocol=HttpRpc(), out_protocol=Soap11())
        server = WsgiApplication(app)
        return_string = ''.join(server({
            'QUERY_STRING': '',
            'PATH_INFO': '/some_call',
            'REQUEST_METHOD': 'GET',
        }, start_response, "http://null"))

        elt = etree.fromstring(return_string)
        print etree.tostring(elt, pretty_print=True)

        return elt, app.interface.nsmap

    def test_settings_headers_from_user_code(self):
        class RespHeader(ComplexModel):
            __namespace__ = 'tns'
            Elem1 = String

        class SomeService(ServiceBase):
            __out_header__ = RespHeader

            @rpc()
            def some_call(ctx):
                ctx.out_header = RespHeader()
                ctx.out_header.Elem1 = 'Test1'

        elt, nsmap = self.__run_service(SomeService)
        query = '/senv:Envelope/senv:Header/tns:RespHeader/tns:Elem1/text()'
        assert elt.xpath(query, namespaces=nsmap)[0] == 'Test1'

        class SomeService(ServiceBase):
            @rpc(_out_header=RespHeader)
            def some_call(ctx):
                ctx.out_header = RespHeader()
                ctx.out_header.Elem1 = 'Test1'

        elt, nsmap = self.__run_service(SomeService)
        query = '/senv:Envelope/senv:Header/tns:RespHeader/tns:Elem1/text()'
        assert elt.xpath(query, namespaces=nsmap)[0] == 'Test1'

        class SomeService(ServiceBase):
            @rpc()
            def some_call(ctx):
                ctx.out_header = RespHeader()
                ctx.out_header.Elem1 = 'Test1'

        elt, nsmap = self.__run_service(SomeService)
        query = '/senv:Envelope/senv:Header/tns:RespHeader/tns:Elem1/text()'
        assert len(elt.xpath(query, namespaces=nsmap)) == 0

if __name__ == '__main__':
    unittest.main()
