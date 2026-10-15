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
    from twisted.web.server import Request, Site
    from twisted.web.test.requesthelper import DummyChannel
except ImportError:
    Site = None

try:
    import werkzeug
except ImportError:
    werkzeug = None

from spyne import Application, Service, rpc
from spyne.model.binary import File
from spyne.model.primitive import Unicode
from spyne.protocol.http import HttpRpc
from spyne.protocol.json import HybridHttpJsonDocument
from spyne.protocol.soap import Soap11


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


@unittest.skipIf(Site is None or werkzeug is None,
                                                "needs twisted and werkzeug")
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



class EchoService(Service):
    @rpc(Unicode, _returns=Unicode)
    def echo(ctx, s):
        ctx.app.received.append(s)
        return s


def _request(app, method, path, body=b'', headers=()):
    from spyne.server.twisted import TwistedWebResource

    channel = DummyChannel()
    channel.site = Site(TwistedWebResource(app))
    request = Request(channel)
    request.content = BytesIO(body)
    for k, v in headers:
        request.requestHeaders.setRawHeaders(k, [v])
    request.requestHeaders.setRawHeaders(b'content-length',
                                                [str(len(body)).encode()])
    request.requestReceived(method, path, b'HTTP/1.1')
    return request, channel.transport.written.getvalue()


@unittest.skipIf(Site is None, "needs twisted")
class TestTwistedHttpBytes(unittest.TestCase):
    """Twisted gives the request method, uri and headers as bytes."""

    def _app(self, in_protocol, out_protocol):
        app = Application([EchoService], 'tns', in_protocol=in_protocol,
                                                    out_protocol=out_protocol)
        app.received = []
        return app

    def test_wsdl(self):
        app = self._app(Soap11(), Soap11())
        request, out = _request(app, b'GET', b'/?wsdl')

        self.assertEqual(request.code, 200)
        self.assertIn(b'location="http://', out)

    def test_wsdl_behind_proxy(self):
        app = self._app(Soap11(), Soap11())
        request, out = _request(app, b'GET', b'/?wsdl', headers=[
            (b'x-forwarded-host', b'proxy.example.com'),
            (b'x-forwarded-proto', b'https'),
            (b'x-forwarded-port', b'443'),
        ])

        self.assertEqual(request.code, 200)
        self.assertIn(b'location="https://proxy.example.com/"', out)

    def test_soap_post(self):
        app = self._app(Soap11(), Soap11())
        body = (
            b'<soapenv:Envelope '
            b'xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" '
            b'xmlns:tns="tns"><soapenv:Body>'
            b'<tns:echo><tns:s>hello</tns:s></tns:echo>'
            b'</soapenv:Body></soapenv:Envelope>'
        )
        request, _ = _request(app, b'POST', b'/', body,
                         [(b'content-type', b'text/xml; charset=utf-8')])

        self.assertEqual(request.code, 200)
        self.assertEqual(app.received, [u'hello'])

    def test_hybrid_http_json_post(self):
        app = self._app(HybridHttpJsonDocument(), HttpRpc())
        request, _ = _request(app, b'POST', b'/echo', b'{"s": "hello"}',
                                    [(b'content-type', b'application/json')])

        self.assertEqual(request.code, 200)
        self.assertEqual(app.received, [u'hello'])
