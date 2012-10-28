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

import logging
logging.basicConfig(level=logging.DEBUG)

import unittest

from lxml import etree
from StringIO import StringIO

from spyne.const.suffix import RESPONSE_SUFFIX
from spyne.model.primitive import NATIVE_MAP

from spyne.application import Application
from spyne.auxproc.sync import SyncAuxProc
from spyne.auxproc.thread import ThreadAuxProc
from spyne.decorator import rpc
from spyne.decorator import srpc
from spyne.model.complex import Array
from spyne.model.complex import ComplexModel
from spyne.model.primitive import String
from spyne.protocol.http import HttpRpc
from spyne.protocol.soap import Soap11
from spyne.server.null import NullServer
from spyne.server.wsgi import WsgiApplication
from spyne.service import ServiceBase


Application.transport = 'test'


def start_response(code, headers):
    print(code, headers)


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
            Application([MultipleMethods1,MultipleMethods2], 'tns', in_protocol=Soap11(), out_protocol=Soap11())

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

        app = Application([Service, AuxService], 'tns','name', Soap11(), Soap11())
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
            'SERVER_NAME': 'localhost',
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
            'SERVER_NAME': 'localhost',
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
            'SERVER_NAME': 'localhost',
        }, start_response, "http://null"))

        elt = etree.fromstring(return_string)
        print etree.tostring(elt, pretty_print=True)

        return elt, app.interface.nsmap

    def test_settings_headers_from_user_code(self):
        class RespHeader(ComplexModel):
            __namespace__ = 'tns'
            Elem1 = String

        # test header in service definition
        class SomeService(ServiceBase):
            __out_header__ = RespHeader

            @rpc()
            def some_call(ctx):
                ctx.out_header = RespHeader()
                ctx.out_header.Elem1 = 'Test1'

        elt, nsmap = self.__run_service(SomeService)
        query = '/senv:Envelope/senv:Header/tns:RespHeader/tns:Elem1/text()'
        assert elt.xpath(query, namespaces=nsmap)[0] == 'Test1'

        # test header in decorator
        class SomeService(ServiceBase):
            @rpc(_out_header=RespHeader)
            def some_call(ctx):
                ctx.out_header = RespHeader()
                ctx.out_header.Elem1 = 'Test1'

        elt, nsmap = self.__run_service(SomeService)
        query = '/senv:Envelope/senv:Header/tns:RespHeader/tns:Elem1/text()'
        assert elt.xpath(query, namespaces=nsmap)[0] == 'Test1'

        # test no header
        class SomeService(ServiceBase):
            @rpc()
            def some_call(ctx):
                ctx.out_header = RespHeader()
                ctx.out_header.Elem1 = 'Test1'

        elt, nsmap = self.__run_service(SomeService)
        query = '/senv:Envelope/senv:Header/tns:RespHeader/tns:Elem1/text()'
        assert len(elt.xpath(query, namespaces=nsmap)) == 0


class TestNativeTypes(unittest.TestCase):
    def test_native_types(self):
        for t in NATIVE_MAP:
            class SomeService(ServiceBase):
                @rpc(t)
                def some_call(ctx, arg):
                    pass
            nt, = SomeService.public_methods['some_call'].in_message._type_info.values()
            assert issubclass(nt, NATIVE_MAP[t])

    def test_native_types_in_arrays(self):
        for t in NATIVE_MAP:
            class SomeService(ServiceBase):
                @rpc(Array(t))
                def some_call(ctx, arg):
                    pass
            nt, = SomeService.public_methods['some_call'].in_message._type_info.values()
            nt, = nt._type_info.values()
            assert issubclass(nt, NATIVE_MAP[t])


class TestBodyStyle(unittest.TestCase):
    def test_soap_bare_empty_output(self):
        class SomeService(ServiceBase):
            @rpc(String, _body_style='bare')
            def some_call(ctx, s):
                assert s == 'abc'

        app = Application([SomeService], 'tns', in_protocol=Soap11(),
                                                out_protocol=Soap11(cleanup_namespaces=True))

        req = """
        <senv:Envelope  xmlns:senv="http://schemas.xmlsoap.org/soap/envelope/"
                        xmlns:tns="tns">
            <senv:Body>
                <tns:some_call>abc</tns:some_call>
            </senv:Body>
        </senv:Envelope>
        """

        server = WsgiApplication(app)
        resp = etree.fromstring(''.join(server({
            'QUERY_STRING': '',
            'PATH_INFO': '/call',
            'REQUEST_METHOD': 'GET',
            'SERVER_NAME': 'localhost',
            'wsgi.input': StringIO(req)
        }, start_response, "http://null")))

        print etree.tostring(resp, pretty_print=True)

        assert resp[0].tag == '{http://schemas.xmlsoap.org/soap/envelope/}Body'
        assert len(resp[0]) == 1
        assert resp[0][0].tag == '{tns}some_call'+ RESPONSE_SUFFIX
        assert len(resp[0][0]) == 0

    def test_soap_bare_empty_input(self):
        class SomeService(ServiceBase):
            @rpc(_body_style='bare', _returns=String)
            def some_call(ctx):
                return 'abc'

        app = Application([SomeService], 'tns', in_protocol=Soap11(),
                                                out_protocol=Soap11(cleanup_namespaces=True))

        req = """
        <senv:Envelope  xmlns:senv="http://schemas.xmlsoap.org/soap/envelope/"
                        xmlns:tns="tns">
            <senv:Body>
                <tns:some_call/>
            </senv:Body>
        </senv:Envelope>
        """

        server = WsgiApplication(app)
        resp = etree.fromstring(''.join(server({
            'QUERY_STRING': '',
            'PATH_INFO': '/call',
            'REQUEST_METHOD': 'GET',
            'SERVER_NAME': 'localhost',
            'wsgi.input': StringIO(req)
        }, start_response, "http://null")))

        print etree.tostring(resp, pretty_print=True)

        assert resp[0].tag == '{http://schemas.xmlsoap.org/soap/envelope/}Body'
        assert resp[0][0].tag == '{tns}some_call' + RESPONSE_SUFFIX
        assert resp[0][0].text == 'abc'

    def test_soap_bare_wrapped_array_output(self):
        class SomeService(ServiceBase):
            @rpc(_body_style='bare', _returns=Array(String))
            def some_call(ctx):
                return ['abc', 'def']

        app = Application([SomeService], 'tns', in_protocol=Soap11(),
                                                out_protocol=Soap11(cleanup_namespaces=True))

        req = """
        <senv:Envelope  xmlns:senv="http://schemas.xmlsoap.org/soap/envelope/"
                        xmlns:tns="tns">
            <senv:Body>
                <tns:some_call/>
            </senv:Body>
        </senv:Envelope>
        """

        server = WsgiApplication(app)
        resp = etree.fromstring(''.join(server({
            'QUERY_STRING': '',
            'PATH_INFO': '/call',
            'REQUEST_METHOD': 'GET',
            'wsgi.input': StringIO(req)
        }, start_response, "http://null")))

        print etree.tostring(resp, pretty_print=True)

        assert resp[0].tag == '{http://schemas.xmlsoap.org/soap/envelope/}Body'
        assert resp[0][0].tag == '{tns}some_call' + RESPONSE_SUFFIX
        assert resp[0][0][0].text == 'abc'
        assert resp[0][0][1].text == 'def'


if __name__ == '__main__':
    unittest.main()
