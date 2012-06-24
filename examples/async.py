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

#
# FIXME: This example is not working. It's here just so we don't forget about
# it. Please ignore this.
#

import time
from threading import Thread

from spyne.application import Application
from spyne.decorator import rpc
from spyne.decorator import srpc
from spyne.interface.wsdl import Wsdl11
from spyne.protocol.soap import Soap11
from spyne.service import ServiceBase
from spyne.model.primitive import String
from spyne.model.primitive import Integer
from spyne.util import get_callback_info
from spyne.server.wsgi import WsgiApplication

'''
This is a very simple async service that sleeps for a specified
number of seconds and then call back the caller with a message.
This kicks off a new Thread for each request, which is not recommended
for a real-world application.  Spyne does not provide any thread
management or scheduling mechanism, the service is responsible for the
execution of the async process.
'''

class SleepingService(ServiceBase):
    @rpc(Integer, _is_async=True)
    def sleep(self, seconds):
        msgid, replyto = get_callback_info()

        def run():
            time.sleep(seconds)

            client = make_service_client(replyto, self)
            client.woke_up('good morning', msgid=msgid)

        Thread(target=run).start()

    @srpc(String, _is_callback=True)
    def woke_up(message):
        pass

if __name__=='__main__':
    try:
        from wsgiref.simple_server import make_server
    except ImportError:
        print("Error: example server code requires Python >= 2.5")

    application = Application([SleepingService], 'spyne.examples.async',
                interface=Wsdl11(), in_protocol=Soap11(), out_protocol=Soap11())

    server = make_server('127.0.0.1', 7789, WsgiApplication(application))

    print("listening to http://127.0.0.1:7789")
    print("wsdl is at: http://localhost:7789/?wsdl")

    server.serve_forever()
