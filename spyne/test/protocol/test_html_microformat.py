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

import logging
logging.basicConfig(level=logging.DEBUG)

import unittest

from lxml import html

from spyne.application import Application
from spyne.decorator import srpc
from spyne.model.primitive import Integer
from spyne.model.primitive import String
from spyne.model.complex import Array
from spyne.model.complex import ComplexModel
from spyne.protocol.http import HttpRpc
from spyne.protocol.html import HtmlMicroFormat
from spyne.service import Service
from spyne.server.wsgi import WsgiMethodContext
from spyne.server.wsgi import WsgiApplication
from spyne.util.test import show, call_wsgi_app_kwargs


class TestHtmlMicroFormat(unittest.TestCase):
    def test_simple(self):
        class SomeService(Service):
            @srpc(String, _returns=String)
            def some_call(s):
                return s

        app = Application([SomeService], 'tns',
                                     in_protocol=HttpRpc(hier_delim='_'),
                                     out_protocol=HtmlMicroFormat(doctype=None))

        server = WsgiApplication(app)

        initial_ctx = WsgiMethodContext(server, {
            'QUERY_STRING': 's=s',
            'PATH_INFO': '/some_call',
            'REQUEST_METHOD': 'GET',
            'SERVER_NAME': 'localhost',
        }, 'some-content-type')

        ctx, = server.generate_contexts(initial_ctx)
        assert ctx.in_error is None

        server.get_in_object(ctx)
        server.get_out_object(ctx)
        server.get_out_string(ctx)

        assert b''.join(ctx.out_string) == b'<div class="some_callResponse">' \
                                   b'<div class="some_callResult">s</div></div>'

    def test_multiple_return(self):
        class SomeService(Service):
            @srpc(_returns=[Integer, String])
            def some_call():
                return 1, 's'

        app = Application([SomeService], 'tns',
                                     in_protocol=HttpRpc(hier_delim='_'),
                                     out_protocol=HtmlMicroFormat(doctype=None))
        server = WsgiApplication(app)

        initial_ctx = WsgiMethodContext(server, {
            'QUERY_STRING': '',
            'PATH_INFO': '/some_call',
            'REQUEST_METHOD': 'GET',
            'SERVER_NAME': 'localhost',
        }, 'some-content-type')

        ctx, = server.generate_contexts(initial_ctx)
        server.get_in_object(ctx)
        server.get_out_object(ctx)
        server.get_out_string(ctx)

        assert b''.join(ctx.out_string) == b'<div class="some_callResponse">' \
                               b'<div class="some_callResult0">1</div>' \
                               b'<div class="some_callResult1">s</div></div>'


    def test_complex(self):
        class CM(ComplexModel):
            i = Integer
            s = String

        class CCM(ComplexModel):
            c = CM
            i = Integer
            s = String

        class SomeService(Service):
            @srpc(CCM, _returns=CCM)
            def some_call(ccm):
                return CCM(c=ccm.c,i=ccm.i, s=ccm.s)

        app = Application([SomeService], 'tns',
                                     in_protocol=HttpRpc(hier_delim='_'),
                                     out_protocol=HtmlMicroFormat(doctype=None))
        server = WsgiApplication(app)

        initial_ctx = WsgiMethodContext(server, {
            'QUERY_STRING': 'ccm_c_s=abc&ccm_c_i=123&ccm_i=456&ccm_s=def',
            'PATH_INFO': '/some_call',
            'REQUEST_METHOD': 'GET',
            'SERVER_NAME': 'localhost',
        }, 'some-content-type')

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

        elt = html.fromstring(b''.join(ctx.out_string))
        print(html.tostring(elt, pretty_print=True))

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
        class SomeService(Service):
            @srpc(String(max_occurs='unbounded'), _returns=String)
            def some_call(s):
                print(s)
                return '\n'.join(s)

        app = Application([SomeService], 'tns',
                                     in_protocol=HttpRpc(hier_delim='_'),
                                     out_protocol=HtmlMicroFormat(doctype=None))
        server = WsgiApplication(app)

        initial_ctx = WsgiMethodContext(server, {
            'QUERY_STRING': 's=1&s=2',
            'PATH_INFO': '/some_call',
            'REQUEST_METHOD': 'GET',
            'SERVER_NAME': 'localhost',
        }, 'some-content-type')

        ctx, = server.generate_contexts(initial_ctx)
        server.get_in_object(ctx)
        server.get_out_object(ctx)
        server.get_out_string(ctx)

        assert b''.join(ctx.out_string) == (b'<div class="some_callResponse">'
                               b'<div class="some_callResult">1\n2</div></div>')

        ctx, = server.generate_contexts(initial_ctx)
        server.get_in_object(ctx)
        server.get_out_object(ctx)
        server.get_out_string(ctx)

        assert b''.join(ctx.out_string) == b'<div class="some_callResponse">' \
                               b'<div class="some_callResult">1\n2</div></div>'

    def test_before_first_root(self):
        class CM(ComplexModel):
            i = Integer
            s = String

        class CCM(ComplexModel):
            c = CM
            i = Integer
            s = String

        class SomeService(Service):
            @srpc(CCM, _returns=Array(CCM))
            def some_call(ccm):
                return [CCM(c=ccm.c,i=ccm.i, s=ccm.s)] * 2

        cb_called = [False]
        def _cb(ctx, cls, inst, parent, name, **kwargs):
            assert not cb_called[0]
            cb_called[0] = True

        app = Application([SomeService], 'tns',
                                     in_protocol=HttpRpc(hier_delim='_'),
                                     out_protocol=HtmlMicroFormat(
                                           doctype=None, before_first_root=_cb))
        server = WsgiApplication(app)

        call_wsgi_app_kwargs(server,
                             ccm_c_s='abc', ccm_c_i=123, ccm_i=456, ccm_s='def')

        assert cb_called[0]

    def test_complex_array(self):
        class CM(ComplexModel):
            i = Integer
            s = String

        class CCM(ComplexModel):
            c = CM
            i = Integer
            s = String

        class SomeService(Service):
            @srpc(CCM, _returns=Array(CCM))
            def some_call(ccm):
                return [CCM(c=ccm.c,i=ccm.i, s=ccm.s)] * 2

        app = Application([SomeService], 'tns',
                                     in_protocol=HttpRpc(hier_delim='_'),
                                     out_protocol=HtmlMicroFormat(doctype=None))
        server = WsgiApplication(app)

        out_string = call_wsgi_app_kwargs(server,
                             ccm_c_s='abc', ccm_c_i=123, ccm_i=456, ccm_s='def')

        #
        # Here's what this is supposed to return:
        #
        # <div class="some_callResponse"><div class="some_callResult">
        #     <div class="CCM">
        #         <div class="i">456</div>
        #         <div class="c">
        #             <div class="i">123</div>
        #             <div class="s">abc</div>
        #         </div>
        #         <div class="s">def</div>
        #     </div>
        #     <div class="CCM">
        #         <div class="i">456</div>
        #         <div class="c">
        #             <div class="i">123</div>
        #             <div class="s">abc</div>
        #         </div>
        #         <div class="s">def</div>
        #     </div>
        # </div></div>
        #

        print(out_string)
        elt = html.fromstring(out_string)
        show(elt, "TestHtmlMicroFormat.test_complex_array")

        resp = elt.find_class('some_callResponse')
        assert len(resp) == 1
        res = resp[0].find_class('some_callResult')
        assert len(res) == 1

        assert len(res[0].find_class("CCM")) == 2

        # We don't need to test the rest as the test_complex test takes care of
        # that

if __name__ == '__main__':
    unittest.main()
