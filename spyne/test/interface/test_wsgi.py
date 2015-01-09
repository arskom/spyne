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

import unittest

from spyne.util import six
from spyne.util.six import StringIO

from spyne.protocol.soap.soap11 import Soap11
from spyne.server.wsgi import WsgiApplication
from spyne.application import Application
from spyne.model.primitive import Unicode
from spyne.decorator import rpc
from spyne.const.xml_ns import wsdl as NS_WSDL
from spyne.service import ServiceBase


def start_response(code, headers):
    print(code, headers)


class Test(unittest.TestCase):
    def setUp(self):
        class SomeService(ServiceBase):
            @rpc(Unicode)
            def some_call(ctx, some_str):
                print(some_str)


        app = Application([SomeService], "some_tns", in_protocol=Soap11(),
                                                     out_protocol=Soap11())
        self.wsgi_app = WsgiApplication(app)

    def test_document_built(self):
        self.h = 0

        def on_wsdl_document_built(doc):
            self.h += 1

        self.wsgi_app.doc.wsdl11.event_manager.add_listener("wsdl_document_built",
                                                         on_wsdl_document_built)
        self.wsgi_app.doc.wsdl11.build_interface_document("http://some_url/")

        assert self.h == 1

    def test_document_manipulation(self):
        def on_wsdl_document_built(doc):
            doc.root_elt.tag = 'ehe'

        self.wsgi_app.doc.wsdl11.event_manager.add_listener(
                                  "wsdl_document_built", on_wsdl_document_built)
        self.wsgi_app.doc.wsdl11.build_interface_document("http://some_url/")
        d = self.wsgi_app.doc.wsdl11.get_interface_document()

        from lxml import etree

        assert etree.fromstring(d).tag == 'ehe'

    def test_wsgi(self):
        retval = ''.join(self.wsgi_app({
            'PATH_INFO': '/',
            'QUERY_STRING': 'wsdl',
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '7000',
            'REQUEST_METHOD': 'GET',
            'wsgi.url_scheme': 'http',
            'wsgi.input': StringIO(),
        }, start_response))

        from lxml import etree

        assert etree.fromstring(retval).tag == '{%s}definitions' % NS_WSDL

if __name__ == '__main__':
    unittest.main()
