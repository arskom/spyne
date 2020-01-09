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

import unittest

from spyne.application import Application
from spyne.decorator import srpc
from spyne.error import ValidationError
from spyne.service import Service
from spyne.protocol.http import HttpRpc
from spyne.protocol.soap import Soap11
from spyne.model.primitive import Integer
from spyne.model.primitive import String
from spyne.server import ServerBase
from spyne.server.wsgi import WsgiApplication

from spyne import MethodContext
from spyne.server.wsgi import WsgiMethodContext

Application.transport = 'test'


class TestValidationString(unittest.TestCase):
    def test_min_len(self):
        StrictType = String(min_len=3)

        self.assertEqual(StrictType.validate_string(StrictType, 'aaa'), True)
        self.assertEqual(StrictType.validate_string(StrictType, 'a'), False)

    def test_max_len(self):
        StrictType = String(max_len=3)

        self.assertEqual(StrictType.validate_string(StrictType, 'a'), True)
        self.assertEqual(StrictType.validate_string(StrictType, 'aaa'), True)
        self.assertEqual(StrictType.validate_string(StrictType, 'aaaa'), False)

    def test_pattern(self):
        # Pattern match needs to be checked after the string is decoded, that's
        # why we need to use validate_native here.
        StrictType = String(pattern='[a-z]')

        self.assertEqual(StrictType.validate_native(StrictType, 'a'), True)
        self.assertEqual(StrictType.validate_native(StrictType, 'a1'), False)
        self.assertEqual(StrictType.validate_native(StrictType, '1'), False)


class TestValidationInteger(unittest.TestCase):
    def test_lt(self):
        StrictType = Integer(lt=3)

        self.assertEqual(StrictType.validate_native(StrictType, 2), True)
        self.assertEqual(StrictType.validate_native(StrictType, 3), False)

    def test_le(self):
        StrictType = Integer(le=3)

        self.assertEqual(StrictType.validate_native(StrictType, 2), True)
        self.assertEqual(StrictType.validate_native(StrictType, 3), True)
        self.assertEqual(StrictType.validate_native(StrictType, 4), False)

    def test_gt(self):
        StrictType = Integer(gt=3)

        self.assertEqual(StrictType.validate_native(StrictType, 4), True)
        self.assertEqual(StrictType.validate_native(StrictType, 3), False)

    def test_ge(self):
        StrictType = Integer(ge=3)

        self.assertEqual(StrictType.validate_native(StrictType, 3), True)
        self.assertEqual(StrictType.validate_native(StrictType, 2), False)

class TestHttpRpcSoftValidation(unittest.TestCase):
    def setUp(self):
        class SomeService(Service):
            @srpc(String(pattern='a'))
            def some_method(s):
                pass
            @srpc(String(pattern='a', max_occurs=2))
            def some_other_method(s):
                pass

        self.application = Application([SomeService],
            in_protocol=HttpRpc(validator='soft'),
            out_protocol=Soap11(),
            name='Service', tns='tns',
        )


    def __get_ctx(self, mn, qs):
        server = WsgiApplication(self.application)
        ctx = WsgiMethodContext(server, {
            'QUERY_STRING': qs,
            'PATH_INFO': '/%s' % mn,
            'REQUEST_METHOD': "GET",
            'SERVER_NAME': 'localhost',
        }, 'some-content-type')

        ctx, = server.generate_contexts(ctx)
        server.get_in_object(ctx)

        return ctx

    def test_http_rpc(self):
        ctx = self.__get_ctx('some_method', 's=1')
        self.assertEqual(ctx.in_error.faultcode, 'Client.ValidationError')

        ctx = self.__get_ctx('some_method', 's=a')
        self.assertEqual(ctx.in_error, None)

        ctx = self.__get_ctx('some_other_method', 's=1')
        self.assertEqual(ctx.in_error.faultcode, 'Client.ValidationError')
        ctx = self.__get_ctx('some_other_method', 's=1&s=2')
        self.assertEqual(ctx.in_error.faultcode, 'Client.ValidationError')
        ctx = self.__get_ctx('some_other_method', 's=1&s=2&s=3')
        self.assertEqual(ctx.in_error.faultcode, 'Client.ValidationError')
        ctx = self.__get_ctx('some_other_method', 's=a&s=a&s=a')
        self.assertEqual(ctx.in_error.faultcode, 'Client.ValidationError')

        ctx = self.__get_ctx('some_other_method', 's=a&s=a')
        self.assertEqual(ctx.in_error, None)
        ctx = self.__get_ctx('some_other_method', 's=a')
        self.assertEqual(ctx.in_error, None)
        ctx = self.__get_ctx('some_other_method', '')
        self.assertEqual(ctx.in_error, None)

class TestSoap11SoftValidation(unittest.TestCase):
    def test_basic(self):
        class SomeService(Service):
            @srpc(String(pattern='a'))
            def some_method(s):
                pass

        application = Application([SomeService],
            in_protocol=Soap11(validator='soft'),
            out_protocol=Soap11(),
            name='Service', tns='tns',
        )
        server = ServerBase(application)

        ctx = MethodContext(server, MethodContext.SERVER)
        ctx.in_string = [u"""
            <SOAP-ENV:Envelope xmlns:ns0="tns"
                               xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
               <SOAP-ENV:Body>
                  <ns0:some_method>
                     <ns0:s>OK</ns0:s>
                  </ns0:some_method>
               </SOAP-ENV:Body>
            </SOAP-ENV:Envelope>
        """]

        ctx, = server.generate_contexts(ctx)
        server.get_in_object(ctx)

        self.assertEqual(isinstance(ctx.in_error, ValidationError), True)

if __name__ == '__main__':
    unittest.main()
