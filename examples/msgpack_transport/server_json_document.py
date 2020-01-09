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
This is a simple HelloWorld example to show the basics of writing a
MessagePack-via-vanilla-TCP-sockets server using the JsonDocument protocol.
"""


import logging

from spyne import Application, rpc, Service, Iterable, UnsignedInteger, \
    Unicode

from spyne.protocol.json import JsonDocument
from spyne.server.twisted.msgpack import TwistedMessagePackProtocolFactory
from spyne.server.wsgi import WsgiApplication


HOST = '127.0.0.1'
PORT = 5551


class HelloWorldService(Service):
    @rpc(Unicode, UnsignedInteger, _returns=Iterable(Unicode))
    def say_hello(ctx, name, times):
        for i in range(times):
            yield u'Hello, %s' % name


if __name__=='__main__':
    from twisted.internet import reactor
    from twisted.python import log

    # logging boilerplate
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('spyne.protocol.xml').setLevel(logging.DEBUG)

    observer = log.PythonLoggingObserver('twisted')
    log.startLoggingWithObserver(observer.emit, setStdout=False)

    # set up application
    application = Application([HelloWorldService],
        'spyne.examples.hello.msgpack', in_protocol=JsonDocument(),
                                                    out_protocol=JsonDocument())

    # set up transport
    factory = TwistedMessagePackProtocolFactory(application)

    # set up listening endpoint
    reactor.listenTCP(PORT, factory, interface=HOST)

    # run the reactor
    reactor.run()
