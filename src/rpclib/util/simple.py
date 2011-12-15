
#
# rpclib - Copyright (C) Rpclib contributors.
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

"""Contains functions that implement the most common protocol and transport
combinations"""

from rpclib.application import Application
from rpclib.interface.wsdl import Wsdl11
from rpclib.protocol.soap import Soap11
from rpclib.server.wsgi import WsgiApplication

def wsgi_soap11_application(services, tns='rpclib.simple.soap', validator=None):
    """Wraps `services` argument inside a WsgiApplication that uses Wsdl 1.1 as
    interface document and Soap 1.1 and both input and output protocols.
    """

    application = Application(services, tns, interface=Wsdl11(),
                in_protocol=Soap11(validator=validator), out_protocol=Soap11())

    return WsgiApplication(application)
