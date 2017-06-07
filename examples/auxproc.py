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

import sys
import time
import logging

from wsgiref.simple_server import make_server

from spyne import Application, rpc, Integer, Service
from spyne.protocol.http import HttpRpc

from spyne.protocol.xml import XmlDocument
from spyne.server.wsgi import WsgiApplication

# Requires Python >=2.7
from spyne.auxproc.thread import ThreadAuxProc
from spyne.auxproc.sync import SyncAuxProc


host = '127.0.0.1'
port = 9753


class SomeService(Service):
    @rpc(Integer)
    def block(ctx, seconds):
        """Blocks the reactor for given number of seconds."""
        logging.info("Primary sleeping for %d seconds." % seconds)
        time.sleep(seconds)


class SomeAuxService(Service):
    __aux__ = ThreadAuxProc() # change this to SyncAuxProc to see the difference

    @rpc(Integer)
    def block(ctx, seconds):
        """Blocks the reactor for given number of seconds."""
        logging.info("Auxiliary sleeping for %d seconds." % (seconds * 2))
        time.sleep(seconds * 2)


def main():
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('spyne.protocol.xml').setLevel(logging.DEBUG)

    services = (SomeService, SomeAuxService)
    application = Application(services, 'spyne.examples.auxproc',
                              in_protocol=HttpRpc(), out_protocol=XmlDocument())

    server = make_server(host, port, WsgiApplication(application))

    logging.info("listening to http://%s:%d" % (host, port))

    return server.serve_forever()


if __name__ == '__main__':
    sys.exit(main())
