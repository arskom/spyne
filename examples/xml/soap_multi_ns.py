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


"""
This is a simple example that illustrates how to have immediate children of a
complexType in a different namespace.
"""

from spyne import Unicode, Iterable, XmlAttribute, ComplexModel, Service, \
    Application, rpc
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication


NS_B = "www.example.com/schema/b"


class Baz(ComplexModel):
    __namespace__ = NS_B

    Thing = Unicode
    AttrC = XmlAttribute(Unicode)


class FooCustomRequest(ComplexModel):
    AttrA = XmlAttribute(Unicode)
    AttrB = XmlAttribute(Unicode)
    Bar = Baz.customize(sub_ns=NS_B)
    Baz = Unicode


class FooService(Service):
    @rpc(FooCustomRequest, _returns = Iterable(Unicode), _body_style='bare')
    def Foo(ctx, req):
        AttrA, AttrB, Baz, Bar = req.AttrA, req.AttrB, req.Baz, req.Bar
        yield 'Hello, %s' % Bar


application = Application([FooService],
    tns="www.example.com/schema/a",
    in_protocol=Soap11(validator='soft'),
    out_protocol=Soap11(),
)


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
