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

from pprint import pformat
from urllib import urlencode

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

def _start_response(code, headers):
    print(code, pformat(headers))

def _call_wsgi_app_kwargs(app, **kwargs):
    return _call_wsgi_app(app, kwargs.items())

def _call_wsgi_app(app, pairs):
    out_string = ''.join(app({
        'QUERY_STRING': urlencode(pairs),
        'PATH_INFO': '/some_call',
        'REQUEST_METHOD': 'GET',
        'SERVER_NAME': 'rpclib.test',
        'SERVER_PORT': '0',
        'wsgi.url_scheme': 'http',
    }, _start_response))

    return out_string


class CM(ComplexModel):
    i = Integer
    s = String

class CCM(ComplexModel):
    c = CM
    i = Integer
    s = String

class TestHtmlColumnTable(unittest.TestCase):
    def test_complex_array(self):
        class SomeService(ServiceBase):
            @srpc(CCM, _returns=Array(CCM))
            def some_call(ccm):
                return [ccm] * 5

        app = Application([SomeService], 'tns', HttpRpc(), HtmlTable(field_name_attr='class'), Wsdl11())
        server = WsgiApplication(app)

        out_string = _call_wsgi_app_kwargs(server,
                ccm_i='456',
                ccm_s='def',
                ccm_c_i='123',
                ccm_c_s='abc',
            )

        elt = html.fromstring(out_string)
        print(html.tostring(elt, pretty_print=True))

        resp = elt.find_class('some_callResponse')
        assert len(resp) == 1
        for i in range(len(elt)):
            row = elt[i]
            if i == 0:  # check for field names in table header
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


            else: # check for field values in table body
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

        out_string = _call_wsgi_app(server, (('s', '1'), ('s', '2')) )
        assert out_string == '<table class="some_callResponse"><tr><th>string</th></tr><tr><td>1</td></tr><tr><td>2</td></tr></table>'

class TestHtmlRowTable(unittest.TestCase):
    def test_complex(self):
        class SomeService(ServiceBase):
            @srpc(CCM, _returns=CCM)
            def some_call(ccm):
                return ccm


        app = Application([SomeService], 'tns', HttpRpc(),
                 HtmlTable(field_name_attr='class', fields_as='rows'), Wsdl11())
        server = WsgiApplication(app)

        out_string = _call_wsgi_app_kwargs(server,
                         ccm_c_s='abc', ccm_c_i='123', ccm_i='456', ccm_s='def')

        elt = html.fromstring(out_string)
        print(html.tostring(elt, pretty_print=True))

        # Here's what this is supposed to return
        """
        <table class="some_callResponse">
            <tr>
                <th class="i">i</th>
                <td class="i">456</td>
            </tr>
            <tr>
                <th class="c_i">c_i</th>
                <td class="c_i">123</td>
            </tr>
            <tr>
                <th class="c_s">c_s</th>
                <td class="c_s">abc</td>
            </tr>
            <tr>
                <th class="s">s</th>
                <td class="s">def</td>
            </tr>
        </table>
        """

        resp = elt.find_class('some_callResponse')
        assert len(resp) == 1

        assert elt.xpath('//th[@class="i"]/text()')[0] == 'i'
        assert elt.xpath('//td[@class="i"]/text()')[0] == '456'

        assert elt.xpath('//th[@class="c_i"]/text()')[0] == 'c_i'
        assert elt.xpath('//td[@class="c_i"]/text()')[0] == '123'

        assert elt.xpath('//th[@class="c_s"]/text()')[0] == 'c_s'
        assert elt.xpath('//td[@class="c_s"]/text()')[0] == 'abc'

        assert elt.xpath('//th[@class="s"]/text()')[0] == 's'
        assert elt.xpath('//td[@class="s"]/text()')[0] == 'def'


    def test_string_array(self):
        class SomeService(ServiceBase):
            @srpc(String(max_occurs='unbounded'), _returns=Array(String))
            def some_call(s):
                return s

        app = Application([SomeService], 'tns', HttpRpc(), HtmlTable(fields_as='rows'), Wsdl11())
        server = WsgiApplication(app)

        out_string = _call_wsgi_app(server, (('s', '1'), ('s', '2')) )
        assert out_string == '<table class="some_callResponse"><tr><td>1</td></tr><tr><td>2</td></tr></table>'


if __name__ == '__main__':
    unittest.main()
