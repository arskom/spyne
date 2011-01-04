#!/usr/bin/env python
#
# soaplib - Copyright (C) 2009 Aaron Bickell, Jamie Kirkpatrick
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

from soaplib.core.service import soap
from soaplib.core.model.primitive import String, Integer, Array
from soaplib.server.wsgi_soap import request
from soaplib.server.wsgi_soap import SimpleWSGIApp

'''
This example is an enhanced version of the HelloWorld example that
uses service 'hooks' to apply cross-cutting behavior to the service.
In this example, the service hooks are used to gather performance
information on both the method execution as well as the duration
of the entire call, including serialization and deserialization. The
available hooks are:

    * on_call
    * on_wsdl
    * on_wsdl_exception
    * on_method_exec
    * on_results
    * on_exception
    * on_return

These method can be used to easily apply cross-cutting functionality
accross all methods in the service to do things like database transaction
management, logging and measuring performance.  This example also
employs the threadlocal request (soaplib.wsgi_soap.request) object
to hold the data points for this request.
'''


class HelloWorldService(SimpleWSGIApp):

    @soap(String, Integer, _returns=Array(String))
    def say_hello(self, name, times):
        results = []
        raise Exception("this is some crazy crap")
        for i in range(0, times):
            results.append('Hello, %s' % name)
        return results

    def on_call(self, environ):
        request.additional['call_start'] = time()

    def on_method_exec(self, environ, body, py_params, soap_params):
        request.additional['method_start'] = time()

    def on_results(self, environ, py_results, soap_results, http_headers):
        request.additional['method_end'] = time()

    def on_return(self, environ, return_String):
        call_start = request.additional['call_start']
        call_end = time()
        method_start = request.additional['method_start']
        method_end = request.additional['method_end']

        print 'Method took [%s] - total execution time[%s]'% (
            method_end-method_start, call_end-call_start)


def make_client():
    from soaplib.client import make_service_client
    client = make_service_client('http://localhost:7889/', HelloWorldService())
    return client

if __name__=='__main__':
    try:
        from wsgiref.simple_server import make_server
        server = make_server('localhost', 7889, HelloWorldService())
        server.serve_forever()
    except ImportError:
        print "Error: example server code requires Python >= 2.5"
