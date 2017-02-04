#!/usr/bin/env python
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

import unittest
from spyne.test import FakeApp
from spyne.interface import Interface
from spyne.interface.wsdl import Wsdl11
from spyne.protocol.xml import XmlDocument
from spyne.model.fault import Fault

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

    def test_to_parent_wo_detail(self):
        from lxml.etree import Element
        import spyne.const.xml
        ns_soap_env = spyne.const.xml.NS_SOAP11_ENV
        soap_env = spyne.const.xml.PREFMAP[spyne.const.xml.NS_SOAP11_ENV]

        element = Element('testing')
        fault = Fault()
        cls = Fault

        XmlDocument().to_parent(None, cls, fault, element, 'urn:ignored')

        (child,) = element.getchildren()
        self.assertEqual(child.tag, '{%s}Fault' % ns_soap_env)
        self.assertEqual(child.find('faultcode').text, '%s:Server' % soap_env)
        self.assertEqual(child.find('faultstring').text, 'Fault')
        self.assertEqual(child.find('faultactor').text, '')
        self.failIf(child.findall('detail'))

    def test_to_parent_w_detail(self):
        from lxml.etree import Element
        element = Element('testing')
        detail = Element('something')
        fault = Fault(detail=detail)
        cls = Fault

        XmlDocument().to_parent(None, cls, fault, element, 'urn:ignored')

        (child,) = element.getchildren()
        self.failUnless(child.find('detail').find('something') is detail)

    def test_from_xml_wo_detail(self):
        from lxml.etree import Element
        from lxml.etree import SubElement
        from spyne.const.xml import PREFMAP, SOAP11_ENV, NS_SOAP11_ENV

        soap_env = PREFMAP[NS_SOAP11_ENV]
        element = Element(SOAP11_ENV('Fault'))

        fcode = SubElement(element, 'faultcode')
        fcode.text = '%s:other' % soap_env
        fstr = SubElement(element, 'faultstring')
        fstr.text = 'Testing'
        actor = SubElement(element, 'faultactor')
        actor.text = 'phreddy'

        fault = XmlDocument().from_element(None, Fault, element)

        self.assertEqual(fault.faultcode, '%s:other' % soap_env)
        self.assertEqual(fault.faultstring, 'Testing')
        self.assertEqual(fault.faultactor, 'phreddy')
        self.assertEqual(fault.detail, None)

    def test_from_xml_w_detail(self):
        from lxml.etree import Element
        from lxml.etree import SubElement
        from spyne.const.xml import SOAP11_ENV

        element = Element(SOAP11_ENV('Fault'))
        fcode = SubElement(element, 'faultcode')
        fcode.text = 'soap11env:other'
        fstr = SubElement(element, 'faultstring')
        fstr.text = 'Testing'
        actor = SubElement(element, 'faultactor')
        actor.text = 'phreddy'
        detail = SubElement(element, 'detail')

        fault = XmlDocument().from_element(None, Fault, element)

        self.failUnless(fault.detail is detail)

    def test_add_to_schema_no_extends(self):
        from spyne.const.xml import XSD

        class cls(Fault):
            __namespace__='ns'
            @classmethod
            def get_type_name_ns(self, app):
                return 'testing:My'

        interface = Interface(FakeApp())
        interface.add_class(cls)

        pref = cls.get_namespace_prefix(interface)
        wsdl = Wsdl11(interface)
        wsdl.build_interface_document('prot://addr')
        schema = wsdl.get_schema_info(pref)

        self.assertEqual(len(schema.types), 1)
        c_cls = interface.classes['{ns}cls']
        c_elt = schema.types[0]
        self.failUnless(c_cls is cls)
        self.assertEqual(c_elt.tag, XSD('complexType'))
        self.assertEqual(c_elt.get('name'), 'cls')

        self.assertEqual(len(schema.elements), 1)
        e_elt = schema.elements.values()[0]
        self.assertEqual(e_elt.tag, XSD('element'))
        self.assertEqual(e_elt.get('name'), 'cls')
        self.assertEqual(e_elt.get('type'), 'testing:My')
        self.assertEqual(len(e_elt), 0)

    def test_add_to_schema_w_extends(self):
        from spyne.const.xml import XSD

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

        interface = Interface(FakeApp())
        interface.add_class(cls)

        pref = cls.get_namespace_prefix(interface)
        wsdl = Wsdl11(interface)
        wsdl.build_interface_document('prot://addr')
        schema = wsdl.get_schema_info(pref)

        self.assertEqual(len(schema.types), 1)
        self.assertEqual(len(interface.classes), 1)

        c_cls = next(iter(interface.classes.values()))
        c_elt = next(iter(schema.types.values()))

        self.failUnless(c_cls is cls)
        self.assertEqual(c_elt.tag, XSD('complexType'))
        self.assertEqual(c_elt.get('name'), 'cls')

        from lxml import etree
        print(etree.tostring(c_elt, pretty_print=True))
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
