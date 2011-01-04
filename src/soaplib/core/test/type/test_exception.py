#!/usr/bin/env python
#
# soaplib - Copyright (C) Soaplib contributors.
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

class FaultTests(unittest.TestCase):

    def _getTargetClass(self):
        from soaplib.core.model.exception import Fault
        return Fault

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_ctor_defaults(self):
        fault = self._makeOne()
        self.assertEqual(fault.faultcode, 'senv:Server')
        self.assertEqual(fault.faultstring, 'Fault')
        self.assertEqual(fault.faultactor, '')
        self.assertEqual(fault.detail, None)
        self.assertEqual(repr(fault), "senv:Server: 'Fault'")

    def test_ctor_faultcode_w_senv_prefix(self):
        fault = self._makeOne(faultcode='senv:Other')
        self.assertEqual(fault.faultcode, 'senv:Other')
        self.assertEqual(repr(fault), "senv:Other: 'Fault'")

    def test_ctor_explicit_faultstring(self):
        fault = self._makeOne(faultstring='Testing')
        self.assertEqual(fault.faultstring, 'Testing')
        self.assertEqual(repr(fault), "senv:Server: 'Testing'")

    def test_ctor_no_faultstring_overridden_get_type_name(self):
        class Derived(self._getTargetClass()):
            def get_type_name(self):
                return 'Overridden'
        fault = Derived()
        self.assertEqual(fault.faultstring, 'Overridden')
        self.assertEqual(repr(fault), "senv:Server: 'Overridden'")

    def test_to_parent_element_wo_detail(self):
        from lxml.etree import Element
        from soaplib.core.namespaces import ns_soap_env
        element = Element('testing')
        fault = self._makeOne()
        cls = self._getTargetClass()

        cls.to_parent_element(fault, 'urn:ignored', element)

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
        fault = self._makeOne(detail=detail)
        cls = self._getTargetClass()

        cls.to_parent_element(fault, 'urn:ignored', element)

        (child,) = element.getchildren()
        self.failUnless(child.find('detail').find('something') is detail)

    def test_add_to_parent_element(self):
        from lxml.etree import Element
        from soaplib.core.namespaces import ns_soap_env
        element = Element('testing')
        fault = self._makeOne()
        cls = self._getTargetClass()

        fault.add_to_parent_element('urn:ignored', element)

        (child,) = element.getchildren()
        self.assertEqual(child.tag, '{%s}Fault' % ns_soap_env)
        self.assertEqual(child.find('faultcode').text, 'senv:Server')
        self.assertEqual(child.find('faultstring').text, 'Fault')
        self.assertEqual(child.find('faultactor').text, '')
        self.failIf(child.findall('detail'))

    def test_from_xml_wo_detail(self):
        from lxml.etree import Element
        from lxml.etree import SubElement
        from soaplib.core.namespaces import ns_soap_env
        element = Element('{%s}Fault' % ns_soap_env)
        fcode = SubElement(element, 'faultcode')
        fcode.text = 'senv:other'
        fstr = SubElement(element, 'faultstring')
        fstr.text = 'Testing'
        actor = SubElement(element, 'faultactor')
        actor.text = 'phreddy'

        fault = self._getTargetClass().from_xml(element)

        self.assertEqual(fault.faultcode, 'senv:other')
        self.assertEqual(fault.faultstring, 'Testing')
        self.assertEqual(fault.faultactor, 'phreddy')
        self.assertEqual(fault.detail, None)

    def test_from_xml_w_detail(self):
        from lxml.etree import Element
        from lxml.etree import SubElement
        from soaplib.core.namespaces import ns_soap_env
        element = Element('{%s}Fault' % ns_soap_env)
        fcode = SubElement(element, 'faultcode')
        fcode.text = 'senv:other'
        fstr = SubElement(element, 'faultstring')
        fstr.text = 'Testing'
        actor = SubElement(element, 'faultactor')
        actor.text = 'phreddy'
        detail = SubElement(element, 'detail')

        fault = self._getTargetClass().from_xml(element)

        self.failUnless(fault.detail is detail)

    def test_add_to_schema_no_extends(self):
        from soaplib.core.namespaces import ns_xsd
        class cls(self._getTargetClass()):
            @classmethod
            def get_type_name_ns(self, app):
                return 'testing:My'

        schema = DummySchemaEntries(object())

        cls.add_to_schema(schema)

        self.assertEqual(len(schema._complex_types), 1)
        c_cls, c_elt = schema._complex_types[0]
        self.failUnless(c_cls is cls)
        self.assertEqual(c_elt.tag, '{%s}complexType' % ns_xsd)
        self.assertEqual(c_elt.get('name'), 'FaultFault')
        self.assertEqual(len(c_elt), 1)
        seq = c_elt[0]
        self.assertEqual(seq.tag, '{%s}sequence' % ns_xsd)

        self.assertEqual(len(schema._elements), 1)
        e_cls, e_elt = schema._elements[0]
        self.failUnless(e_cls is cls)
        self.assertEqual(e_elt.tag, '{%s}element' % ns_xsd)
        self.assertEqual(e_elt.get('name'), 'Fault')
        self.assertEqual(e_elt.get('{%s}type' % ns_xsd), 'testing:MyFault')
        self.assertEqual(len(e_elt), 0)

    def test_add_to_schema_w_extends(self):
        from soaplib.core.namespaces import ns_xsd
        class base(self._getTargetClass()):
            @classmethod
            def get_type_name_ns(self, app):
                return 'testing:Base'
        class cls(self._getTargetClass()):
            __extends__ = base
            @classmethod
            def get_type_name_ns(self, app):
                return 'testing:My'

        schema = DummySchemaEntries(object())

        cls.add_to_schema(schema)

        self.assertEqual(len(schema._complex_types), 1)
        c_cls, c_elt = schema._complex_types[0]
        self.failUnless(c_cls is cls)
        self.assertEqual(c_elt.tag, '{%s}complexType' % ns_xsd)
        self.assertEqual(c_elt.get('name'), 'FaultFault')
        self.assertEqual(len(c_elt), 1)

        cc_elt = c_elt[0]
        self.assertEqual(cc_elt.tag, '{%s}complexContent' % ns_xsd)
        self.assertEqual(len(cc_elt), 1)

        e_elt = cc_elt[0]
        self.assertEqual(e_elt.tag, '{%s}extension' % ns_xsd)
        self.assertEqual(e_elt.get('base'), 'testing:Base')
        self.assertEqual(len(e_elt), 1)

        seq = e_elt[0]
        self.assertEqual(seq.tag, '{%s}sequence' % ns_xsd)

        self.assertEqual(len(schema._elements), 1)
        e_cls, e_elt = schema._elements[0]
        self.failUnless(e_cls is cls)
        self.assertEqual(e_elt.tag, '{%s}element' % ns_xsd)
        self.assertEqual(e_elt.get('name'), 'Fault')
        self.assertEqual(e_elt.get('{%s}type' % ns_xsd), 'testing:MyFault')
        self.assertEqual(len(e_elt), 0)

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
