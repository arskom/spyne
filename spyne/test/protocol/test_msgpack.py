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

import msgpack
import unittest

from StringIO import StringIO

from spyne.application import Application
from spyne.decorator import rpc
from spyne.service import ServiceBase
from spyne.model.complex import Array
from spyne.model.primitive import String
from spyne.model.complex import ComplexModel
from spyne.model.primitive import Unicode
from spyne.protocol.msgpack import MessagePackDocument
from spyne.protocol.msgpack import MessagePackRpc
from spyne.server.wsgi import WsgiApplication
from spyne.server.wsgi import WsgiMethodContext
from spyne.test.protocol._test_dictobj import TDictDocumentTest

TestMessagePackDocument = TDictDocumentTest(msgpack, MessagePackDocument,
                                            "Client.MessagePackDecodeError")
from spyne.test.test_service import start_response

class TestMessagePackRpc(unittest.TestCase):
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
            out_protocol=MessagePackRpc(),
            name='Service', tns='tns'
        )
        server = WsgiApplication(application)

        input_string = msgpack.packb([0,0,"get_values", [["a","c"]] ])
        input_stream = StringIO(input_string)

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

        ret = ''.join(ret)
        print repr(ret)
        print msgpack.unpackb(ret)
        assert ret == msgpack.packb([1, 0, None, {'get_valuesResponse': {
            'get_valuesResult': {
                'KeyValuePair': [
                    {'value': 'b', 'key': 'a'},
                    {'value': 'd', 'key': 'c'}
                ]
            }}}
        ])

if __name__ == '__main__':
    unittest.main()
