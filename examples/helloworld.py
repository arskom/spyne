#!/usr/bin/env python
# encoding: utf8
#
# rpclib - Copyright (C) 2009 Rpclib contributors
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

import logging

from rpclib.application import Application
from rpclib.decorator import srpc
from rpclib.interface.wsdl import Wsdl11
from rpclib.protocol.soap import Soap11
from rpclib.service import ServiceBase
from rpclib.model.complex import Iterable
from rpclib.model.primitive import Integer
from rpclib.model.primitive import String
from rpclib.server.wsgi import WsgiApplication

'''
This is a simple HelloWorld example to show the basics of writing
a webservice using rpclib, starting a server, and creating a service
client.

Here's how to call it using suds:

>>> from suds.client import Client
>>> c = Client('http://localhost:7789/?wsdl')
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

        for i in xrange(times):
            yield 'Hello, %s' % name

if __name__=='__main__':
    try:
        from wsgiref.simple_server import make_server
    except ImportError:
        print "Error: example server code requires Python >= 2.5"

    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('rpclib.protocol.soap._base').setLevel(logging.DEBUG)

    application = Application([HelloWorldService], 'rpclib.examples.hello.vanilla',
                interface=Wsdl11(), in_protocol=Soap11(), out_protocol=Soap11())

    server = make_server('127.0.0.1', 7789, WsgiApplication(application))

    print "listening to http://127.0.0.1:7789"
    print "wsdl is at: http://localhost:7789/?wsdl"

    server.serve_forever()
