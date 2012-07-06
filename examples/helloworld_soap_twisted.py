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

from spyne.application import Application
from spyne.decorator import srpc
from spyne.interface.wsdl import Wsdl11
from spyne.protocol.soap import Soap11
from spyne.service import ServiceBase
from spyne.model.complex import Array
from spyne.model.primitive import Integer
from spyne.model.primitive import String
from spyne.server.wsgi import WsgiApplication
from spyne.util.wsgi_wrapper import run_twisted

'''
This is the HelloWorld example running in the twisted framework.
'''


class HelloWorldService(ServiceBase):
    @srpc(String, Integer, _returns=Array(String))
    def say_hello(name, times):
        '''Docstrings for service methods appear as documentation in the wsdl.

        @param name the name to say hello to
        @param the number of times to say hello
        @return the completed array
        '''
        results = []
        for i in range(0, times):
            results.append('Hello, %s' % name)

        return results

if __name__=='__main__':
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('spyne.protocol.xml').setLevel(logging.DEBUG)

    application = Application([HelloWorldService], 'spyne.examples.hello.twisted',
                interface=Wsdl11(), in_protocol=Soap11(), out_protocol=Soap11())

    application.interface.nsmap[None] = application.interface.nsmap['tns']
    application.interface.prefmap[application.interface.nsmap['tns']] = None
    del application.interface.nsmap['tns']

    wsgi_app = WsgiApplication(application)

    logging.info('listening on 0.0.0.0:7789')
    logging.info('wsdl is at: http://0.0.0.0:7789/app/?wsdl')

    run_twisted(((wsgi_app, "app"),), 7789)
