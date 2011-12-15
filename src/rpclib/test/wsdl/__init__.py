
#
# rpclib - Copyright (C) rpclib contributors.
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
from rpclib.interface.wsdl import Wsdl11
from rpclib.protocol.soap import Soap11
import rpclib.const.xml_ns as ns

def build_app(service_list, tns, name):
    app = Application(service_list, tns, Wsdl11(), 
                      Soap11(), Soap11(), name=name)
    app.transport = 'http://schemas.xmlsoap.org/soap/http'
    return app

class AppTestWrapper():
    def __init__(self, application):

        self.url = 'http:/localhost:7789/wsdl'
        self.service_string = '{%s}service' % ns.wsdl
        self.port_string = '{%s}port' % ns.wsdl
        self.soap_binding_string = '{%s}binding' % ns.soap
        self.operation_string = '{%s}operation' % ns.wsdl
        self.port_type_string = '{%s}portType' % ns.wsdl
        self.binding_string = '{%s}binding' % ns.wsdl

        self.app = application
        self.app.interface.build_interface_document(self.url)
        self.wsdl = self.app.interface.get_interface_document()

    def get_service_list(self):
        return self.app.interface.root_elt.findall(self.service_string)

    def get_port_list(self, service):
        from lxml import etree
        print((etree.tostring(service, pretty_print=True)))
        return service.findall(self.port_string)

    def get_soap_bindings(self, binding):
        return binding.findall(self.soap_binding_string)

    def get_port_types(self):
        return self.app.interface.root_elt.findall(self.port_type_string)

    def get_port_operations(self, port_type):
        return port_type.findall(self.operation_string)

    def get_bindings(self):
        return self.app.interface.root_elt.findall(self.binding_string)

    def get_binding_operations(self, binding):
        return [o for o in binding.iterfind(self.operation_string)]
