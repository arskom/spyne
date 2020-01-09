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
This is a simple HelloWorld example to show the basics of writing a Http api
using Spyne's push utilities.
"""


import logging

from spyne.application import Application
from spyne.decorator import rpc
from spyne.protocol.html import HtmlColumnTable
from spyne.protocol.http import HttpRpc
from spyne.service import Service
from spyne.model.complex import Iterable
from spyne.model.primitive import UnsignedInteger
from spyne.model.primitive import String
from spyne.server.wsgi import WsgiApplication


class HelloWorldService(Service):
    @rpc(String, UnsignedInteger, _returns=Iterable(String))
    def say_hello(ctx, name, times):
        def cb(ret):
            for i in range(times):
                ret.append('Hello, %s' % name)

        return Iterable.Push(cb)

if __name__=='__main__':
    from lxml.builder import E
    logging.basicConfig(level=logging.DEBUG)

    cloth = E.html(E.body(
        E.style("""
            td,th {
                border-left: 1px solid #ccc;
                border-right: 1px solid #ccc;
                border-bottom: 1px solid;
                margin: 0;
            }""", type="text/css"
        ),
        spyne="",
    ))

    application = Application([HelloWorldService], 'spyne.examples.hello.http',
        in_protocol=HttpRpc(validator='soft'),
        out_protocol=HtmlColumnTable(cloth=cloth),
    )

    wsgi_application = WsgiApplication(application)

    from wsgiref.simple_server import make_server
    server = make_server('127.0.0.1', 8000, wsgi_application)

    logging.info("listening to http://127.0.0.1:8000")
    logging.info("wsdl is at: http://localhost:8000/?wsdl")

    server.serve_forever()
