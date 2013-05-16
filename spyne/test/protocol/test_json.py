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


from spyne.model.primitive import Integer
from spyne.test.protocol._test_dictdoc import TDictDocumentTest
from spyne.protocol.json import JsonP
from spyne.protocol.json import JsonDocument
from spyne.protocol.json import JsonEncoder

from spyne import MethodContext
from spyne.application import Application
from spyne.decorator import srpc
from spyne.service import ServiceBase
from spyne.server import ServerBase
from spyne.server.null import NullServer

TestJsonDocument = TDictDocumentTest(json, JsonDocument,
                                            dumps_kwargs=dict(cls=JsonEncoder))


class Test(unittest.TestCase):
    def test_invalid_input(self):
        class SomeService(ServiceBase):
            @srpc()
            def yay():
                pass

        app = Application([SomeService], 'tns',
                                in_protocol=JsonDocument(),
                                out_protocol=JsonDocument())

        server = ServerBase(app)

        initial_ctx = MethodContext(server)
        initial_ctx.in_string = ['{']
        ctx, = server.generate_contexts(initial_ctx)
        assert ctx.in_error.faultcode == 'Client.JsonDecodeError'


class TestJsonP(unittest.TestCase):
    def test_callback_name(self):
        callback_name = 'some_callback'
        retval = 42

        class SomeService(ServiceBase):
            @srpc(_returns=Integer)
            def yay():
                return retval

        app = Application([SomeService], 'tns',
                                in_protocol=JsonDocument(),
                                out_protocol=JsonP(callback_name))

        server = NullServer(app, ostr=True)
        assert ''.join(server.service.yay()) == '%s(%d);' % (callback_name, retval);

    def illustrate_wrappers(self):
        from spyne.model.complex import ComplexModel, Array
        from spyne.model.primitive import Unicode

        class Permission(ComplexModel):
            _type_info = [
                ('application', Unicode),
                ('feature', Unicode),
            ]

        class SomeService(ServiceBase):
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
        print ''.join(server.service.yay())
        # assert false

if __name__ == '__main__':
    unittest.main()
