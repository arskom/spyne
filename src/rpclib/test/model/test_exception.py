#!/usr/bin/env python
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

import unittest
from rpclib.test import FakeApp
from rpclib.interface.wsdl import Wsdl11
from rpclib.protocol.xml import XmlObject
from rpclib.model.fault import Fault

class FaultTests(unittest.TestCase):
    def test_ctor_defaults(self):
        fault = Fault()
        self.assertEqual(fault.faultcode, 'Server')
        self.assertEqual(fault.faultstring, 'Fault')
        self.assertEqual(fault.faultactor, '')
        self.assertEqual(fault.detail, None)
        self.assertEqual(repr(fault), "Fault(Server: 'Fault')")

    def test_ctor_faultcode_w_senv_prefix(self):
        fault = Fault(faultcode='Other')
        self.assertEqual(fault.faultcode, 'Other')
        self.assertEqual(repr(fault), "Fault(Other: 'Fault')")

    def test_ctor_explicit_faultstring(self):
        fault = Fault(faultstring='Testing')
        self.assertEqual(fault.faultstring, 'Testing')
        self.assertEqual(repr(fault), "Fault(Server: 'Testing')")

    def test_ctor_no_faultstring_overridden_get_type_name(self):
        class Derived(Fault):
            def get_type_name(self):
                return 'Overridden'
        fault = Derived()
        self.assertEqual(fault.faultstring, 'Overridden')
        self.assertEqual(repr(fault), "Fault(Server: 'Overridden')")

    def test_to_parent_element_wo_detail(self):
        from lxml.etree import Element
        import rpclib.const.xml_ns
        ns_soap_env = rpclib.const.xml_ns.soap_env

        element = Element('testing')
        fault = Fault()
        cls = Fault

        XmlObject().to_parent_element(cls, fault, 'urn:ignored', element)

        (child,) = element.getchildren()
        self.assertEqual(child.tag, '{%s}Fault' % ns_soap_env)
        self.assertEqual(child.find('faultcode').text, 'senv:Server')
        self.assertEqual(child.find('faultstring').text, 'Fault')
        self.assertEqual(child.find('faultactor').text, '')
        self.failIf(child.findall('detail'))

    def test_to_parent_element_w_detail(self):
        from lxml.etree import Element
        element = Element('testing')
        detail = Element('something')
        fault = Fault(detail=detail)
        cls = Fault

        XmlObject().to_parent_element(cls, fault, 'urn:ignored', element)

        (child,) = element.getchildren()
        self.failUnless(child.find('detail').find('something') is detail)

    def test_from_xml_wo_detail(self):
        from lxml.etree import Element
        from lxml.etree import SubElement
        import rpclib.const.xml_ns
        ns_soap_env = rpclib.const.xml_ns.soap_env

        element = Element('{%s}Fault' % ns_soap_env)
        fcode = SubElement(element, 'faultcode')
        fcode.text = 'senv:other'
        fstr = SubElement(element, 'faultstring')
        fstr.text = 'Testing'
        actor = SubElement(element, 'faultactor')
        actor.text = 'phreddy'

        fault = XmlObject().from_element(Fault, element)

        self.assertEqual(fault.faultcode, 'senv:other')
        self.assertEqual(fault.faultstring, 'Testing')
        self.assertEqual(fault.faultactor, 'phreddy')
        self.assertEqual(fault.detail, None)

    def test_from_xml_w_detail(self):
        from lxml.etree import Element
        from lxml.etree import SubElement
        import rpclib.const.xml_ns
        ns_soap_env = rpclib.const.xml_ns.soap_env

        element = Element('{%s}Fault' % ns_soap_env)
        fcode = SubElement(element, 'faultcode')
        fcode.text = 'senv:other'
        fstr = SubElement(element, 'faultstring')
        fstr.text = 'Testing'
        actor = SubElement(element, 'faultactor')
        actor.text = 'phreddy'
        detail = SubElement(element, 'detail')

        fault = XmlObject().from_element(Fault, element)

        self.failUnless(fault.detail is detail)

    def test_add_to_schema_no_extends(self):
        import rpclib.const.xml_ns
        ns_xsd = rpclib.const.xml_ns.xsd

        class cls(Fault):
            __namespace__='ns'
            @classmethod
            def get_type_name_ns(self, app):
                return 'testing:My'

        interface = Wsdl11(FakeApp())
        interface.add(cls)

        pref = cls.get_namespace_prefix(interface)
        schema = interface.get_schema_info(pref)

        self.assertEqual(len(schema.types), 1)
        c_cls = interface.classes['{ns}Fault']
        c_elt = schema.types[0]
        self.failUnless(c_cls is cls)
        self.assertEqual(c_elt.tag, '{%s}complexType' % ns_xsd)
        self.assertEqual(c_elt.get('name'), 'Fault')

        self.assertEqual(len(schema.elements), 1)
        e_elt = schema.elements.values()[0]
        self.assertEqual(e_elt.tag, '{%s}element' % ns_xsd)
        self.assertEqual(e_elt.get('name'), 'Fault')
        self.assertEqual(e_elt.get('type'), 'testing:My')
        self.assertEqual(len(e_elt), 0)

    def test_add_to_schema_w_extends(self):
        import rpclib.const.xml_ns
        ns_xsd = rpclib.const.xml_ns.xsd

        class base(Fault):
            __namespace__ = 'ns'
            @classmethod
            def get_type_name_ns(self, app):
                return 'testing:Base'
        class cls(Fault):
            __namespace__ = 'ns'
            @classmethod
            def get_type_name_ns(self, app):
                return 'testing:My'

        interface = Wsdl11(FakeApp())
        interface.add(cls)

        pref = cls.get_namespace_prefix(interface)
        schema = interface.get_schema_info(pref)

        self.assertEqual(len(schema.types), 1)
        self.assertEqual(len(interface.classes), 1)
        c_cls = interface.classes.values()[0]
        c_elt = schema.types.values()[0]
        print c_cls, cls
        self.failUnless(c_cls is cls)
        self.assertEqual(c_elt.tag, '{%s}complexType' % ns_xsd)
        self.assertEqual(c_elt.get('name'), 'Fault')
        self.assertEqual(len(c_elt), 0)

class DummySchemaEntries:
    def __init__(self, app):
        self.app = app
        self._complex_types = []
        self._elements = []

    def add_complex_type(self, cls, ct):
        self._complex_types.append((cls, ct))

    def add_element(self, cls, elt):
        self._elements.append((cls, elt))


if __name__ == '__main__': #pragma NO COVERAGE
    unittest.main()
