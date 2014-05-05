# coding: utf-8
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
from wsgiref.util import setup_testing_defaults
from wsgiref.validate import validator

from lxml import etree
from pyramid import testing
from pyramid.config import Configurator
from pyramid.request import Request

from spyne.protocol.soap import Soap11
from spyne.service import ServiceBase
from spyne.decorator import srpc
from spyne import Application
from spyne.model import Unicode, Integer, Iterable
from spyne.server.pyramid import PyramidApplication


class SpyneIntegrationTest(unittest.TestCase):
    """Tests for integration of Spyne into Pyramid view callable"""
    class HelloWorldService(ServiceBase):
        @srpc(Unicode, Integer, _returns=Iterable(Unicode))
        def say_hello(name, times):
            for i in range(times):
                yield 'Hello, %s' % name

    def setUp(self):
        request = testing.DummyRequest()
        self.config = testing.setUp(request=request)

    def tearDown(self):
        testing.tearDown()

    def testGetWsdl(self):
        """Simple test for serving of WSDL by spyne through pyramid route"""
        application = PyramidApplication(
            Application([self.HelloWorldService],
                        tns='spyne.examples.hello',
                        in_protocol=Soap11(validator='lxml'),
                        out_protocol=Soap11()))

        config = Configurator(settings={'debug_all': True})
        config.add_route('home', '/')
        config.add_view(application, route_name='home')
        wsgi_app = validator(config.make_wsgi_app())

        env = {
            'SCRIPT_NAME': '',
            'REQUEST_METHOD': 'GET',
            'PATH_INFO': '/',
            'QUERY_STRING': 'wsdl',
        }
        setup_testing_defaults(env)

        request = Request(env)
        resp = request.get_response(wsgi_app)
        self.assert_(resp.status.startswith("200 "))
        node = etree.XML(resp.body)  # will throw exception if non well formed

