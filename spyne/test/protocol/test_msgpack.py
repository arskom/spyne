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

import logging

logging.basicConfig(level=logging.DEBUG)

import unittest
from io import BytesIO

import msgpack

from spyne import MethodContext
from spyne.application import Application
from spyne.decorator import rpc, srpc
from spyne.model.complex import Array, ComplexModel
from spyne.model.primitive import String, Unicode
from spyne.protocol.msgpack import MessagePackDocument, MessagePackRpc
from spyne.server import ServerBase
from spyne.server.wsgi import WsgiApplication
from spyne.service import Service
from spyne.test.protocol._test_dictdoc import TDictDocumentTest
from spyne.test.test_service import start_response


def convert_dict(d):
    if not isinstance(d, dict):
        return d

    r = {}

    for k, v in d.items():
        r[k.encode("utf8")] = convert_dict(v)

    return r


# apply spyne defaults to test unpacker
TestMessagePackDocument = TDictDocumentTest(
    msgpack,
    MessagePackDocument,
    loads_kwargs=dict(use_list=False),
    convert_dict=convert_dict,
)


class TestMessagePackRpc(unittest.TestCase):
    def test_invalid_input(self):
        class SomeService(Service):
            @srpc()
            def yay():
                pass

        app = Application(
            [SomeService],
            "tns",
            in_protocol=MessagePackDocument(),
            out_protocol=MessagePackDocument(),
        )

        server = ServerBase(app)

        initial_ctx = MethodContext(server, MethodContext.SERVER)
        initial_ctx.in_string = [b"\xdf"]  # Invalid input
        (ctx,) = server.generate_contexts(initial_ctx)
        assert ctx.in_error.faultcode == "Client.MessagePackDecodeError"

    def test_rpc(self):
        data = {"a": "b", "c": "d"}

        class KeyValuePair(ComplexModel):
            key = Unicode
            value = Unicode

        class SomeService(Service):
            @rpc(
                String(max_occurs="unbounded"),
                _returns=Array(KeyValuePair),
                _in_variable_names={"keys": "key"},
            )
            def get_values(ctx, keys):
                for k in keys:
                    yield KeyValuePair(key=k, value=data[k])

        application = Application(
            [SomeService],
            in_protocol=MessagePackRpc(),
            out_protocol=MessagePackRpc(ignore_wrappers=False),
            name="Service",
            tns="tns",
        )
        server = WsgiApplication(application)

        input_string = msgpack.packb([0, 0, "get_values", [["a", "c"]]])
        input_stream = BytesIO(input_string)

        ret = server(
            {
                "CONTENT_LENGTH": str(len(input_string)),
                "CONTENT_TYPE": "application/x-msgpack",
                "HTTP_CONNECTION": "close",
                "HTTP_CONTENT_LENGTH": str(len(input_string)),
                "HTTP_CONTENT_TYPE": "application/x-msgpack",
                "PATH_INFO": "/",
                "QUERY_STRING": "",
                "SERVER_NAME": "localhost",
                "SERVER_PORT": "7000",
                "REQUEST_METHOD": "POST",
                "wsgi.url_scheme": "http",
                "wsgi.input": input_stream,
            },
            start_response,
        )

        ret = b"".join(ret)
        print(repr(ret))
        ret = msgpack.unpackb(ret)
        print(repr(ret))

        s = [
            1,
            0,
            None,
            {
                b"get_valuesResponse": {
                    b"get_valuesResult": [
                        {b"KeyValuePair": {b"key": "a", b"value": "b"}},
                        {b"KeyValuePair": {b"key": "c", b"value": "d"}},
                    ]
                }
            },
        ]
        print(s)
        assert ret == s


if __name__ == "__main__":
    unittest.main()
