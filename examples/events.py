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

from time import time

from rpclib.application import Application
from rpclib.decorator import srpc
from rpclib.interface.wsdl import Wsdl11
from rpclib.protocol.soap import Soap11
from rpclib.service import ServiceBase
from rpclib.model.complex import Array
from rpclib.model.primitive import String
from rpclib.model.primitive import Integer
from rpclib.server.wsgi import WsgiApplication

'''
This example is an enhanced version of the HelloWorld example that
uses event listeners to apply cross-cutting behavior to the service.
In this example, the service hooks are used to gather performance
information on both the method execution as well as the duration
of the entire call, including serialization and deserialization.

These method can be used to easily apply cross-cutting functionality
accross all methods in the service to do things like database transaction
management, logging and measuring performance. This example also
uses the user-defined context (udc) attribute of the MethodContext object
to hold the data points for this request.

You may notice that one construction of MethodContext instance is followed by
two destructions. This is because the fanout code creates shallow copies of
the context instance in an early stage of the method processing pipeline. As the
python's shallow-copying operator does not let us customize copy constructor,
it's not possible to cleanly log this event.
'''

class UserDefinedContext(object):
    def __init__(self):
        self.call_start = time()
        self.call_end = None
        self.method_start = None
        self.method_end = None

class HelloWorldService(ServiceBase):
    @srpc(String, Integer, _returns=Array(String))
    def say_hello(name, times):
        results = []

        for i in range(0, times):
            results.append('Hello, %s' % name)

        return results

def _on_wsgi_call(ctx):
    print("_on_wsgi_call")
    ctx.udc = UserDefinedContext()

def _on_method_call(ctx):
    print("_on_method_call")
    ctx.udc.method_start = time()

def _on_method_return_object(ctx):
    print("_on_method_return_object")
    ctx.udc.method_end = time()

def _on_wsgi_return(ctx):
    print("_on_wsgi_return")
    call_end = time()
    print('Method took [%0.8f] - total execution time[%0.8f]'% (
        ctx.udc.method_end - ctx.udc.method_start,
        call_end - ctx.udc.call_start))

def _on_method_context_destroyed(ctx):
    print("_on_method_context_destroyed")
    print('MethodContext(%d) lived for [%0.8f] seconds' % (id(ctx),
                                                ctx.call_end - ctx.call_start))
def _on_method_context_constructed(ctx):
    print("_on_method_context_constructed")
    print('Hello, this is MethodContext(%d). Time now: %0.8f' % (id(ctx),
                                                                ctx.call_start))

if __name__=='__main__':
    try:
        from wsgiref.simple_server import make_server
    except ImportError:
        print("Error: example server code requires Python >= 2.5")

    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('rpclib.protocol.xml').setLevel(logging.DEBUG)

    application = Application([HelloWorldService], 'rpclib.examples.events',
                interface=Wsdl11(), in_protocol=Soap11(), out_protocol=Soap11())

    application.event_manager.add_listener('method_call', _on_method_call)
    application.event_manager.add_listener('method_return_object',
                                                _on_method_return_object)
    application.event_manager.add_listener('method_context_constructed',
                                                _on_method_context_constructed)
    application.event_manager.add_listener('method_context_destroyed',
                                                _on_method_context_destroyed)

    wsgi_wrapper = WsgiApplication(application)
    wsgi_wrapper.event_manager.add_listener('wsgi_call', _on_wsgi_call)
    wsgi_wrapper.event_manager.add_listener('wsgi_return', _on_wsgi_return)

    server = make_server('127.0.0.1', 7789, wsgi_wrapper)

    print("listening to http://127.0.0.1:7789")
    print("wsdl is at: http://localhost:7789/?wsdl")

    server.serve_forever()
