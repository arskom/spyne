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

#
# Most of the service tests are performed through the interop tests.
#
import unittest

from rpclib.interface.wsdl import Wsdl11
from rpclib.protocol.soap import Soap11

from rpclib.application import Application
from rpclib.decorator import srpc
from rpclib.error import ValidationError
from rpclib.service import ServiceBase
from rpclib.protocol.http import HttpRpc
from rpclib.protocol.soap import Soap11
from rpclib.interface.wsdl import Wsdl11
from rpclib.model.primitive import Integer
from rpclib.model.primitive import String
from rpclib.server import ServerBase

from rpclib import MethodContext
from rpclib.server.wsgi import WsgiMethodContext

Application.transport = 'test'


class TestValidationString(unittest.TestCase):
    def test_min_len(self):
        StrictType = String(min_len=3)

        self.assertEquals(StrictType.validate_string(StrictType, 'aaa'), True)
        self.assertEquals(StrictType.validate_string(StrictType, 'a'), False)

    def test_max_len(self):
        StrictType = String(max_len=3)

        self.assertEquals(StrictType.validate_string(StrictType, 'a'), True)
        self.assertEquals(StrictType.validate_string(StrictType, 'aaa'), True)
        self.assertEquals(StrictType.validate_string(StrictType, 'aaaa'), False)

    def test_pattern(self):
        StrictType = String(pattern='a')

        self.assertEquals(StrictType.validate_string(StrictType, 'a'), True)
        self.assertEquals(StrictType.validate_string(StrictType, 'b'), False)


class TestValidationInteger(unittest.TestCase):
    def test_lt(self):
        StrictType = Integer(lt=3)

        self.assertEquals(StrictType.validate_native(StrictType, 2), True)
        self.assertEquals(StrictType.validate_native(StrictType, 3), False)

    def test_le(self):
        StrictType = Integer(le=3)

        self.assertEquals(StrictType.validate_native(StrictType, 2), True)
        self.assertEquals(StrictType.validate_native(StrictType, 3), True)
        self.assertEquals(StrictType.validate_native(StrictType, 4), False)

    def test_gt(self):
        StrictType = Integer(gt=3)

        self.assertEquals(StrictType.validate_native(StrictType, 4), True)
        self.assertEquals(StrictType.validate_native(StrictType, 3), False)

    def test_ge(self):
        StrictType = Integer(ge=3)

        self.assertEquals(StrictType.validate_native(StrictType, 3), True)
        self.assertEquals(StrictType.validate_native(StrictType, 2), False)

class TestHttpRpcSoftValidation(unittest.TestCase):
    def setUp(self):
        class SomeService(ServiceBase):
            @srpc(String(pattern='a'))
            def some_method(s):
                pass
            @srpc(String(pattern='a', max_occurs=2))
            def some_other_method(s):
                pass

        self.application = Application([SomeService],
            interface=Wsdl11(),
            in_protocol=HttpRpc(validator='soft'),
            out_protocol=Soap11(),
            name='Service', tns='tns',
        )


    def __get_ctx(self, mn, qs):
        ctx = WsgiMethodContext(self.application, {
            'QUERY_STRING': qs,
            'PATH_INFO': '/%s' % mn,
        }, 'some-content-type')

        server = ServerBase(self.application)
        server.get_in_object(ctx)

        return ctx

    def test_http_rpc(self):

        ctx = self.__get_ctx('some_method', 's=1')
        self.assertEquals(ctx.in_error.faultcode, 'Client.ValidationError')

        ctx = self.__get_ctx('some_method', 's=a')
        self.assertEquals(ctx.in_error, None)

        ctx = self.__get_ctx('some_other_method', 's=1')
        self.assertEquals(ctx.in_error.faultcode, 'Client.ValidationError')
        ctx = self.__get_ctx('some_other_method', 's=1&s=2')
        self.assertEquals(ctx.in_error.faultcode, 'Client.ValidationError')
        ctx = self.__get_ctx('some_other_method', 's=1&s=2&s=3')
        self.assertEquals(ctx.in_error.faultcode, 'Client.ValidationError')
        ctx = self.__get_ctx('some_other_method', 's=a&s=a&s=a')
        self.assertEquals(ctx.in_error.faultcode, 'Client.ValidationError')

        ctx = self.__get_ctx('some_other_method', 's=a&s=a')
        self.assertEquals(ctx.in_error, None)
        ctx = self.__get_ctx('some_other_method', 's=a')
        self.assertEquals(ctx.in_error, None)
        ctx = self.__get_ctx('some_other_method', '')
        self.assertEquals(ctx.in_error, None)

class TestSoap11SoftValidation(unittest.TestCase):
    def test_basic(self):
        class SomeService(ServiceBase):
            @srpc(String(pattern='a'))
            def some_method(s):
                pass

        application = Application([SomeService],
            interface=Wsdl11(),
            in_protocol=Soap11(validator='soft'),
            out_protocol=Soap11(),
            name='Service', tns='tns',
        )

        ctx = MethodContext(application)
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

        from rpclib.server import ServerBase

        server = ServerBase(application)
        server.get_in_object(ctx)

        self.assertEquals(isinstance(ctx.in_error, ValidationError), True)

if __name__ == '__main__':
    unittest.main()
