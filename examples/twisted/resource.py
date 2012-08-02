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

import logging
import time
import sys

from twisted.python import log
from twisted.web.server import Site
from twisted.web.static import File
from twisted.internet import reactor
from twisted.python import log

from spyne.application import Application
from spyne.decorator import srpc
from spyne.protocol.http import HttpRpc
from spyne.protocol.json import JsonObject
from spyne.protocol.xml import XmlObject
from spyne.service import ServiceBase
from spyne.model.complex import Array
from spyne.model.primitive import Integer
from spyne.model.primitive import String
from spyne.server.wsgi import WsgiApplication
from spyne.server.twisted import TwistedWebResource
from spyne.util.wsgi_wrapper import run_twisted

from _service import SomeService

'''
This is a blocking example running in a single-process twisted setup.

In this example, user code runs directly in the reactor loop. So unless your
code fully adheres to the asynchronous programming principles, you can block
the reactor loop.

    $ time curl -s "http://localhost:9752/block?seconds=10" > /dev/null & time curl -s "http://localhost:9752/block?seconds=10" > /dev/null& 
    [1] 27559
    [2] 27560

    real    0m10.026s
    user    0m0.005s
    sys     0m0.008s

    real    0m20.045s
    user    0m0.009s
    sys     0m0.005s

'''

host = '127.0.0.1'
port = 9752

if __name__=='__main__':
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('spyne.protocol.xml').setLevel(logging.DEBUG)

    application = Application([SomeService], 'spyne.examples.hello.twisted',
                              in_protocol=HttpRpc(), out_protocol=XmlObject())

    application.interface.nsmap[None] = application.interface.nsmap['tns']
    application.interface.prefmap[application.interface.nsmap['tns']] = None
    del application.interface.nsmap['tns']

    observer = log.PythonLoggingObserver('twisted')
    log.startLoggingWithObserver(observer.emit, setStdout=False)

    wr = TwistedWebResource(application)
    site = Site(wr)

    reactor.listenTCP(port, site)

    logging.info("listening on: %s:%d" % (host,port))
    logging.info('wsdl is at: http://0.0.0.0:7789/?wsdl')

    sys.exit(reactor.run())
