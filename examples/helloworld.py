#!/usr/bin/env python
# -*- coding: utf-8 -*-
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

import soaplib

from soaplib.service import rpc
from soaplib.service import DefinitionBase
from soaplib.model.primitive import String, Integer

from soaplib.server import wsgi
from soaplib.model.clazz import Array

'''
This is a simple HelloWorld example to show the basics of writing
a webservice using soaplib, starting a server, and creating a service
client.
'''

class HelloWorldService(DefinitionBase):
    @rpc(String, Integer, _returns=Array(String))
    def say_hello(self, name, times):
        '''
        Docstrings for service methods appear as documentation in the wsdl
        <b>what fun</b>
        @param name the name to say hello to
        @param the number of times to say hello
        @return the completed array
        '''
        results = []
        for i in range(0, times):
            results.append('Hello, %s' % name)
        return results

if __name__=='__main__':
    try:
        from wsgiref.simple_server import make_server
        soap_application = soaplib.Application([HelloWorldService], 'tns')
        wsgi_application = wsgi.Application(soap_application)

        print "listening to http://0.0.0.0:7789"
        print "wsdl is at: http://127.0.0.1:7789/?wsdl"

        server = make_server('localhost', 7789, wsgi_application)
        server.serve_forever()

    except ImportError:
        print "Error: example server code requires Python >= 2.5"
