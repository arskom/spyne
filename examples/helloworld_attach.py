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

from soaplib.service import rpc, DefinitionBase
from soaplib.model.primitive import String, Integer
from soaplib.model.binary import Attachment
from soaplib.model.clazz import Array
from soaplib.server.wsgi import Application


class HelloWorldService(DefinitionBase):
    @rpc(Attachment, Integer, _returns=Array(String), _mtom=True)
    def say_hello(self, name, times):
        results = []
        for i in range(0, times):
            results.append('Hello, %s' % name.data)
        return results

if __name__=='__main__':
    try:
        from wsgiref.simple_server import make_server
        server = make_server('localhost', 7789, Application([HelloWorldService], "tns"))
        server.serve_forever()
    except ImportError:
        print "Error: example server code requires Python >= 2.5"
