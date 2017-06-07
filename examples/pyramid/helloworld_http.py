#!/usr/bin/env python
# encoding: utf8
#
# Copyright   Burak Arslan <burak at arskom dot com dot tr>,
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

from pyramid.config import Configurator
from pyramid.view import view_config

from wsgiref.simple_server import make_server

from spyne.util.simple import pyramid_soap11_application
from spyne.decorator import rpc
from spyne.model.complex import Iterable
from spyne.model.primitive import Integer
from spyne.model.primitive import String
from spyne.service import Service

logging.basicConfig()
logging.basicConfig(level=logging.DEBUG)
logging.getLogger('spyne.protocol.xml').setLevel(logging.DEBUG)

tns = 'spyne.examples.pyramid.helloworld'

'''
>>> from suds.client import Client
>>> cli = Client("http://localhost:8000/?wsdl")
>>> cli
<suds.client.Client object at 0x104d5ed10>
>>> print cli

Suds ( https://fedorahosted.org/suds/ )  version: 0.4 GA  build: R699-20100913

Service ( HelloWorldService ) tns="spyne.helloworld"
   Prefixes (1)
      ns0 = "spyne.helloworld"
   Ports (1):
      (Application)
         Methods (1):
            say_hello(xs:string name, xs:integer times, )
         Types (3):
            say_hello
            say_helloResponse
            stringArray


>>> res = cli.service.say_hello('justin', 5)
>>> res
(stringArray){
   string[] = 
      "Hello, justin",
      "Hello, justin",
      "Hello, justin",
      "Hello, justin",
      "Hello, justin",
 }
'''

class HelloWorldService(Service):
    __namespace__ = tns
    
    @rpc(String, Integer, _returns=Iterable(String))
    def say_hello(ctx, name, times):
        '''
        Docstrings for service methods appear as documentation in the wsdl
        <b>what fun</b>
        @param name the name to say hello to
        @param the number of times to say hello
        @return the completed array
        '''

        for i in range(times):
            yield 'Hello, %s' % name

# view
soapApp = view_config(route_name="home")(
    pyramid_soap11_application([HelloWorldService], tns))

if __name__ == '__main__':
    # configuration settings
    settings = {}
    settings['debug_all'] = True
    # configuration setup
    config = Configurator(settings=settings)
    # routes setup
    config.add_route('home', '/')
    config.scan()
    # serve app
    app = config.make_wsgi_app()
    server = make_server('0.0.0.0', 8000, app)
    server.serve_forever()
