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
import logging
logging.basicConfig(level=logging.DEBUG)

from spyne.util.six import BytesIO

import msgpack

from spyne import MethodContext
from spyne.application import Application
from spyne.decorator import rpc
from spyne.decorator import srpc
from spyne.service import ServiceBase
from spyne.model.complex import Array
from spyne.model.primitive import String
from spyne.model.complex import ComplexModel
from spyne.model.primitive import Unicode
from spyne.protocol.msgpack import MessagePackDocument
from spyne.protocol.msgpack import MessagePackRpc
from spyne.server import ServerBase
from spyne.server.wsgi import WsgiApplication
from spyne.test.protocol._test_dictdoc import TDictDocumentTest

from spyne.test.test_service import start_response


TestMessagePackDocument  = TDictDocumentTest(msgpack, MessagePackDocument)

class TestMessagePackRpc(unittest.TestCase):
    def test_invalid_input(self):
        class SomeService(ServiceBase):
            @srpc()
            def yay():
                pass

        app = Application([SomeService], 'tns',
                                in_protocol=MessagePackDocument(),
                                out_protocol=MessagePackDocument())

        server = ServerBase(app)

        initial_ctx = MethodContext(server, MethodContext.SERVER)
        initial_ctx.in_string = ['\xdf']  # Invalid input
        ctx, = server.generate_contexts(initial_ctx)
        assert ctx.in_error.faultcode == 'Client.MessagePackDecodeError'

    def test_rpc(self):
        data = {"a":"b", "c": "d"}

        class KeyValuePair(ComplexModel):
            key = Unicode
            value = Unicode

        class Service(ServiceBase):
            @rpc(String(max_occurs='unbounded'),
                    _returns=Array(KeyValuePair),
                    _in_variable_names={
                        'keys': 'key'
                    }
                )
            def get_values(ctx, keys):
                for k in keys:
                    yield KeyValuePair(key=k, value=data[k])

        application = Application([Service],
            in_protocol=MessagePackRpc(),
            out_protocol=MessagePackRpc(ignore_wrappers=False),
            name='Service', tns='tns'
        )
        server = WsgiApplication(application)

        input_string = msgpack.packb([0,0,"get_values", [["a","c"]] ])
        input_stream = BytesIO(input_string)

        ret = server({
            'CONTENT_LENGTH': str(len(input_string)),
            'CONTENT_TYPE': 'application/x-msgpack',
            'HTTP_CONNECTION': 'close',
            'HTTP_CONTENT_LENGTH': str(len(input_string)),
            'HTTP_CONTENT_TYPE': 'application/x-msgpack',
            'PATH_INFO': '/',
            'QUERY_STRING': '',
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '7000',
            'REQUEST_METHOD': 'POST',
            'wsgi.url_scheme': 'http',
            'wsgi.input': input_stream,
        }, start_response)

        ret = b''.join(ret)
        print(repr(ret))
        print(msgpack.unpackb(ret))
        s = msgpack.packb([1, 0, None, {'get_valuesResponse': {
            'get_valuesResult': [
                  {"KeyValuePair": {'value': 'b', 'key': 'a'}},
                  {"KeyValuePair": {'value': 'd', 'key': 'c'}},
                ]
            }}
        ])
        print(s)
        assert ret == s


if __name__ == '__main__':
    unittest.main()
