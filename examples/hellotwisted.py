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

from soaplib.util.wsgi_wrapper import run_twisted
from soaplib.server.wsgi import Application
from soaplib.service import DefinitionBase
from soaplib.service import rpc
from soaplib.type.clazz import Array
from soaplib.type.primitive import Integer
from soaplib.type.primitive import String

'''
This is the HelloWorld example running in the twisted framework.
'''

class HelloWorldService(DefinitionBase):
    @rpc(String, Integer, _returns=Array(String))
    def say_hello(self, name, times):
        '''Docstrings for service methods appear as documentation in the wsdl
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
    app=Application([HelloWorldService], 'tns')
    print 'listening on 0.0.0.0:7789'
    print 'wsdl is at: http://0.0.0.0:7789/SOAP/?wsdl'
    run_twisted( ( (app, "SOAP"),), 7789)
