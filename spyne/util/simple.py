
#
# spyne - Copyright (C) Spyne contributors.
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

from spyne.application import Application


def wsgi_soap11_application(services, tns='spyne.simple.soap', validator=None,
                                                                    name=None):
    """Wraps `services` argument inside a WsgiApplication that uses Wsdl 1.1 as
    interface document and Soap 1.1 and both input and output protocols.
    """

    from spyne.protocol.soap import Soap11
    from spyne.server.wsgi import WsgiApplication

    application = Application(services, tns, name=name,
                in_protocol=Soap11(validator=validator), out_protocol=Soap11())

    return WsgiApplication(application)

wsgi_soap_application = wsgi_soap11_application
"""DEPRECATED! Use :func:`wsgi_soap11_application` instead."""


def pyramid_soap11_application(services, tns='spyne.simple.soap', validator=None,
                                                                    name=None):
    """Wraps `services` argument inside a PyramidApplication that uses Wsdl 1.1 as
    interface document and Soap 1.1 and both input and output protocols.
    """

    from spyne.protocol.soap import Soap11
    from spyne.server.pyramid import PyramidApplication

    application = Application(services, tns, name=name,
                in_protocol=Soap11(validator=validator), out_protocol=Soap11())

    return PyramidApplication(application)
