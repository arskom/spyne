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


"""This is a blocking example running in a single-process twisted setup.

In this example, user code runs directly in the reactor loop. So unless your
code fully adheres to the asynchronous programming principles, you can block
the reactor loop. ::

    $ time curl -s "http://localhost:9757/block?seconds=10" > /dev/null & \
      time curl -s "http://localhost:9757/block?seconds=10" > /dev/null &
    [1] 27559
    [2] 27560

    real    0m10.026s
    user    0m0.005s
    sys     0m0.008s

    real    0m20.045s
    user    0m0.009s
    sys     0m0.005s

If you call sleep, it sleeps by returning a deferred: ::

    $ time curl -s "http://localhost:9757/sleep?seconds=10" > /dev/null & \
      time curl -s "http://localhost:9757/sleep?seconds=10" > /dev/null &
    [1] 27778
    [2] 27779

    real    0m10.012s
    user    0m0.000s
    sys     0m0.000s

    real    0m10.013s
    user    0m0.000s
    sys     0m0.000s
"""

import sys
import time
import logging

from twisted.internet import reactor
from twisted.web.server import Site
from twisted.internet.task import deferLater
from twisted.python import log

from spyne import Unicode, Integer, Double, ByteArray, Iterable, rpc, \
    Service, Application
from spyne.server.twisted import TwistedWebResource
from spyne.protocol.http import HttpRpc

HOST = '0.0.0.0'
PORT = 9758


class SomeService(Service):
    @rpc(Integer, _returns=Integer)
    def block(ctx, seconds):
        """Blocks the current thread for given number of seconds."""
        time.sleep(seconds)
        return seconds


class SomeNonBlockingService(Service):
    @rpc(Integer, _returns=Unicode)
    def sleep(ctx, seconds):
        """Waits without blocking reactor for given number of seconds by
        returning a deferred."""

        def _cb():
            return "slept for %r seconds" % seconds

        return deferLater(reactor, seconds, _cb)

    @rpc(Unicode, Double, Double, _returns=ByteArray)
    def say_hello_with_sleep(ctx, name, times, seconds):
        """Sends multiple hello messages by waiting given number of seconds
        inbetween."""

        times = [times]  # Workaround for Python 2's lacking of nonlocal

        def _cb(response):
            if times[0] > 0:
                msg = u"Hello %s, sleeping for %f seconds for " \
                                 u"%d more time(s)." % (name, seconds, times[0])

                response.append(msg.encode('utf8'))
                response.append(b'\n')

                logging.debug(msg)

                times[0] -= 1
                return deferLater(reactor, seconds, _cb, response)

        return Iterable.Push(_cb)


def initialize(services, tns='spyne.examples.twisted.resource'):
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('spyne.protocol.xml').setLevel(logging.DEBUG)

    observer = log.PythonLoggingObserver('twisted')
    log.startLoggingWithObserver(observer.emit, setStdout=False)

    return Application(services, 'spyne.examples.twisted.hello',
                                in_protocol=HttpRpc(), out_protocol=HttpRpc())


if __name__=='__main__':
    application = initialize([SomeService, SomeNonBlockingService])
    resource = TwistedWebResource(application)
    site = Site(resource)

    reactor.listenTCP(PORT, site, interface=HOST)

    logging.info("listening on: %s:%d" % (HOST,PORT))
    logging.info('wsdl is at: http://%s:%d/?wsdl' % (HOST, PORT))

    sys.exit(reactor.run())
