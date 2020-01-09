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

from __future__ import print_function


"""This shows the async push capabilities of Spyne using twisted in async mode.

In this example, user code runs directly in the reactor loop. Data is pushed to
the output slowly without blocking other requests.
"""


import logging
import sys

from twisted.internet import reactor
from twisted.internet.task import deferLater
from twisted.web.server import Site

from spyne import Application, rpc, Service, Iterable, Unicode, \
    UnsignedInteger
from spyne.protocol.http import HttpRpc
from spyne.protocol.html import HtmlColumnTable
from spyne.server.twisted import TwistedWebResource


HOST = '127.0.0.1'
PORT = 8000


class HelloWorldService(Service):
    @rpc(Unicode(default='World'), UnsignedInteger(default=5),
                                                    _returns=Iterable(Unicode))
    def say_hello(ctx, name, times):
        # workaround for Python2's lacking of nonlocal
        times = [times]

        def _cb(push):
            # This callback is called immediately after the function returns.

            if times[0] > 0:
                times[0] -= 1

                data = u'Hello, %s' % name
                print(data)

                # The object passed to the append() method is immediately
                # serialized to bytes and pushed to the response stream's
                # file-like object.
                push.append(data)

                # When a push-callback returns anything other than a deferred,
                # the response gets closed.
                return deferLater(reactor, 1, _cb, push)

        # This is Spyne's way of returning NOT_DONE_YET
        return Iterable.Push(_cb)

    @rpc(Unicode(default='World'), _returns=Iterable(Unicode))
    def say_hello_forever(ctx, name):
        def _cb(push):
            push.append(u'Hello, %s' % name)
            return deferLater(reactor, 0.1, _cb, push)

        return Iterable.Push(_cb)


if __name__=='__main__':
    application = Application([HelloWorldService],
            'spyne.examples.twisted.resource_push',
            in_protocol=HttpRpc(),
            out_protocol=HtmlColumnTable(),
        )

    resource = TwistedWebResource(application)
    site = Site(resource)

    reactor.listenTCP(PORT, site, interface=HOST)

    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('spyne.protocol.xml').setLevel(logging.DEBUG)
    logging.info("listening on: %s:%d" % (HOST,PORT))
    logging.info('wsdl is at: http://%s:%d/?wsdl' % (HOST, PORT))

    sys.exit(reactor.run())
