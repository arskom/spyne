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


from . import build_app
from .port_service_services import DoublePortService, SinglePortService, S1

class TestWSDLBindingBehavior(unittest.TestCase):
    def setUp(self):
        self.transport = 'http://schemas.xmlsoap.org/soap/http'
        self.url = 'http:/localhost:7789/wsdl'
        self.port_type_string = '{%s}portType' % ns.wsdl
        self.service_string = '{%s}service' % ns.wsdl
        self.binding_string = '{%s}binding' % ns.wsdl
        self.operation_string = '{%s}operation' % ns.wsdl
        self.port_string = '{%s}port' % ns.wsdl

    def test_binding_simple(self):
        sa = build_app([S1], 'S1Port', 'TestServiceName')

        sa.interface.build_interface_document(self.url)

        services =  sa.interface.root_elt.xpath(
                        '/wsdl:definitions/wsdl:service', 
                        namespaces = { 
                            'wsdl':'http://schemas.xmlsoap.org/wsdl/' })
        self.assertEqual(len(services), 1)
        
        portTypes =  sa.interface.root_elt.xpath(
                        '/wsdl:definitions/wsdl:portType', 
                        namespaces = { 
                            'wsdl':'http://schemas.xmlsoap.org/wsdl/' })
        self.assertEqual(len(portTypes), 1)

        ports =  sa.interface.root_elt.xpath(
                        '/wsdl:definitions/wsdl:service[@name="%s"]/wsdl:port' % 
                            "S1", 
                        namespaces = {
                            'wsdl':'http://schemas.xmlsoap.org/wsdl/' })
        self.assertEqual(len(ports), 1)
        

    def test_binding_multiple(self):
        sa = build_app(
            [SinglePortService, DoublePortService],
            'MultiServiceTns',
            'AppName'
        )
        sa.interface.build_interface_document(self.url)

        # 2 Service, 
        # First has 1 port
        # Second has 2
         
        # => need 2 service, 3 port and 3 bindings

        services =  sa.interface.root_elt.xpath(
                        '/wsdl:definitions/wsdl:service', 
                        namespaces = { 
                            'wsdl':'http://schemas.xmlsoap.org/wsdl/' })
        self.assertEqual(len(services), 2)
        
        
        portTypes =  sa.interface.root_elt.xpath(
                        '/wsdl:definitions/wsdl:portType', 
                        namespaces = { 
                            'wsdl':'http://schemas.xmlsoap.org/wsdl/' })
        self.assertEqual(len(portTypes), 3)


        bindings =  sa.interface.root_elt.xpath(
                        '/wsdl:definitions/wsdl:binding', 
                        namespaces = {
                            'wsdl':'http://schemas.xmlsoap.org/wsdl/' })

        self.assertEqual(len(bindings), 3)

        ports =  sa.interface.root_elt.xpath(
                        '/wsdl:definitions/wsdl:service[@name="%s"]/wsdl:port' % 
                            SinglePortService.__service_name__, 
                        namespaces = {
                            'wsdl':'http://schemas.xmlsoap.org/wsdl/' })
        self.assertEqual(len(ports), 1)
        
        ports =  sa.interface.root_elt.xpath(
                        '/wsdl:definitions/wsdl:service[@name="%s"]/wsdl:port' % 
                            "DoublePortService", 
                        namespaces = {
                            'wsdl':'http://schemas.xmlsoap.org/wsdl/' })
        self.assertEqual(len(ports), 2)
        
        # checking name and type
        #service SinglePortService
        for srv in ( SinglePortService, DoublePortService ):
            for port in srv.__port_types__:
                bindings =  sa.interface.root_elt.xpath(
                                '/wsdl:definitions/wsdl:binding[@name="%s"]' %
                                    port, 
                                namespaces = {
                                    'wsdl':'http://schemas.xmlsoap.org/wsdl/' })
                self.assertEqual(bindings[0].get('type'), "tns:%s" % port) 



    
    
    