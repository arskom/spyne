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
from rpclib.model.complex import Array
from rpclib.model.complex import ComplexModel
from rpclib.interface.wsdl import Wsdl11
from rpclib.protocol.http import HttpRpc
from rpclib.protocol.html import HtmlTable
from rpclib.service import ServiceBase
from rpclib.server.wsgi import WsgiMethodContext
from rpclib.server.wsgi import WsgiApplication


class TestHtmlTable(unittest.TestCase):
    def test_complex_array(self):
        class CM(ComplexModel):
            i = Integer
            s = String

        class CCM(ComplexModel):
            c = CM
            i = Integer
            s = String

        class SomeService(ServiceBase):
            @srpc(CCM, _returns=Array(CCM))
            def some_call(ccm):
                return [ccm] * 5

        app = Application([SomeService], 'tns', HttpRpc(), HtmlTable(field_name_attr='class'), Wsdl11())
        server = WsgiApplication(app)

        initial_ctx = WsgiMethodContext(server, {
            'QUERY_STRING': 'ccm_c_s=abc&ccm_c_i=123&ccm_i=456&ccm_s=def',
            'PATH_INFO': '/some_call',
            'REQUEST_METHOD': 'GET',
        }, 'some-content-type')

        ctx, = server.generate_contexts(initial_ctx)
        server.get_in_object(ctx)
        server.get_out_object(ctx)
        server.get_out_string(ctx)

        out_string = ''.join(ctx.out_string)
        elt = html.fromstring(out_string)
        print html.tostring(elt, pretty_print=True)

        resp = elt.find_class('some_callResponse')
        assert len(resp) == 1
        for i in range(len(elt)):
            row = elt[i]
            if i == 0:
                cell = row.findall('th[@class="i"]')
                assert len(cell) == 1
                assert cell[0].text == 'i'

                cell = row.findall('th[@class="c_i"]')
                assert len(cell) == 1
                assert cell[0].text == 'c_i'

                cell = row.findall('th[@class="c_s"]')
                assert len(cell) == 1
                assert cell[0].text == 'c_s'

                cell = row.findall('th[@class="s"]')
                assert len(cell) == 1
                assert cell[0].text == 's'


            else:
                cell = row.findall('td[@class="i"]')
                assert len(cell) == 1
                assert cell[0].text == '456'

                cell = row.findall('td[@class="c_i"]')
                assert len(cell) == 1
                assert cell[0].text == '123'

                cell = row.findall('td[@class="c_s"]')
                assert len(cell) == 1
                assert cell[0].text == 'abc'

                cell = row.findall('td[@class="s"]')
                assert len(cell) == 1
                assert cell[0].text == 'def'

    def test_string_array(self):
        class SomeService(ServiceBase):
            @srpc(String(max_occurs='unbounded'), _returns=Array(String))
            def some_call(s):
                return s

        app = Application([SomeService], 'tns', HttpRpc(), HtmlTable(), Wsdl11())
        server = WsgiApplication(app)

        initial_ctx = WsgiMethodContext(server, {
            'QUERY_STRING': 's=1&s=2',
            'PATH_INFO': '/some_call',
            'REQUEST_METHOD': 'GET',
        }, 'some-content-type')

        ctx, = server.generate_contexts(initial_ctx)
        server.get_in_object(ctx)
        server.get_out_object(ctx)
        server.get_out_string(ctx)

        assert ''.join(ctx.out_string) == '<table class="some_callResponse"><tr><th>string</th></tr><tr><td>1</td></tr><tr><td>2</td></tr></table>'

if __name__ == '__main__':
    unittest.main()
