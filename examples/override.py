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

from rpclib.application import Application
from rpclib.decorator import srpc
from rpclib.interface.wsdl import Wsdl11
from rpclib.protocol.soap import Soap11
from rpclib.service import ServiceBase
from rpclib.model.primitive import String
from rpclib.server.wsgi import WsgiApplication

'''
This example shows how to override the variable names for fun and profit.
This is very useful for situations that require the use of variable names
that are python keywords like, from, to, import, return, etc.
'''

class EmailManager(ServiceBase):
    @srpc(String, String, String, _returns=String,
        _in_variable_names = {'_to': 'to', '_from': 'from',
            '_message': 'message'},
        _out_variable_name = 'return')
    def send_email(_to, _from, message):
        # do email sending here
        return repr((_to, _from, message, 'sent!'))

if __name__=='__main__':
    try:
        from wsgiref.simple_server import make_server
    except ImportError:
        print "Error: example server code requires Python >= 2.5"

    application = Application([EmailManager], 'rpclib.examples.events',
                interface=Wsdl11(), in_protocol=Soap11(), out_protocol=Soap11())

    server = make_server('127.0.0.1', 7789, WsgiApplication(application))

    print "listening to http://127.0.0.1:7789"
    print "wsdl is at: http://localhost:7789/?wsdl"

    server.serve_forever()
