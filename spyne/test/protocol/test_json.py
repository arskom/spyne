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
try:
    import simplejson as json
except ImportError:
    import json


from spyne import MethodContext
from spyne import Application
from spyne import rpc,srpc
from spyne import Service
from spyne.model import Integer, Unicode, ComplexModel
from spyne.protocol.json import JsonP
from spyne.protocol.json import JsonDocument
from spyne.protocol.json import JsonEncoder
from spyne.protocol.json import _SpyneJsonRpc1
from spyne.server import ServerBase
from spyne.server.null import NullServer

from spyne.test.protocol._test_dictdoc import TDictDocumentTest
from spyne.test.protocol._test_dictdoc import TDry


class TestDictDocument(TDictDocumentTest(json, JsonDocument,
                                           dumps_kwargs=dict(cls=JsonEncoder))):
    def dumps(self, o):
        return super(TestDictDocument, self).dumps(o).encode('utf8')

    def loads(self, o):
        return super(TestDictDocument, self).loads(o.decode('utf8'))

_dry_sjrpc1 = TDry(json, _SpyneJsonRpc1)

class TestSpyneJsonRpc1(unittest.TestCase):
    def test_call(self):
        class SomeService(Service):
            @srpc(Integer, _returns=Integer)
            def yay(i):
                print(i)
                return i

        ctx = _dry_sjrpc1([SomeService],
                    {"ver": 1, "body": {"yay": {"i":5}}}, True)

        print(ctx)
        print(list(ctx.out_string))
        assert ctx.out_document == {"ver": 1, "body": 5}

    def test_call_with_header(self):
        class SomeHeader(ComplexModel):
            i = Integer

        class SomeService(Service):
            __in_header__ = SomeHeader
            @rpc(Integer, _returns=Integer)
            def yay(ctx, i):
                print(ctx.in_header)
                return ctx.in_header.i

        ctx = _dry_sjrpc1([SomeService],
                    {"ver": 1, "body": {"yay": None}, "head": {"i":5}}, True)

        print(ctx)
        print(list(ctx.out_string))
        assert ctx.out_document == {"ver": 1, "body": 5}

    def test_error(self):
        class SomeHeader(ComplexModel):
            i = Integer

        class SomeService(Service):
            __in_header__ = SomeHeader
            @rpc(Integer, Integer, _returns=Integer)
            def div(ctx, dividend, divisor):
                return dividend / divisor

        ctx = _dry_sjrpc1([SomeService],
                    {"ver": 1, "body": {"div": [4,0]}}, True)

        print(ctx)
        print(list(ctx.out_string))
        assert ctx.out_document == {"ver": 1, "fault": {
                        'faultcode': 'Server', 'faultstring': 'Internal Error'}}


class TestJsonDocument(unittest.TestCase):
    def test_out_kwargs(self):
        class SomeService(Service):
            @srpc()
            def yay():
                pass

        app = Application([SomeService], 'tns',
                                in_protocol=JsonDocument(),
                                out_protocol=JsonDocument())

        assert 'cls' in app.out_protocol.kwargs
        assert not ('cls' in app.in_protocol.kwargs)

        app = Application([SomeService], 'tns',
                                in_protocol=JsonDocument(),
                                out_protocol=JsonDocument(cls='hey'))

        assert app.out_protocol.kwargs['cls'] == 'hey'
        assert not ('cls' in app.in_protocol.kwargs)

    def test_invalid_input(self):
        class SomeService(Service):
            pass

        app = Application([SomeService], 'tns',
                                in_protocol=JsonDocument(),
                                out_protocol=JsonDocument())

        server = ServerBase(app)

        initial_ctx = MethodContext(server, MethodContext.SERVER)
        initial_ctx.in_string = [b'{']
        ctx, = server.generate_contexts(initial_ctx, in_string_charset='utf8')
        assert ctx.in_error.faultcode == 'Client.JsonDecodeError'


class TestJsonP(unittest.TestCase):
    def test_callback_name(self):
        callback_name = 'some_callback'

        class SomeComplexModel(ComplexModel):
            i = Integer
            s = Unicode

        v1 = 42
        v2 = SomeComplexModel(i=42, s='foo')

        class SomeService(Service):
            @srpc(_returns=Integer)
            def yay():
                return v1

            @srpc(_returns=SomeComplexModel)
            def complex():
                return v2

        app = Application([SomeService], 'tns',
                                in_protocol=JsonDocument(),
                                out_protocol=JsonP(callback_name))

        server = NullServer(app, ostr=True)

        ret = server.service.yay()
        ret = list(ret)
        print(b''.join(ret))
        assert b''.join(ret) == b''.join((callback_name.encode('utf8'), b'(',
                                             str(v1).encode('utf8'), b');'))

        ret = server.service.complex()
        ret = list(ret)
        print(b''.join(ret))
        assert b''.join(ret) == b''.join((callback_name.encode('utf8'), b'(',
                                    json.dumps({"i": 42, "s": "foo"}).encode('utf-8') , b');'))


    def test_wrapped_array_in_wrapped_response(self):
        from spyne.model.complex import ComplexModel, Array
        from spyne.model.primitive import Unicode

        class Permission(ComplexModel):
            _type_info = [
                ('application', Unicode),
                ('feature', Unicode),
            ]

        class SomeService(Service):
            @srpc(_returns=Array(Permission))
            def yay():
                return [
                    Permission(application='app', feature='f1'),
                    Permission(application='app', feature='f2')
                ]

        app = Application([SomeService], 'tns',
                            in_protocol=JsonDocument(),
                            out_protocol=JsonDocument(ignore_wrappers=False))

        server = NullServer(app, ostr=True)
        retstr = b''.join(server.service.yay()).decode('utf-8')
        print(retstr)
        assert retstr == '{"yayResponse": {"yayResult": [' \
            '{"Permission": {"application": "app", "feature": "f1"}}, ' \
            '{"Permission": {"application": "app", "feature": "f2"}}]}}'


if __name__ == '__main__':
    unittest.main()
