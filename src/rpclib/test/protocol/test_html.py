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

import logging
logging.basicConfig(level=logging.DEBUG)

import unittest

from lxml import html

from rpclib.application import Application
from rpclib.decorator import srpc
from rpclib.model.primitive import Integer
from rpclib.model.primitive import String
from rpclib.model.complex import ComplexModel
from rpclib.interface.wsdl import Wsdl11
from rpclib.protocol.http import HttpRpc
from rpclib.protocol.html import HtmlMicroFormat
from rpclib.service import ServiceBase

class TestHtmlMicroFormat(unittest.TestCase):
    '''Most of the service tests are performed through the interop tests.'''

    def test_simple(self):
        class SomeService(ServiceBase):
            @srpc(String, _returns=String)
            def some_call(s):
                return s

        app = Application([SomeService], 'tns', Wsdl11(), HttpRpc(), HtmlMicroFormat())

        from rpclib.server.wsgi import WsgiMethodContext

        initial_ctx = WsgiMethodContext(app, {
            'QUERY_STRING': 's=s',
            'PATH_INFO': '/some_call',
            'REQUEST_METHOD': 'GET',
        }, 'some-content-type')

        from rpclib.server import ServerBase

        server = ServerBase(app)
        ctx, = server.generate_contexts(initial_ctx)
        assert ctx.in_error is None

        server.get_in_object(ctx)
        server.get_out_object(ctx)
        server.get_out_string(ctx)

        assert ''.join(ctx.out_string) == '<div class="some_callResponse"><div class="some_callResult">s</div></div>'

    def test_multiple_return(self):
        class SomeNotSoComplexModel(ComplexModel):
            s = String

        class SomeService(ServiceBase):
            @srpc(_returns=[Integer, String])
            def some_call():
                return 1, 's'

        app = Application([SomeService], 'tns', Wsdl11(), HttpRpc(), HtmlMicroFormat())

        from rpclib.server.wsgi import WsgiMethodContext

        initial_ctx = WsgiMethodContext(app, {
            'QUERY_STRING': '',
            'PATH_INFO': '/some_call',
            'REQUEST_METHOD': 'GET',
        }, 'some-content-type')

        from rpclib.server import ServerBase

        server = ServerBase(app)
        ctx, = server.generate_contexts(initial_ctx)
        server.get_in_object(ctx)
        server.get_out_object(ctx)
        server.get_out_string(ctx)

        assert ''.join(ctx.out_string) == '<div class="some_callResponse"><div class="some_callResult0">1</div><div class="some_callResult1">s</div></div>'


    def test_complex(self):
        class CM(ComplexModel):
            i = Integer
            s = String

        class CCM(ComplexModel):
            c = CM
            i = Integer
            s = String

        class SomeService(ServiceBase):
            @srpc(CCM, _returns=CCM)
            def some_call(ccm):
                return CCM(c=ccm.c,i=ccm.i, s=ccm.s)

        app = Application([SomeService], 'tns', Wsdl11(), HttpRpc(), HtmlMicroFormat())

        from rpclib.server.wsgi import WsgiMethodContext

        initial_ctx = WsgiMethodContext(app, {
            'QUERY_STRING': 'ccm_c_s=abc&ccm_c_i=123&ccm_i=456&ccm_s=def',
            'PATH_INFO': '/some_call',
            'REQUEST_METHOD': 'GET',
        }, 'some-content-type')

        from rpclib.server import ServerBase

        server = ServerBase(app)
        ctx, = server.generate_contexts(initial_ctx)
        server.get_in_object(ctx)
        server.get_out_object(ctx)
        server.get_out_string(ctx)

        #
        # Here's what this is supposed to return:
        #
        # <div class="some_callResponse">
        #   <div class="some_callResult">
        #     <div class="i">456</div>
        #     <div class="c">
        #       <div class="i">123</div>
        #       <div class="s">abc</div>
        #     </div>
        #     <div class="s">def</div>
        #   </div>
        # </div>
        #

        elt = html.fromstring(''.join(ctx.out_string))
        resp = elt.find_class('some_callResponse')
        assert len(resp) == 1
        res = resp[0].find_class('some_callResult')
        assert len(res) == 1

        i = res[0].findall('div[@class="i"]')
        assert len(i) == 1
        assert i[0].text == '456'

        c = res[0].findall('div[@class="c"]')
        assert len(c) == 1

        c_i = c[0].findall('div[@class="i"]')
        assert len(c_i) == 1
        assert c_i[0].text == '123'

        c_s = c[0].findall('div[@class="s"]')
        assert len(c_s) == 1
        assert c_s[0].text == 'abc'

        s = res[0].findall('div[@class="s"]')
        assert len(s) == 1
        assert s[0].text == 'def'

    def test_multiple(self):
        class SomeService(ServiceBase):
            @srpc(String(max_occurs='unbounded'), _returns=String)
            def some_call(s):
                return '\n'.join(s)

        app = Application([SomeService], 'tns', Wsdl11(), HttpRpc(), HtmlMicroFormat())

        from rpclib.server.wsgi import WsgiMethodContext

        initial_ctx = WsgiMethodContext(app, {
            'QUERY_STRING': 's=1&s=2',
            'PATH_INFO': '/some_call',
            'REQUEST_METHOD': 'GET',
        }, 'some-content-type')

        from rpclib.server import ServerBase

        server = ServerBase(app)
        ctx, = server.generate_contexts(initial_ctx)
        server.get_in_object(ctx)
        server.get_out_object(ctx)
        server.get_out_string(ctx)

        assert ''.join(ctx.out_string) == '<div class="some_callResponse"><div class="some_callResult">1\n2</div></div>'

if __name__ == '__main__':
    unittest.main()
