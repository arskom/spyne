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

import os
from glob import glob
import unittest

from lxml import etree

from soaplib.core.model.clazz import ClassModel
from soaplib.core.model.primitive import String
from soaplib.core.util.xsd_gen import XSDGenerator


class SimpleModel(ClassModel):
    __namespace__ = "SimpleModel"

    text = String

class NestedModel(ClassModel):
    __namespace__ = "NestedModel"

    text = String
    simple_model = SimpleModel

class DoubleNestedModel(ClassModel):
    __namespace__ = "DoubleNestedModel"

    some_text = String
    nested = NestedModel

class TestXsdGen(unittest.TestCase):
    def setUp(self):
        self.xsd_gen = XSDGenerator()

    def tearDown(self):
        for f in glob('*.xsd'):
            os.unlink(f)

    def named_element_check(self, element):
        name_found = False
        for el in element.iter():
            if el.tag.find('element') != -1 and el.attrib['name'] == 'text':
                name_found = True
                break

        return name_found

    def test_simple_xsd(self):
        simple_xsd = self.xsd_gen.get_model_xsd(
            SimpleModel,
            pretty_print=False
        )

        xsd_element = etree.XML(simple_xsd)

        self.assertEquals(xsd_element.attrib['targetNamespace'],
            SimpleModel.get_namespace()
        )

        name_found = self.named_element_check(xsd_element)

        self.assertTrue(name_found)

    def test_nested_xsd(self):
        nested_xsd = self.xsd_gen.get_model_xsd(
            NestedModel,
            pretty_print=False
        )

        tree = etree.XML(nested_xsd)

        self.assertEquals(
            tree.attrib['targetNamespace'],
            NestedModel.get_namespace()
        )

    def test_double_nested_xsd(self):
        double_xsd = self.xsd_gen.get_model_xsd(
                DoubleNestedModel,
                pretty_print=False
        )

        tree = etree.XML(double_xsd)

        self.assertEquals(
            tree.attrib['targetNamespace'],
            DoubleNestedModel.get_namespace()
        )

    def test_xsd_file(self):
        file_name = self.xsd_gen.write_model_xsd_file(SimpleModel, '.')
        self.assertTrue(os.path.isfile(file_name))

    def test_get_all_models(self):
        ret_list = self.xsd_gen.get_all_models_xsd(DoubleNestedModel, pretty_print=True)

        self.assertEquals(len(ret_list), 3)

    def test_write_all_models(self):
        ret_list = self.xsd_gen.write_all_models(DoubleNestedModel, '.')
        self.assertEquals(len(ret_list), 3)
        for file in ret_list:
            self.assertTrue(os.path.isfile(file))

if __name__ == '__main__':
    unittest.main()
