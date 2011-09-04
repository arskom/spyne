#!/usr/bin/env python
# encoding: utf8
#
# rpclib - Copyright (C) Rpclib contributors
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

from rpclib.application import Application
from rpclib.decorator import srpc
from rpclib.interface.wsdl import Wsdl11
from rpclib.protocol.soap import Soap11
from rpclib.service import ServiceBase
from rpclib.model.complex import Array
from rpclib.model.primitive import Integer
from rpclib.model.primitive import String
from rpclib.server.wsgi import WsgiApplication
from rpclib.util.wsgi_wrapper import run_twisted

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
    application = Application([HelloWorldService], 'rpclib.examples.hello.twisted',
                interface=Wsdl11(), in_protocol=Soap11(), out_protocol=Soap11())
    wsgi_app = WsgiApplication(application)

    print 'listening on 0.0.0.0:7789'
    print 'wsdl is at: http://0.0.0.0:7789/app/?wsdl'

    run_twisted( ( (wsgi_app, "app"),), 7789)
