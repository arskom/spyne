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

from spyne.model.fault import Fault
import logging
logging.basicConfig(level=logging.DEBUG)

import unittest

from decimal import Decimal

from spyne import MethodContext
from spyne.application import Application
from spyne.decorator import srpc
from spyne.model.primitive import Integer
from spyne.model.primitive import String
from spyne.model.primitive import DateTime
from spyne.model.primitive import Mandatory
from spyne.model.complex import ComplexModel
from spyne.model.complex import Iterable
from spyne.service import ServiceBase
from spyne.server import ServerBase

def TDictObjectTest(serializer, _DictObjectChild, decode_error):
    class Test(unittest.TestCase):
        '''Most of the service tests are performed through the interop tests.'''

        def test_multiple_return_sd_2(self):
            class SomeService(ServiceBase):
                @srpc(_returns=Iterable(Integer))
                def some_call():
                    return 1, 2

            app = Application([SomeService], 'tns', in_protocol=_DictObjectChild(), out_protocol=_DictObjectChild(skip_depth=2))

            server = ServerBase(app)
            initial_ctx = MethodContext(server)
            initial_ctx.in_string = [serializer.dumps({"some_call":[]})]

            ctx, = server.generate_contexts(initial_ctx)
            server.get_in_object(ctx)
            server.get_out_object(ctx)
            server.get_out_string(ctx)

            assert list(ctx.out_string) == [serializer.dumps(1),serializer.dumps(2)]

        def test_multiple_return_sd_1(self):
            class SomeService(ServiceBase):
                @srpc(_returns=Iterable(Integer))
                def some_call():
                    return 1, 2

            app = Application([SomeService], 'tns',
                                    in_protocol=_DictObjectChild(),
                                    out_protocol=_DictObjectChild(skip_depth=1))

            server = ServerBase(app)
            initial_ctx = MethodContext(server)
            initial_ctx.in_string = [serializer.dumps({"some_call":[]})]

            ctx, = server.generate_contexts(initial_ctx)
            server.get_in_object(ctx)
            server.get_out_object(ctx)
            server.get_out_string(ctx)

            assert list(ctx.out_string) == [serializer.dumps({"integer": [1, 2]})]

        def test_multiple_return_sd_0(self):
            class SomeService(ServiceBase):
                @srpc(_returns=Iterable(Integer))
                def some_call():
                    return 1, 2

            app = Application([SomeService], 'tns', in_protocol=_DictObjectChild(), out_protocol=_DictObjectChild())


            server = ServerBase(app)
            initial_ctx = MethodContext(server)
            initial_ctx.in_string = [serializer.dumps({"some_call":{}})]

            ctx, = server.generate_contexts(initial_ctx)
            server.get_in_object(ctx)
            server.get_out_object(ctx)
            server.get_out_string(ctx)

            assert list(ctx.out_string) == [serializer.dumps({"some_callResponse": {"some_callResult": {"integer": [1, 2]}}})]

            server = ServerBase(app)
            initial_ctx = MethodContext(server)
            initial_ctx.in_string = [serializer.dumps({"some_call":[]})]

            ctx, = server.generate_contexts(initial_ctx)
            server.get_in_object(ctx)
            server.get_out_object(ctx)
            server.get_out_string(ctx)

            assert list(ctx.out_string) == [serializer.dumps({"some_callResponse": {"some_callResult": {"integer": [1, 2]}}})]

        def test_primitive_only(self):
            class SomeComplexModel(ComplexModel):
                i = Integer
                s = String

            class SomeService(ServiceBase):
                @srpc(SomeComplexModel, _returns=SomeComplexModel)
                def some_call(scm):
                    return SomeComplexModel(i=5, s='5x')

            app = Application([SomeService], 'tns', in_protocol=_DictObjectChild(),
                                                 out_protocol=_DictObjectChild())

            server = ServerBase(app)
            initial_ctx = MethodContext(server)
            initial_ctx.in_string = [serializer.dumps({"some_call":[]})]

            ctx, = server.generate_contexts(initial_ctx)
            server.get_in_object(ctx)
            server.get_out_object(ctx)
            server.get_out_string(ctx)

            assert list(ctx.out_string) == [serializer.dumps({"some_callResponse": {"some_callResult": {"i": 5, "s": "5x"}}})]

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

            app = Application([SomeService], 'tns', in_protocol=_DictObjectChild(),
                                                         out_protocol=_DictObjectChild())

            server = ServerBase(app)
            initial_ctx = MethodContext(server)
            initial_ctx.in_string = [serializer.dumps({"some_call":{"ccm": {"c":{"i":3, "s": "3x"}, "i":4, "s": "4x"}}})]

            ctx, = server.generate_contexts(initial_ctx)
            server.get_in_object(ctx)
            server.get_out_object(ctx)
            server.get_out_string(ctx)

            ret = serializer.loads(''.join(ctx.out_string))
            print(ret)

            assert ret['some_callResponse']['some_callResult']['i'] == 4
            assert ret['some_callResponse']['some_callResult']['s'] == '4x'
            assert ret['some_callResponse']['some_callResult']['c']['i'] == 3
            assert ret['some_callResponse']['some_callResult']['c']['s'] == '3x'

        def test_multiple_list(self):
            class SomeService(ServiceBase):
                @srpc(String(max_occurs=Decimal('inf')), _returns=String(max_occurs=Decimal('inf')))
                def some_call(s):
                    return s

            app = Application([SomeService], 'tns', in_protocol=_DictObjectChild(),
                                                    out_protocol=_DictObjectChild())
            server = ServerBase(app)

            initial_ctx = MethodContext(server)
            initial_ctx.in_string = [serializer.dumps({"some_call":[["a","b"]]})]

            ctx, = server.generate_contexts(initial_ctx)
            server.get_in_object(ctx)
            server.get_out_object(ctx)
            server.get_out_string(ctx)

            assert list(ctx.out_string) == [serializer.dumps({"some_callResponse": {"some_callResult": ["a", "b"]}})]

        def test_multiple_dict(self):
            class SomeService(ServiceBase):
                @srpc(String(max_occurs=Decimal('inf')), _returns=String(max_occurs=Decimal('inf')))
                def some_call(s):
                    return s

            app = Application([SomeService], 'tns', in_protocol=_DictObjectChild(),
                                                    out_protocol=_DictObjectChild())
            server = ServerBase(app)

            initial_ctx = MethodContext(server)
            initial_ctx.in_string = [serializer.dumps({"some_call":{"s":["a","b"]}})]

            ctx, = server.generate_contexts(initial_ctx)
            server.get_in_object(ctx)
            server.get_out_object(ctx)
            server.get_out_string(ctx)

            assert list(ctx.out_string) == [serializer.dumps({"some_callResponse": {"some_callResult": ["a", "b"]}})]

        def test_multiple_dict_array(self):
            class SomeService(ServiceBase):
                @srpc(Iterable(String), _returns=Iterable(String))
                def some_call(s):
                    return s

            app = Application([SomeService], 'tns', in_protocol=_DictObjectChild(),
                                                    out_protocol=_DictObjectChild())
            server = ServerBase(app)

            initial_ctx = MethodContext(server)
            initial_ctx.in_string = [serializer.dumps({"some_call":{"s":["a","b"]}})]

            ctx, = server.generate_contexts(initial_ctx)
            server.get_in_object(ctx)
            server.get_out_object(ctx)
            server.get_out_string(ctx)

            assert list(ctx.out_string) == [serializer.dumps({"some_callResponse": {"some_callResult": {"string": ["a", "b"]}}})]

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

            app = Application([SomeService], 'tns', in_protocol=_DictObjectChild(), out_protocol=_DictObjectChild())
            server = ServerBase(app)

            initial_ctx = MethodContext(server)
            initial_ctx.in_string = [serializer.dumps({"some_call": {"ecm": [{"c": {"i":3, "s": "3x"}, "i":4, "s": "4x", "d": "2011-12-13T14:15:16Z"}]}})]

            ctx, = server.generate_contexts(initial_ctx)
            server.get_in_object(ctx)
            server.get_out_object(ctx)
            print(ctx.in_object)
            server.get_out_string(ctx)

            ret = serializer.loads(''.join(ctx.out_string))
            print(ret)
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

        def test_invalid_input(self):
            class SomeService(ServiceBase):
                @srpc()
                def yay():
                    pass

            app = Application([SomeService], 'tns',
                                    in_protocol=_DictObjectChild(),
                                    out_protocol=_DictObjectChild())

            server = ServerBase(app)

            initial_ctx = MethodContext(server)
            initial_ctx.in_string = ['{"some_call": {"yay": ]}}']
            ctx, = server.generate_contexts(initial_ctx)
            assert ctx.in_error.faultcode == decode_error

        def test_invalid_request(self):
            class SomeService(ServiceBase):
                @srpc(Integer, String, DateTime)
                def yay(i,s,d):
                    print(i,s,d)
                    pass

            app = Application([SomeService], 'tns',
                                    in_protocol=_DictObjectChild(validator='soft'),
                                    out_protocol=_DictObjectChild())

            server = ServerBase(app)

            initial_ctx = MethodContext(server)
            initial_ctx.in_string = [serializer.dumps({"some_call": {"yay": []}})]
            ctx, = server.generate_contexts(initial_ctx)

            print(ctx.in_error)
            assert ctx.in_error.faultcode == 'Client.ResourceNotFound'
            print()

        def test_invalid_string(self):
            class SomeService(ServiceBase):
                @srpc(Integer, String, DateTime)
                def yay(i,s,d):
                    print(i,s,d)
                    pass

            app = Application([SomeService], 'tns',
                                    in_protocol=_DictObjectChild(validator='soft'),
                                    out_protocol=_DictObjectChild())
            server = ServerBase(app)

            initial_ctx = MethodContext(server)
            initial_ctx.in_string = [serializer.dumps({"yay": {"s": 1}})]
            ctx, = server.generate_contexts(initial_ctx)
            server.get_in_object(ctx)

            assert ctx.in_error.faultcode == 'Client.ValidationError'

        def test_invalid_number(self):
            class SomeService(ServiceBase):
                @srpc(Integer, String, DateTime)
                def yay(i,s,d):
                    print(i,s,d)
                    pass

            app = Application([SomeService], 'tns',
                                    in_protocol=_DictObjectChild(validator='soft'),
                                    out_protocol=_DictObjectChild())

            server = ServerBase(app)

            initial_ctx = MethodContext(server)
            initial_ctx.in_string = [serializer.dumps({"yay": ["s", "B"]})]
            ctx, = server.generate_contexts(initial_ctx)
            server.get_in_object(ctx)

            assert ctx.in_error.faultcode == 'Client.ValidationError'

        def test_missing_value(self):
            class SomeService(ServiceBase):
                @srpc(Integer, String, Mandatory.DateTime)
                def yay(i,s,d):
                    print(i,s,d)
                    pass

            app = Application([SomeService], 'tns',
                                    in_protocol=_DictObjectChild(validator='soft'),
                                    out_protocol=_DictObjectChild()
                                )
            server = ServerBase(app)

            initial_ctx = MethodContext(server)
            initial_ctx.in_string = [serializer.dumps({"yay": [1, "B"]})]
            ctx, = server.generate_contexts(initial_ctx)
            server.get_in_object(ctx)

            print(ctx.in_error.faultstring)
            assert ctx.in_error.faultcode == 'Client.ValidationError'
            assert ctx.in_error.faultstring.endswith("frequency constraints.")

        def test_invalid_datetime(self):
            class SomeService(ServiceBase):
                @srpc(Integer, String, Mandatory.DateTime)
                def yay(i,s,d):
                    print(i,s,d)
                    pass

            app = Application([SomeService], 'tns',
                    in_protocol=_DictObjectChild(validator='soft'),
                    out_protocol=_DictObjectChild()
                )

            server = ServerBase(app)

            initial_ctx = MethodContext(server)
            initial_ctx.in_string = serializer.dumps({"yay": {"d":"a2011"}})
            ctx, = server.generate_contexts(initial_ctx)
            server.get_in_object(ctx)

            assert ctx.in_error.faultcode == 'Client.ValidationError'

        def test_primitive_with_skip_depth(self):
            class SomeService(ServiceBase):
                @srpc(_returns=String)
                def some_call():
                    return "foo"

            app = Application([SomeService], 'tns',
                    in_protocol=_DictObjectChild(),
                    out_protocol=_DictObjectChild(skip_depth=2)
                )

            server = ServerBase(app)
            initial_ctx = MethodContext(server)
            initial_ctx.in_string = [serializer.dumps({"some_call":[]})]

            ctx, = server.generate_contexts(initial_ctx)
            server.get_in_object(ctx)
            server.get_out_object(ctx)
            server.get_out_string(ctx)

        def test_fault_to_dict(self):
            class SomeService(ServiceBase):
                @srpc(_returns=String)
                def some_call():
                    raise Fault()

            app = Application([SomeService], 'tns',
                                in_protocol=_DictObjectChild(),
                                out_protocol=_DictObjectChild(skip_depth=2))

            server = ServerBase(app)
            initial_ctx = MethodContext(server)
            initial_ctx.in_string = serializer.dumps({"some_call":[]})

            ctx, = server.generate_contexts(initial_ctx)
            server.get_in_object(ctx)
            server.get_out_object(ctx)
            server.get_out_string(ctx)

    return Test
