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
This is a blocking example running in a multi-threaded twisted setup.

This is a way of weakly integrating with the twisted framework -- every request
still runs in its own thread. This way, you can still use other features of
twisted and not have to rewrite your otherwise synchronous code.

    $ time curl -s "http://localhost:9757/block?seconds=10" > /dev/null & \
      time curl -s "http://localhost:9757/block?seconds=10" > /dev/null &
    [1] 27537
    [2] 27538

    real    0m10.031s
    user    0m0.008s
    sys     0m0.007s

    real    0m10.038s
    user    0m0.006s
    sys     0m0.006s
"""

import sys
import time
import logging

from twisted.internet import reactor
from twisted.web.server import Site
from twisted.web.wsgi import WSGIResource
from twisted.python import log

from spyne import Application, rpc, Service, Integer
from spyne.server.wsgi import WsgiApplication
from spyne.protocol.http import HttpRpc


HOST = '0.0.0.0'
PORT = 9757


class SomeService(Service):
    @rpc(Integer, _returns=Integer)
    def block(ctx, seconds):
        """Blocks the current thread for given number of seconds."""
        time.sleep(seconds)
        return seconds


def initialize(services, tns='spyne.examples.twisted.resource'):
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('spyne.protocol.xml').setLevel(logging.DEBUG)

    observer = log.PythonLoggingObserver('twisted')
    log.startLoggingWithObserver(observer.emit, setStdout=False)

    application = Application(services, 'spyne.examples.twisted.hello',
                                in_protocol=HttpRpc(), out_protocol=HttpRpc())

    return application


if __name__ == '__main__':
    application = initialize([SomeService])
    wsgi_application = WsgiApplication(application)
    resource = WSGIResource(reactor, reactor, wsgi_application)
    site = Site(resource)

    reactor.listenTCP(PORT, site, interface=HOST)

    logging.info('listening on: %s:%d' % (HOST,PORT))
    logging.info('wsdl is at: http://%s:%d/?wsdl' % (HOST, PORT))

    sys.exit(reactor.run())
