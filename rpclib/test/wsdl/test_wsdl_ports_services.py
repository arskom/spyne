#!/usr/bin/env python
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

import logging
logging.basicConfig(level=logging.DEBUG)

import unittest

import rpclib.const.xml_ns as ns

from rpclib.test.wsdl import AppTestWrapper
from rpclib.test.wsdl import build_app
from rpclib.test.wsdl.port_service_services import BadRPCPortService
from rpclib.test.wsdl.port_service_services import DoublePortService
from rpclib.test.wsdl.port_service_services import MissingRPCPortService
from rpclib.test.wsdl.port_service_services import MissingServicePortService
from rpclib.test.wsdl.port_service_services import SinglePortService

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
        sa = build_app([SinglePortService], 'SinglePort', 'TestServiceName')

        sa.interface.build_interface_document(self.url)
        sa_el = sa.interface.root_elt
        tns = sa_el.get('targetNamespace')
        self.assertEqual('SinglePort', tns)

        sa = build_app(
            [SinglePortService, DoublePortService],
            'MultiServiceTns',
            'AppName'
        )

        sa.interface.build_interface_document(self.url)
        tns = sa.interface.root_elt.get('targetNamespace')

        self.assertEqual(tns, 'MultiServiceTns')

    def test_raise_missing_port(self):
        # Test that an exception is raised when a port is declared in the service class
        # but the rpc method does not declare a port.

        app = build_app(
            [MissingRPCPortService],
            'MisingPortTns',
            'MissingPortApp'
        )

        self.assertRaises(ValueError, app.interface.build_interface_document,
                                                                       self.url)

        app = build_app(
            [SinglePortService, MissingRPCPortService],
            'MissingPort2Tns',
            'MissingPort2App'
        )

        self.assertRaises(ValueError, app.interface.build_interface_document,
                                                                       self.url)


    def test_raise_invalid_port(self):

        app = build_app(
            [BadRPCPortService],
            'MisingPortTns',
            'MissingPortApp'
        )

        self.assertRaises(ValueError, app.interface.build_interface_document,
                                                                       self.url)

        app = build_app(
            [BadRPCPortService, SinglePortService],
            'MissingPort2Tns',
            'MissingPortApp'
        )

        self.assertRaises(ValueError, app.interface.build_interface_document,
                                                                       self.url)



    def test_raise_no_service_port(self):

        app = build_app(
            [MissingServicePortService],
            'MisingPortTns',
            'MissingPortApp'
        )

        self.assertRaises(ValueError, app.interface.build_interface_document,
                                                                       self.url)

        app = build_app(
            [SinglePortService, MissingServicePortService],
            'MissingServicePort2Tns',
            'MissingServicePort2App'
        )

        self.assertRaises(ValueError, app.interface.build_interface_document,
                                                                       self.url)


    def test_service_name(self):
        sa = build_app([SinglePortService], 'SinglePort', 'TestServiceName')
        sa.interface.build_interface_document(self.url)
        sa_el = sa.interface.root_elt

        sl = [s for s in sa_el.iterfind(self.service_string)]
        name = sl[0].get('name')
        print((len(sl)))

        self.assertEqual('SinglePortService_ServiceInterface', name)


    def test_service_contains_ports(self):
        # Check that the element for the service has the correct number of ports
        # Check that the element for the service has the correct port names

        app = build_app(
            [SinglePortService],
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
        sa = build_app([SinglePortService], 'tns', name='SinglePortApp')
        sa.interface.build_interface_document(self.url)
        sa_wsdl_el = sa.interface.root_elt

        pl = sa_wsdl_el.findall(self.port_type_string)
        print(('\n', pl, pl[0].attrib))
        self.assertEqual('FirstPortType', pl[0].get('name'))

        da = build_app([DoublePortService], 'tns', name='DoublePortApp')

        da.interface.build_interface_document(self.url)
        da_wsdl_el = da.interface.root_elt

        pl2 = da_wsdl_el.findall(self.port_type_string)
        self.assertEqual('FirstPort', pl2[0].get('name'))
        self.assertEqual('SecondPort', pl2[1].get('name'))


    def test_port_count(self):
        sa = build_app([SinglePortService], 'tns', name='SinglePortApp')
        sa.interface.build_interface_document(self.url)
        sa_wsdl_el = sa.interface.root_elt

        self.assertEquals(1, len(sa_wsdl_el.findall(self.port_type_string)))
        pl = sa_wsdl_el.findall(self.port_type_string)
        self.assertEqual(1, len(pl))


        da = build_app([DoublePortService], 'tns', name='DoublePortApp')
        da_wsdl_string = da.interface.build_interface_document(self.url)
        da_wsdl_el = da.interface.root_elt

        self.assertEquals(2, len(da_wsdl_el.findall(self.port_type_string)))

if __name__ == '__main__':
    unittest.main()
