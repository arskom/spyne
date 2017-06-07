#!/usr/bin/env python
# encoding: utf8
#
# Copyright © Burak Arslan <burak at arskom dot com dot tr>,
#             Arskom Ltd. http://www.arskom.com.tr
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    1. Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#    2. Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#    3. Neither the name of the owner nor the names of its contributors may be
#       used to endorse or promote products derived from this software without
#       specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
# OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#


from spyne import Application, rpc, Service, Iterable, Integer, Unicode, \
    File
from spyne.protocol.http import HttpRpc
from spyne.protocol.json import JsonDocument
from spyne.protocol.xml import XmlDocument
from spyne.server.http import HttpTransportContext
from spyne.server.wsgi import WsgiApplication


def _say_hello(ctx, name, times, file_ext):
    if isinstance(ctx.transport, HttpTransportContext):
        file_name = "{}.{}".format(ctx.descriptor.name, file_ext)

        ctx.transport.add_header('Content-Disposition', 'attachment',
                                                             filename=file_name)

    for i in range(times):
        yield u'Hello, %s' % name


class SomeService(Service):
    @rpc(Unicode, Integer, _returns=Iterable(Unicode))
    def say_hello_as_xml_file(ctx, name, times):
        ctx.out_protocol = XmlDocument()

        # this is normally set automatically based on the out protocol
        # but you can set it just to be explicit
        if isinstance(ctx.transport, HttpTransportContext):
            ctx.transport.set_mime_type("application/xml")

        return _say_hello(ctx, name, times, 'xml')

    @rpc(Unicode, Integer, _returns=Iterable(Unicode))
    def say_hello_as_json_file(ctx, name, times):
        ctx.out_protocol = JsonDocument()

        # see how we don't set the mime type but it's still present in the
        # response headers

        return _say_hello(ctx, name, times ,'txt')

    @rpc(Unicode, Integer, _returns=Unicode)
    def say_hello_as_text_file(ctx, name, times):
        return '\n'.join(_say_hello(ctx, name, times ,'json'))

    @rpc(Unicode, Integer, _returns=File)
    def say_hello_as_binary_file(ctx, name, times):
        # WARNING!: the native value for data is an iterable of bytes, not just
        # bytes! If you forget this you may return data using 1-byte http chunks
        # which is incredibly inefficient.

        # WARNING!: don't forget to encode your data! This is the binary
        # output mode! You can't just write unicode data to socket!

        mime_type = HttpTransportContext.gen_header("text/plain",
                                                                 charset="utf8")

        return File.Value(type=mime_type,
            data=['\n'.join(s.encode('utf8') for s in
                                           _say_hello(ctx, name, times, 'txt'))]
        )


application = Application([SomeService], 'spyne.examples.response_as_file',
                          in_protocol=HttpRpc(validator='soft'),
                          out_protocol=HttpRpc())

wsgi_application = WsgiApplication(application)


if __name__ == '__main__':
    import logging

    from wsgiref.simple_server import make_server

    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('spyne.protocol.xml').setLevel(logging.DEBUG)

    logging.info("listening to http://127.0.0.1:8000")
    logging.info("wsdl is at: http://localhost:8000/?wsdl")

    server = make_server('127.0.0.1', 8000, wsgi_application)
    server.serve_forever()
