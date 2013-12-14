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


import logging
logging.basicConfig(level=logging.DEBUG)

import unittest

from lxml import etree

from spyne.application import Application

from spyne.test.interface.wsdl import AppTestWrapper
from spyne.test.interface.wsdl import build_app
from spyne.test.interface.wsdl.defult_services import TDefaultPortService
from spyne.test.interface.wsdl.defult_services import TDefaultPortServiceMultipleMethods

from spyne.const import REQUEST_SUFFIX
from spyne.const import RESPONSE_SUFFIX
from spyne.const import ARRAY_SUFFIX

from spyne.const.xml_ns import const_nsmap
from spyne.decorator import srpc
from spyne.service import ServiceBase
from spyne.interface.wsdl import Wsdl11
from spyne.model.complex import Array
from spyne.model.complex import ComplexModel
from spyne.model.complex import XmlAttribute
from spyne.model.primitive import Integer
from spyne.model.primitive import String
from spyne.protocol.soap import Soap11

ns = {
    'wsdl':'http://schemas.xmlsoap.org/wsdl/',
    'xs':'http://www.w3.org/2001/XMLSchema',
}

class TestDefaultWSDLBehavior(unittest.TestCase):
    def _default_service(self, app_wrapper, service_name):
        self.assertEquals(1, len(app_wrapper.get_service_list()))

        services = app_wrapper.get_service_list()
        service = services[0]

        # the default behavior requires that there be only a single service
        self.assertEquals(1, len(services))
        self.assertEquals(service_name, service.get('name'))

        # Test the default service has the correct number of ports
        # the default behavior requires that there be only a single port
        ports = app_wrapper.get_port_list(service)
        self.assertEquals(len(ports), 1)


    def _default_port_type(self, app_wrapper, portType_name, op_count):
        # Verify the portType Count
        portTypes = app_wrapper.get_port_types()

        # there should be only one portType
        self.assertEquals(1, len(portTypes))

        # Verify the portType name
        portType = portTypes[0]
        # Check the name of the port
        self.assertEquals(portType_name, portType.get('name'))

        # verify that the portType definition has the correct
        # number of operations
        ops = app_wrapper.get_port_operations(portType)
        self.assertEquals(op_count, len(ops))

    def _default_binding(self, wrapper, binding_name, opp_count):
        # the default behavior is only single binding
        bindings = wrapper.get_bindings()
        self.assertEquals(1, len(bindings))

        # check for the correct binding name
        binding = bindings[0]
        name = binding.get('name')
        self.assertEquals(binding_name, name)

        # Test that the default service contains the soap binding
        sb = wrapper.get_soap_bindings(binding)
        self.assertEquals(1, len(sb))

        # verify the correct number of operations
        ops = wrapper.get_binding_operations(binding)
        self.assertEquals(opp_count, len(ops))

    def _default_binding_methods(self, wrapper, op_count, op_names):
        binding = wrapper.get_bindings()[0]
        operations = wrapper.get_binding_operations(binding)

        # Check the number of operations bound to the port
        self.assertEquals(op_count, len(operations))

        # Check the operation names are correct
        for op in operations:
            self.assertTrue(op.get('name') in op_names)

    def test_default_port_type(self):
        # Test the default port is created
        # Test the default port has the correct name
        app = build_app(
                [TDefaultPortService()],
                'DefaultPortTest',
                'DefaultPortName'
        )

        wrapper = AppTestWrapper(app)
        self._default_port_type(wrapper, 'DefaultPortName', 1)

    def test_default_port_type_multiple(self):
        app = build_app(
                [TDefaultPortServiceMultipleMethods()],
                'DefaultServiceTns',
                'MultipleDefaultPortServiceApp'
                )

        wrapper = AppTestWrapper(app)

        self._default_port_type(wrapper, "MultipleDefaultPortServiceApp", 3)

    def test_default_binding(self):
        app = build_app(
                [TDefaultPortService()],
                'DefaultPortTest',
                'DefaultBindingName'
        )

        wrapper = AppTestWrapper(app)

        self._default_binding(wrapper, "DefaultBindingName", 1)

    def test_default_binding_multiple(self):
        app = build_app(
                [TDefaultPortServiceMultipleMethods()],
                'DefaultPortTest',
                'MultipleDefaultBindingNameApp'
                )

        wrapper = AppTestWrapper(app)

        self._default_binding(wrapper, 'MultipleDefaultBindingNameApp', 3)

    def test_default_binding_methods(self):
        app = build_app(
            [TDefaultPortService()],
            'DefaultPortTest',
            'DefaultPortMethods'
        )

        wrapper = AppTestWrapper(app)

        self._default_binding_methods(
            wrapper,
            1,
            ['echo_default_port_service']
        )

    def test_bare_simple(self):
        class SomeService(ServiceBase):
            @srpc(String, _returns=String, _body_style='bare')
            def whatever(ss):
                return ss

        app = Application([SomeService], tns='tns')
        app.transport = 'None'

        wsdl = Wsdl11(app.interface)
        wsdl.build_interface_document('url')
        wsdl = etree.fromstring(wsdl.get_interface_document())

        schema = wsdl.xpath(
                '/wsdl:definitions/wsdl:types/xs:schema[@targetNamespace="tns"]',
                namespaces=ns,
            )
        assert len(schema) == 1

        print(etree.tostring(wsdl, pretty_print=True))

        elts = schema[0].xpath(
            'xs:element[@name="whatever%s"]' % REQUEST_SUFFIX, namespaces=ns)
        assert len(elts) > 0
        assert elts[0].attrib['type'] == 'xs:string'

        elts = schema[0].xpath(
            'xs:element[@name="whatever%s"]' % RESPONSE_SUFFIX, namespaces=ns)
        assert len(elts) > 0
        assert elts[0].attrib['type'] == 'xs:string'

    def test_bare_with_conflicting_types(self):
        class SomeService(ServiceBase):
            @srpc(Array(String), _returns=Array(String))
            def whatever(sa):
                return sa
            @srpc(Array(String), _returns=Array(String), _body_style='bare')
            def whatever_bare(sa):
                return sa

        app = Application([SomeService], tns='tns')
        app.transport = 'None'

        wsdl = Wsdl11(app.interface)
        wsdl.build_interface_document('url')
        wsdl = etree.fromstring(wsdl.get_interface_document())
        schema, = wsdl.xpath(
                '/wsdl:definitions/wsdl:types/xs:schema[@targetNamespace="tns"]',
                namespaces=ns,
            )

        print(etree.tostring(schema, pretty_print=True))

        assert len(schema.xpath(
            'xs:complexType[@name="string%s"]' % ARRAY_SUFFIX, namespaces=ns)) > 0

        elts = schema.xpath(
            'xs:element[@name="whatever_bare%s"]' % REQUEST_SUFFIX, namespaces=ns)
        assert len(elts) > 0
        assert elts[0].attrib['type'] == 'tns:string%s' % ARRAY_SUFFIX

        elts = schema.xpath(
            'xs:element[@name="whatever_bare%s"]' % RESPONSE_SUFFIX, namespaces=ns)
        assert len(elts) > 0
        assert elts[0].attrib['type'] == 'tns:string%s' % ARRAY_SUFFIX

    def test_attribute_of(self):
        class SomeObject(ComplexModel):
            c = String
            a = XmlAttribute(Integer, attribute_of='c')

        class SomeService(ServiceBase):
            @srpc(SomeObject)
            def echo_simple_bare(ss):
                pass

        app = Application([SomeService], tns='tns',
                                    in_protocol=Soap11(), out_protocol=Soap11())
        app.transport = 'None'

        wsdl = Wsdl11(app.interface)
        wsdl.build_interface_document('url')

        wsdl = etree.fromstring(wsdl.get_interface_document())
        print(etree.tostring(wsdl, pretty_print=True))
        assert len(wsdl.xpath(
            "/wsdl:definitions/wsdl:types/xs:schema[@targetNamespace='%s']"
            "/xs:complexType[@name='SomeObject']/xs:sequence/xs:element[@name='c']"
            '/xs:complexType/xs:simpleContent/xs:extension/xs:attribute[@name="a"]'
            % (SomeObject.get_namespace()), namespaces=const_nsmap)) > 0

if __name__ == '__main__':
    unittest.main()
