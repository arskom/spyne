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
using Spyne. Here's a sample:

$ curl http://localhost:8000/say_hello?name=Dave\&times=3
["Hello, Dave", "Hello, Dave", "Hello, Dave"]
"""


import logging

from spyne import Application, rpc, ServiceBase, Iterable, UnsignedInteger, \
    String

from spyne.protocol.json import JsonDocument
from spyne.protocol.http import HttpRpc
from spyne.server.wsgi import WsgiApplication


class HelloWorldService(ServiceBase):
    @rpc(String, UnsignedInteger, _returns=Iterable(String))
    def say_hello(ctx, name, times):
        """
        Docstrings for service methods do appear as documentation in the
        interface documents. <b>What fun!</b>

        :param name: The name to say hello to
        :param times: The number of times to say hello

        :returns: An array of 'Hello, <name>' strings, repeated <times> times.
        """

        for i in range(times):
            yield 'Hello, %s' % name


if __name__ == '__main__':
    # Python daemon boilerplate
    from wsgiref.simple_server import make_server

    logging.basicConfig(level=logging.DEBUG)

    # Instantiate the application by giving it:
    #   * The list of services it should wrap,
    #   * A namespace string.
    #   * An input protocol.
    #   * An output protocol.
    application = Application([HelloWorldService], 'spyne.examples.hello.http',
        # The input protocol is set as HttpRpc to make our service easy to
        # call. Input validation via the 'soft' engine is enabled. (which is
        # actually the the only validation method for HttpRpc.)
        in_protocol=HttpRpc(validator='soft'),

        # The ignore_wrappers parameter to JsonDocument simplifies the reponse
        # dict by skipping outer response structures that are redundant when
        # the client knows what object to expect.
        out_protocol=JsonDocument(ignore_wrappers=True),
    )

    # Now that we have our application, we must wrap it inside a transport.
    # In this case, we use Spyne's standard Wsgi wrapper. Spyne supports
    # popular Http wrappers like Twisted, Django, Pyramid, etc. as well as
    # a ZeroMQ (REQ/REP) wrapper.
    wsgi_application = WsgiApplication(application)

    # More daemon boilerplate
    server = make_server('127.0.0.1', 8000, wsgi_application)

    logging.info("listening to http://127.0.0.1:8000")
    logging.info("wsdl is at: http://localhost:8000/?wsdl")

    server.serve_forever()
