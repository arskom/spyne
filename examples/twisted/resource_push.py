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

port = 8000
host = '127.0.0.1'

import logging
import sys

from twisted.internet import reactor
from twisted.internet.task import deferLater
from twisted.web.server import Site

from spyne.application import Application
from spyne.protocol.http import HttpRpc
from spyne.protocol.xml import XmlDocument
from spyne.server.twisted import TwistedWebResource

from spyne.decorator import rpc
from spyne.service import ServiceBase
from spyne.model.complex import Iterable
from spyne.model.primitive import Unicode


class HelloWorldService(ServiceBase):
    @rpc(Unicode, _returns=Iterable(Unicode))
    def say_hello_forever(ctx, name):
        def _cb(response):
            response.append(u'Hello, %s' % name)
            return deferLater(reactor, 0.1, _cb, response)

        return Iterable.Push(_cb)


if __name__=='__main__':
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('spyne.protocol.xml').setLevel(logging.DEBUG)

    logging.info("listening to http://127.0.0.1:8000")
    logging.info("wsdl is at: http://localhost:8000/?wsdl")

    application = Application([HelloWorldService],
            'spyne.examples.twisted.resource_push',
            in_protocol=HttpRpc(),
            out_protocol=XmlDocument(),
        )

    resource = TwistedWebResource(application)
    site = Site(resource)

    reactor.listenTCP(port, site, interface=host)

    logging.info("listening on: %s:%d" % (host,port))
    logging.info('wsdl is at: http://%s:%d/?wsdl' % (host, port))

    sys.exit(reactor.run())
