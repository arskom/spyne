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

import json
import logging
logging.basicConfig(level=logging.DEBUG)

import unittest

from rpclib import MethodContext
from rpclib.application import Application
from rpclib.decorator import srpc
from rpclib.model.primitive import Integer
from rpclib.model.primitive import String
from rpclib.model.primitive import DateTime
from rpclib.model.complex import ComplexModel
from rpclib.model.complex import Iterable
from rpclib.interface.wsdl import Wsdl11
from rpclib.protocol.json import JsonObject
from rpclib.service import ServiceBase
from rpclib.server import ServerBase

class Test(unittest.TestCase):
    '''Most of the service tests are performed through the interop tests.'''

    def test_multiple_return_sd_2(self):
        class SomeService(ServiceBase):
            @srpc(_returns=Iterable(Integer))
            def some_call():
                return 1, 2

        app = Application([SomeService], 'tns', JsonObject(), JsonObject(skip_depth=2),
                                                                       Wsdl11())

        server = ServerBase(app)
        initial_ctx = MethodContext(server)
        initial_ctx.in_string = ['{"some_call":[]}']

        ctx, = server.generate_contexts(initial_ctx)
        server.get_in_object(ctx)
        server.get_out_object(ctx)
        server.get_out_string(ctx)

        assert list(ctx.out_string) == ['1','2']

    def test_multiple_return_sd_1(self):
        class SomeService(ServiceBase):
            @srpc(_returns=Iterable(Integer))
            def some_call():
                return 1, 2

        app = Application([SomeService], 'tns', JsonObject(), JsonObject(skip_depth=1),
                                                                       Wsdl11())

        server = ServerBase(app)
        initial_ctx = MethodContext(server)
        initial_ctx.in_string = ['{"some_call":[]}']

        ctx, = server.generate_contexts(initial_ctx)
        server.get_in_object(ctx)
        server.get_out_object(ctx)
        server.get_out_string(ctx)

        assert list(ctx.out_string) == ['{"integer": [1, 2]}']

    def test_multiple_return_sd_0(self):
        class SomeService(ServiceBase):
            @srpc(_returns=Iterable(Integer))
            def some_call():
                return 1, 2

        app = Application([SomeService], 'tns', JsonObject(), JsonObject(),
                                                                       Wsdl11())

        server = ServerBase(app)
        initial_ctx = MethodContext(server)
        initial_ctx.in_string = ['{"some_call":{}}']

        ctx, = server.generate_contexts(initial_ctx)
        server.get_in_object(ctx)
        server.get_out_object(ctx)
        server.get_out_string(ctx)

        assert list(ctx.out_string) == ['{"some_callResponse": {"some_callResult": {"integer": [1, 2]}}}' ]

        server = ServerBase(app)
        initial_ctx = MethodContext(server)
        initial_ctx.in_string = ['{"some_call":[]}']

        ctx, = server.generate_contexts(initial_ctx)
        server.get_in_object(ctx)
        server.get_out_object(ctx)
        server.get_out_string(ctx)

        assert list(ctx.out_string) == ['{"some_callResponse": {"some_callResult": {"integer": [1, 2]}}}']

    def test_primitive_only(self):
        class SomeComplexModel(ComplexModel):
            i = Integer
            s = String

        class SomeService(ServiceBase):
            @srpc(SomeComplexModel, _returns=SomeComplexModel)
            def some_call(scm):
                return SomeComplexModel(i=5, s='5x')

        app = Application([SomeService], 'tns', JsonObject(), JsonObject(),
                                                                       Wsdl11())

        server = ServerBase(app)
        initial_ctx = MethodContext(server)
        initial_ctx.in_string = ['{"some_call":[]}']

        ctx, = server.generate_contexts(initial_ctx)
        server.get_in_object(ctx)
        server.get_out_object(ctx)
        server.get_out_string(ctx)

        assert list(ctx.out_string) == ['{"some_callResponse": {"some_callResult": {"i": 5, "s": "5x"}}}']

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
                return CCM(c=ccm.c, i=ccm.i, s=ccm.s)

        app = Application([SomeService], 'tns', JsonObject(), JsonObject(),
                                                                       Wsdl11())
        server = ServerBase(app)
        initial_ctx = MethodContext(server)
        initial_ctx.in_string = ['{"some_call":{"ccm": {"c":{"i":3, "s": "3x"}, "i":4, "s": "4x"}}}']

        ctx, = server.generate_contexts(initial_ctx)
        server.get_in_object(ctx)
        server.get_out_object(ctx)
        server.get_out_string(ctx)

        ret = json.loads(''.join(ctx.out_string))
        print ret

        assert ret['some_callResponse']['some_callResult']['i'] == 4
        assert ret['some_callResponse']['some_callResult']['s'] == '4x'
        assert ret['some_callResponse']['some_callResult']['c']['i'] == 3
        assert ret['some_callResponse']['some_callResult']['c']['s'] == '3x'

    def test_multiple_list(self):
        class SomeService(ServiceBase):
            @srpc(String(max_occurs=float('inf')), _returns=String(max_occurs=float('inf')))
            def some_call(s):
                return s

        app = Application([SomeService], 'tns', JsonObject(), JsonObject(), Wsdl11())
        server = ServerBase(app)

        initial_ctx = MethodContext(server)
        initial_ctx.in_string = ['{"some_call":[["a","b"]]}']

        ctx, = server.generate_contexts(initial_ctx)
        server.get_in_object(ctx)
        server.get_out_object(ctx)
        server.get_out_string(ctx)

        assert list(ctx.out_string) == ['{"some_callResponse": {"some_callResult": ["a", "b"]}}']

    def test_multiple_dict(self):
        class SomeService(ServiceBase):
            @srpc(String(max_occurs=float('inf')), _returns=String(max_occurs=float('inf')))
            def some_call(s):
                return s

        app = Application([SomeService], 'tns', JsonObject(), JsonObject(), Wsdl11())
        server = ServerBase(app)

        initial_ctx = MethodContext(server)
        initial_ctx.in_string = ['{"some_call":{"s":["a","b"]}}']

        ctx, = server.generate_contexts(initial_ctx)
        server.get_in_object(ctx)
        server.get_out_object(ctx)
        server.get_out_string(ctx)

        assert list(ctx.out_string) == ['{"some_callResponse": {"some_callResult": ["a", "b"]}}']

    def test_multiple_dict_array(self):
        class SomeService(ServiceBase):
            @srpc(Iterable(String), _returns=Iterable(String))
            def some_call(s):
                return s

        app = Application([SomeService], 'tns', JsonObject(), JsonObject(), Wsdl11())
        server = ServerBase(app)

        initial_ctx = MethodContext(server)
        initial_ctx.in_string = ['{"some_call":{"s":["a","b"]}}']

        ctx, = server.generate_contexts(initial_ctx)
        server.get_in_object(ctx)
        server.get_out_object(ctx)
        server.get_out_string(ctx)

        assert list(ctx.out_string) == ['{"some_callResponse": {"some_callResult": {"string": ["a", "b"]}}}']

    def test_multiple_dict_complex_array(self):
        class CM(ComplexModel):
            i = Integer
            s = String

        class CCM(ComplexModel):
            c = CM
            i = Integer
            s = String

        class ECM(CCM):
            d = DateTime

        class SomeService(ServiceBase):
            @srpc(Iterable(ECM), _returns=Iterable(ECM))
            def some_call(ecm):
                return ecm

        app = Application([SomeService], 'tns', JsonObject(), JsonObject(), Wsdl11())
        server = ServerBase(app)

        initial_ctx = MethodContext(server)
        initial_ctx.in_string = ['{"some_call": {"ecm": [{"c": {"i":3, "s": "3x"}, "i":4, "s": "4x", "d": "2011-12-13T14:15:16Z"}]}}']

        ctx, = server.generate_contexts(initial_ctx)
        server.get_in_object(ctx)
        server.get_out_object(ctx)
        print ctx.in_object
        server.get_out_string(ctx)

        ret = json.loads(''.join(ctx.out_string))
        print ret
        assert ret['some_callResponse']
        assert ret['some_callResponse']['some_callResult']
        assert ret['some_callResponse']['some_callResult']['ECM']
        assert ret['some_callResponse']['some_callResult']['ECM'][0]
        assert ret['some_callResponse']['some_callResult']['ECM'][0]["c"]
        assert ret['some_callResponse']['some_callResult']['ECM'][0]["c"]["i"] == 3
        assert ret['some_callResponse']['some_callResult']['ECM'][0]["c"]["s"] == "3x"
        assert ret['some_callResponse']['some_callResult']['ECM'][0]["i"] == 4
        assert ret['some_callResponse']['some_callResult']['ECM'][0]["s"] == "4x"
        assert ret['some_callResponse']['some_callResult']['ECM'][0]["d"] == "2011-12-13T14:15:16+00:00"

if __name__ == '__main__':
    unittest.main()
