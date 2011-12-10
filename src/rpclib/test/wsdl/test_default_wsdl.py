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

from rpclib.test.wsdl import AppTestWrapper
from rpclib.test.wsdl import build_app
from rpclib.test.wsdl.defult_services import DefaultPortService
from rpclib.test.wsdl.defult_services import DefaultPortServiceMultipleMethods


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

    def test_default_service(self):
        single_app = build_app(
                [DefaultPortService],
                'DefaultServiceTns',
                'DefaultPortServiceApp'
                )

        single_wrapper = AppTestWrapper(single_app)
        self._default_service(single_wrapper, "DefaultPortServiceApp")

    def test_default_service_multiple_methods(self):
        triple_app = build_app(
                [DefaultPortServiceMultipleMethods],
                'DefaultServiceTns',
                'DefaultPortServiceApp'
                )

        triple_wrapper = AppTestWrapper(triple_app)
        self._default_service(triple_wrapper, "DefaultPortServiceApp")

    def test_default_port_type(self):
        # Test the default port is created
        # Test the default port has the correct name

        app = build_app(
                [DefaultPortService],
                'DefaultPortTest',
                'DefaultPortName'
        )

        wrapper = AppTestWrapper(app)
        self._default_port_type(wrapper, 'DefaultPortName', 1)

    def test_default_port_type_multiple(self):
        app = build_app(
                [DefaultPortServiceMultipleMethods],
                'DefaultServiceTns',
                'MultipleDefaultPortServiceApp'
                )

        wrapper = AppTestWrapper(app)

        self._default_port_type(wrapper, "MultipleDefaultPortServiceApp", 3)

    def test_default_binding(self):
        app = build_app(
                [DefaultPortService],
                'DefaultPortTest',
                'DefaultBindingName'
        )

        wrapper = AppTestWrapper(app)

        self._default_binding(wrapper, "DefaultBindingName", 1)

    def test_default_binding_multiple(self):
        app = build_app(
                [DefaultPortServiceMultipleMethods],
                'DefaultPortTest',
                'MultipleDefaultBindingNameApp'
                )

        wrapper = AppTestWrapper(app)

        self._default_binding(wrapper, 'MultipleDefaultBindingNameApp', 3)

    def test_default_binding_methods(self):
        app = build_app(
            [DefaultPortService],
            'DefaultPortTest',
            'DefaultPortMethods'
        )

        wrapper = AppTestWrapper(app)

        self._default_binding_methods(
            wrapper,
            1,
            ['echo_default_port_service']
        )

    def test_default_binding_methods_multiple(self):
        app = build_app(
                [DefaultPortServiceMultipleMethods],
                'DefaultBindingMethodsTns',
                'MultipleDefaultBindMethodsApp'
        )

        wrapper = AppTestWrapper(app)

        self._default_binding_methods(
                wrapper,
                3,
                ['echo_one', 'echo_two', 'echo_three']
        )

if __name__ == '__main__':
    unittest.main()
