#!/usr/bin/env python
#
# rpclib - Copyright (C) 2009 Aaron Bickell, Jamie Kirkpatrick
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301
#

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
'''

class UserDefinedContext(object):
    def __init__(self):
        self.call_start = None
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
    print "_on_wsgi_call"
    ctx.udc = UserDefinedContext()
    ctx.udc.call_start = time()

def _on_method_call(ctx):
    print "_on_method_call"
    ctx.udc.method_start = time()

def _on_method_return_object(ctx):
    print "_on_method_return_object"
    ctx.udc.method_end = time()

def _on_wsgi_return(ctx):
    print "_on_wsgi_return"
    call_end = time()
    print 'Method took [%s] - total execution time[%s]'% (
        ctx.udc.method_end - ctx.udc.method_start,
        call_end - ctx.udc.call_start)

if __name__=='__main__':
    try:
        from wsgiref.simple_server import make_server
    except ImportError:
        print "Error: example server code requires Python >= 2.5"

    application = Application([HelloWorldService], 'rpclib.examples.events',
                interface=Wsdl11(), in_protocol=Soap11(), out_protocol=Soap11())

    application.event_manager.add_listener('method_call', _on_method_call)
    application.event_manager.add_listener('method_return_object', _on_method_return_object)

    wsgi_wrapper = WsgiApplication(application)
    wsgi_wrapper.event_manager.add_listener('wsgi_call', _on_wsgi_call)
    wsgi_wrapper.event_manager.add_listener('wsgi_return', _on_wsgi_return)

    server = make_server('127.0.0.1', 7789, wsgi_wrapper)

    print "listening to http://127.0.0.1:7789"
    print "wsdl is at: http://localhost:7789/?wsdl"

    server.serve_forever()
