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


'''This is a blocking example running in a single-process twisted setup.

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
'''


import logging
import sys

from twisted.internet import reactor
from twisted.web.server import Site
from twisted.internet.task import deferLater

from spyne.server.twisted import TwistedWebResource
from spyne.decorator import srpc
from spyne.service import ServiceBase

from _service import initialize
from _service import SomeService

host = '0.0.0.0'
port = 9758


class SomeNonBlockingService(ServiceBase):
    @srpc(int, _returns=str)
    def sleep(seconds):
        """Waits without blocking reactor for given number of seconds by
        returning a deferred."""

        def _cb():
            return "slept for %r seconds" % seconds

        return deferLater(reactor, seconds, _cb)


if __name__=='__main__':
    application = initialize([SomeService, SomeNonBlockingService])
    resource = TwistedWebResource(application)
    site = Site(resource)

    reactor.listenTCP(port, site, interface=host)

    logging.info("listening on: %s:%d" % (host,port))
    logging.info('wsdl is at: http://%s:%d/?wsdl' % (host, port))

    sys.exit(reactor.run())
