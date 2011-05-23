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

import unittest

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
        self.port_type_string = '{%s}portType' % rpclib.ns_wsdl
        self.service_string = '{%s}service' % rpclib.ns_wsdl
        self.binding_string = '{%s}binding' % rpclib.ns_wsdl
        self.operation_string = '{%s}operation' % rpclib.ns_wsdl
        self.port_string = '{%s}port' % rpclib.ns_wsdl

    def test_tns(self):
        sa = build_app([SinglePortService], 'SinglePort', 'TestServiceName')
        sa.get_wsdl(self.url)
        sa_el = sa.wsdl.elements
        tns = sa_el.get('targetNamespace')
        self.assertEqual('SinglePort', tns)

        sa = build_app(
            [SinglePortService, DoublePortService],
            'MultiServiceTns',
            'AppName'
        )

        sa.get_wsdl(self.url)
        tns = sa.wsdl.elements.get('targetNamespace')

        self.assertEqual(tns, 'MultiServiceTns')

    def test_raise_missing_port(self):

        # Test that an exception is raised when a port is declared in the service class
        # but the rpc method does not declare a port.

        app = build_app(
            [MissingRPCPortService],
            'MisingPortTns',
            'MissingPortApp'
        )

        self.assertRaises(ValueError, app.get_wsdl, self.url)

        app = build_app(
            [SinglePortService, MissingRPCPortService],
            'MissingPort2Tns',
            'MissingPort2App'
        )

        self.assertRaises(ValueError, app.get_wsdl, self.url)
        

    def test_raise_invalid_port(self):

        app = build_app(
            [BadRPCPortService],
            'MisingPortTns',
            'MissingPortApp'
        )

        self.assertRaises(ValueError,app.get_wsdl, self.url)

        app = build_app(
            [BadRPCPortService, SinglePortService],
            'MissingPort2Tns',
            'MissingPortApp'
        )

        self.assertRaises(ValueError, app.get_wsdl, self.url)

        

    def test_raise_no_service_port(self):

        app = build_app(
            [MissingServicePortService],
            'MisingPortTns',
            'MissingPortApp'
        )

        self.assertRaises(ValueError,app.get_wsdl, self.url)

        app = build_app(
            [SinglePortService, MissingServicePortService],
            'MissingServicePort2Tns',
            'MissingServicePort2App'
        )

        self.assertRaises(ValueError, app.get_wsdl, self.url)


    def test_service_name(self):
        sa = build_app([SinglePortService], 'SinglePort', 'TestServiceName')
        sa_wsdl = sa.get_wsdl(self.url)
        sa_el = sa.wsdl.elements

        sl = [s for s in sa_el.iterfind(self.service_string)]
        name = sl[0].get('name')
        print len(sl)

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
        sa_wsdl_string = sa.get_wsdl(self.url)
        sa_wsdl_el = sa.wsdl.elements

        pl = [el for el in sa_wsdl_el.iterfind(self.port_type_string)]
        self.assertEqual('FirstPortType', pl[0].get('name'))

        da = build_app([DoublePortService], 'tns', name='DoublePortApp')
        da_wsdl_string = da.get_wsdl(self.url)
        da_wsdl_el = da.wsdl.elements

        pl2 = [el for el in da_wsdl_el.iterfind(self.port_type_string)]
        self.assertEqual('FirstPort', pl2[0].get('name'))
        self.assertEqual('SecondPort', pl2[1].get('name'))

        
    def test_port_count(self):
        sa = build_app([SinglePortService], 'tns', name='SinglePortApp')
        sa.interface.get_interface_document(self.url)
        sa_wsdl_el = sa.interface.root_element

        self.assertEquals(1, len(sa_wsdl_el.find(self.port_type_string)))
        pl = sa_wsdl_el.find(self.port_type_string)
        self.assertEqual(1, len(pl))


        da = build_app([DoublePortService], 'tns', name='DoublePortApp')
        da_wsdl_string = da.interface.get_interface_document(self.url)
        da_wsdl_el = da.interface.root_element

        self.assertEquals(2, len(da_wsdl_el.find(self.port_type_string)))
