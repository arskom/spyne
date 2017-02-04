
#
# spyne - Copyright (C) spyne contributors.
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

from spyne.application import Application
from spyne.interface.wsdl import Wsdl11
from spyne.protocol.soap import Soap11
import spyne.const.xml as ns

def build_app(service_list, tns, name):
    app = Application(service_list, tns, name=name,
                      in_protocol=Soap11(), out_protocol=Soap11())
    app.transport = 'http://schemas.xmlsoap.org/soap/http'
    return app

class AppTestWrapper():
    def __init__(self, application):

        self.url = 'http:/localhost:7789/wsdl'
        self.service_string = ns.WSDL11('service')
        self.port_string = ns.WSDL11('port')
        self.soap_binding_string = ns.WSDL11_SOAP('binding')
        self.operation_string = ns.WSDL11('operation')
        self.port_type_string = ns.WSDL11('portType')
        self.binding_string = ns.WSDL11('binding')

        self.app = application
        self.interface_doc = Wsdl11(self.app.interface)
        self.interface_doc.build_interface_document(self.url)
        self.wsdl = self.interface_doc.get_interface_document()

    def get_service_list(self):
        return self.interface_doc.root_elt.findall(self.service_string)

    def get_port_list(self, service):
        from lxml import etree
        print((etree.tostring(service, pretty_print=True)))
        return service.findall(self.port_string)

    def get_soap_bindings(self, binding):
        return binding.findall(self.soap_binding_string)

    def get_port_types(self):
        return self.interface_doc.root_elt.findall(self.port_type_string)

    def get_port_operations(self, port_type):
        return port_type.findall(self.operation_string)

    def get_bindings(self):
        return self.interface_doc.root_elt.findall(self.binding_string)

    def get_binding_operations(self, binding):
        return [o for o in binding.iterfind(self.operation_string)]
