#!/usr/bin/env python
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

from spyne.interface.wsdl.wsdl11 import Wsdl11
import logging
logging.basicConfig(level=logging.DEBUG)

import unittest

import spyne.const.xml_ns as ns

from spyne.test.interface.wsdl import AppTestWrapper
from spyne.test.interface.wsdl import build_app
from spyne.test.interface.wsdl.port_service_services import TBadRPCPortService
from spyne.test.interface.wsdl.port_service_services import TDoublePortService
from spyne.test.interface.wsdl.port_service_services import TMissingRPCPortService
from spyne.test.interface.wsdl.port_service_services import TMissingServicePortService
from spyne.test.interface.wsdl.port_service_services import TSinglePortService

class TestWSDLPortServiceBehavior(unittest.TestCase):
    def setUp(self):
        self.transport = 'http://schemas.xmlsoap.org/soap/http'
        self.url = 'http:/localhost:7789/wsdl'
        self.port_type_string = '{%s}portType' % ns.wsdl
        self.service_string = '{%s}service' % ns.wsdl
        self.binding_string = '{%s}binding' % ns.wsdl
        self.operation_string = '{%s}operation' % ns.wsdl
        self.port_string = '{%s}port' % ns.wsdl

    def test_tns(self):
        sa = build_app([TSinglePortService()], 'SinglePort', 'TestServiceName')

        wsdl = Wsdl11(sa.interface)
        wsdl.build_interface_document(self.url)
        sa_el = wsdl.root_elt
        tns = sa_el.get('targetNamespace')
        self.assertEqual('SinglePort', tns)

        sa = build_app(
            [TSinglePortService(), TDoublePortService()],
            'MultiServiceTns',
            'AppName'
        )

        wsdl = Wsdl11(sa.interface)
        wsdl.build_interface_document(self.url)
        tns = wsdl.root_elt.get('targetNamespace')

        self.assertEqual(tns, 'MultiServiceTns')

    def test_raise_missing_port(self):
        # Test that an exception is raised when a port is declared in the service class
        # but the rpc method does not declare a port.

        app = build_app(
            [TMissingRPCPortService()],
            'MisingPortTns',
            'MissingPortApp'
        )

        interface_doc = Wsdl11(app.interface)
        self.assertRaises(ValueError, interface_doc.build_interface_document,
                                                                       self.url)

        app = build_app(
            [TSinglePortService(), TMissingRPCPortService()],
            'MissingPort2Tns',
            'MissingPort2App'
        )

        interface_doc = Wsdl11(app.interface)
        self.assertRaises(ValueError, interface_doc.build_interface_document,
                                                                       self.url)


    def test_raise_invalid_port(self):

        app = build_app(
            [TBadRPCPortService()],
            'MisingPortTns',
            'MissingPortApp'
        )

        interface_doc = Wsdl11(app.interface)
        self.assertRaises(ValueError, interface_doc.build_interface_document,
                                                                       self.url)

        app = build_app(
            [TBadRPCPortService(), TSinglePortService()],
            'MissingPort2Tns',
            'MissingPortApp'
        )

        interface_doc = Wsdl11(app.interface)
        self.assertRaises(ValueError, interface_doc.build_interface_document,
                                                                       self.url)



    def test_raise_no_service_port(self):

        app = build_app(
            [TMissingServicePortService()],
            'MisingPortTns',
            'MissingPortApp'
        )

        interface_doc = Wsdl11(app.interface)
        self.assertRaises(ValueError, interface_doc.build_interface_document,
                                                                       self.url)

        app = build_app(
            [TSinglePortService(), TMissingServicePortService()],
            'MissingServicePort2Tns',
            'MissingServicePort2App'
        )

        interface_doc = Wsdl11(app.interface)
        self.assertRaises(ValueError, interface_doc.build_interface_document,
                                                                       self.url)


    def test_service_name(self):
        sa = build_app([TSinglePortService()], 'SinglePort', 'TestServiceName')
        wsdl = Wsdl11(sa.interface)
        wsdl.build_interface_document(self.url)
        sa_el = wsdl.root_elt

        sl = [s for s in sa_el.iterfind(self.service_string)]
        name = sl[0].get('name')
        print((len(sl)))

        self.assertEqual('SinglePortService_ServiceInterface', name)


    def test_service_contains_ports(self):
        # Check that the element for the service has the correct number of ports
        # Check that the element for the service has the correct port names

        app = build_app(
            [TSinglePortService()],
            'SinglePortTns',
            'SinglePortApp'
        )

        wrapper = AppTestWrapper(app)
        service = wrapper.get_service_list()[0]

        # verify that there is only one port
        ports = wrapper.get_port_list(service)
        self.assertEquals(1, len(ports))

        # verify that the ports name matched the port specified in
        # the service class
        port = ports[0]

        self.assertEquals('FirstPortType', port.get('name'))

    def test_port_name(self):
        sa = build_app([TSinglePortService()], 'tns', name='SinglePortApp')
        wsdl = Wsdl11(sa.interface)
        wsdl.build_interface_document(self.url)
        sa_wsdl_el = wsdl.root_elt

        pl = sa_wsdl_el.findall(self.port_type_string)
        print(('\n', pl, pl[0].attrib))
        self.assertEqual('FirstPortType', pl[0].get('name'))

        da = build_app([TDoublePortService()], 'tns', name='DoublePortApp')

        wsdl = Wsdl11(da.interface)
        wsdl.build_interface_document(self.url)
        da_wsdl_el = wsdl.root_elt

        pl2 = da_wsdl_el.findall(self.port_type_string)
        self.assertEqual('FirstPort', pl2[0].get('name'))
        self.assertEqual('SecondPort', pl2[1].get('name'))


    def test_port_count(self):
        sa = build_app([TSinglePortService()], 'tns', name='SinglePortApp')
        wsdl = Wsdl11(sa.interface)
        wsdl.build_interface_document(self.url)
        sa_wsdl_el = wsdl.root_elt

        self.assertEquals(1, len(sa_wsdl_el.findall(self.port_type_string)))
        pl = sa_wsdl_el.findall(self.port_type_string)
        self.assertEqual(1, len(pl))

        da = build_app([TDoublePortService()], 'tns', name='DoublePortApp')
        wsdl = Wsdl11(da.interface)
        wsdl.build_interface_document(self.url)

        from lxml import etree
        print etree.tostring(wsdl.root_elt, pretty_print=True)
        self.assertEquals(2, len(wsdl.root_elt.findall(self.port_type_string)))

if __name__ == '__main__':
    unittest.main()
