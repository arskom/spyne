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

'''
This is a simple HelloWorld example to show the basics of writing a webservice
using Spyne, starting a server, and creating a service client.

Here's how to call it using suds:

>>> from suds.client import Client
>>> c = Client('http://localhost:8000/?wsdl')
>>> c.service.say_hello('punk', 5)
(stringArray){
   string[] =
      "Hello, punk",
      "Hello, punk",
      "Hello, punk",
      "Hello, punk",
      "Hello, punk",
 }
>>>
'''


import logging

from spyne.application import Application
from spyne.decorator import srpc
from spyne.protocol.xml import XmlDocument
from spyne.protocol.http import HttpRpc
from spyne.service import ServiceBase
from spyne.model.complex import Iterable
from spyne.model.primitive import Integer
from spyne.model.primitive import String
from spyne.server.wsgi import WsgiApplication


class HelloWorldService(ServiceBase):
    @srpc(String, Integer, _returns=Iterable(String))
    def say_hello(name, times):
        '''
        Docstrings for service methods appear as documentation in the wsdl
        <b>what fun</b>
        @param name the name to say hello to
        @param the number of times to say hello
        @return the completed array
        '''

        for i in range(times):
            yield 'Hello, %s' % name

if __name__=='__main__':
    from wsgiref.simple_server import make_server

    logging.basicConfig(level=logging.DEBUG)

    application = Application([HelloWorldService], 'spyne.examples.hello.http',
                                in_protocol=HttpRpc(), out_protocol=XmlDocument())

    server = make_server('127.0.0.1', 8000, WsgiApplication(application))

    logging.info("listening to http://127.0.0.1:8000")
    logging.info("wsdl is at: http://localhost:8000/?wsdl")

    server.serve_forever()
