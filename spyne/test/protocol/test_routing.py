
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

from werkzeug.exceptions import MethodNotAllowed

from spyne.protocol.routing import HttpRouter
from spyne.protocol.routing import UrlMapNotBound
from spyne.application import Application
from spyne.decorator import srpc
from spyne.model.primitive import Integer
from spyne.protocol.http import HttpRpc
from spyne.service import ServiceBase
from spyne.server.wsgi import WsgiApplication
from spyne.server.wsgi import WsgiMethodContext

environ = {
            'QUERY_STRING': '',
            'PATH_INFO': '/some_call',
            'SERVER_PATH':"/",
            'SERVER_NAME': "banana",
            'wsgi.url_scheme': 'http',
            'SERVER_PORT': '9000',
            'REQUEST_METHOD': 'GET',
        }

class Test(unittest.TestCase):

    def test_rules(self):
        class SomeService(ServiceBase):
            @srpc(_returns=Integer)
            def some_call():
                return 0

        router = HttpRouter()
        app = Application([SomeService], 'tns', in_protocol=HttpRpc(), out_protocol=HttpRpc())
        server = WsgiApplication(app)

        initial_ctx = WsgiMethodContext(server, environ , 'some-content-type')

        ctx, = server.generate_contexts(initial_ctx)
        router.bind(ctx.in_document)
        router.add_rule("/foo","bar")
        router.build("bar")

        assert router.match("/foo") == ("bar", {})

    def test_rule_method(self):
        class SomeService(ServiceBase):
            @srpc(_returns=Integer)
            def some_call():
                return 0

        router = HttpRouter()
        app = Application([SomeService], 'tns', in_protocol=HttpRpc(), out_protocol=HttpRpc())
        server = WsgiApplication(app)

        initial_ctx = WsgiMethodContext(server, environ , 'some-content-type')

        ctx, = server.generate_contexts(initial_ctx)
        router.bind(ctx.in_document)
        router.add_rule("/foo","bar","POST")
        router.build("bar")
        try:
            router.match("/foo","GET")
        except Exception,e:
            assert isinstance(e,MethodNotAllowed)

    def test_not_bound_error(self):

        router = HttpRouter()
        try:
            router.build("foo")
        except Exception,e:
            assert isinstance(e,UrlMapNotBound)
