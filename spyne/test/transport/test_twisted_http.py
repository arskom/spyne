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

from io import BytesIO

try:
    import werkzeug
    from twisted.web.server import Request, Site
    from twisted.web.test.requesthelper import DummyChannel
except ImportError:
    werkzeug = None

from spyne import Application, Service, rpc
from spyne.model.binary import File
from spyne.model.primitive import Unicode
from spyne.protocol.http import HttpRpc


def _multipart(boundary, file_data):
    return (
        b'--' + boundary + b'\r\n'
        b'Content-Disposition: form-data; name="s"\r\n'
        b'\r\n'
        b'hello\r\n'
        b'--' + boundary + b'\r\n'
        b'Content-Disposition: form-data; name="f"; filename="a.txt"\r\n'
        b'Content-Type: text/plain\r\n'
        b'\r\n' + file_data + b'\r\n'
        b'--' + boundary + b'--\r\n'
    )


@unittest.skipIf(werkzeug is None, "needs twisted and werkzeug")
class TestTwistedHttpFileUpload(unittest.TestCase):
    def _post(self, body, content_type):
        from spyne.server.twisted import TwistedWebResource

        received = []

        class SomeService(Service):
            @rpc(File, Unicode)
            def upload(ctx, f, s):
                received.append((f, s))

        app = Application([SomeService], 'tns',
                                in_protocol=HttpRpc(), out_protocol=HttpRpc())

        channel = DummyChannel()
        channel.site = Site(TwistedWebResource(app))
        request = Request(channel)
        request.content = BytesIO(body)
        request.content.seek(0, 2)  # where twisted leaves it
        request.requestHeaders.setRawHeaders(b'content-type', [content_type])
        request.requestHeaders.setRawHeaders(b'content-length',
                                                    [str(len(body)).encode()])
        request.requestReceived(b'POST', b'/upload', b'HTTP/1.1')

        self.assertEqual(len(received), 1)
        return received[0]

    def test_multipart_file(self):
        body = _multipart(b'BOUNDARY', b'file data')
        f, s = self._post(body, b'multipart/form-data; boundary=BOUNDARY')

        self.assertEqual(s, u'hello')
        self.assertEqual(f.name, 'a.txt')
        self.assertEqual(f.type, 'text/plain')
        self.assertEqual(b''.join(f.data), b'file data')

    def test_multipart_large_file(self):
        # big enough to be spooled to a temporary file
        data = b'x' * (1024 * 1024)
        body = _multipart(b'BOUNDARY', data)
        f, s = self._post(body, b'multipart/form-data; boundary=BOUNDARY')

        self.assertEqual(f.name, 'a.txt')
        self.assertEqual(b''.join(bytes(d) for d in f.data), data)

