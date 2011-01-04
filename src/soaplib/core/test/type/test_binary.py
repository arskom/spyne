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

import base64
import os
import shutil
import unittest
from tempfile import mkstemp
from lxml import etree

from soaplib.core import namespaces
from soaplib.core.model.binary import Attachment

ns_test = 'test_namespace'

class TestBinary(unittest.TestCase):
    def setUp(self):
        os.mkdir('binaryDir')

        fd, self.tmpfile = mkstemp('', '', 'binaryDir')
        os.close(fd)
        f = open(self.tmpfile, 'w')
        for i in range(0, 1000):
            f.write('All work and no play makes jack a dull boy\r\n')
        f.flush()
        f.close()

    def tearDown(self):
        shutil.rmtree('binaryDir')

    def test_to_parent_element_data(self):
        f = open(self.tmpfile)
        data = f.read()
        f.close()
        a = Attachment()
        a.data = data
        element = etree.Element('test')
        Attachment.to_parent_element(a, ns_test, element)
        element = element[0]
        encoded_data = base64.encodestring(data)
        self.assertNotEquals(element.text, None)
        self.assertEquals(element.text, encoded_data)

    def test_to_parent_element_file(self):
        a = Attachment()
        a.file_name = self.tmpfile
        f = open(self.tmpfile, 'rb')
        data = f.read()
        f.close()
        element = etree.Element('test')
        Attachment.to_parent_element(a, ns_test, element)
        element = element[0]
        encoded_data = base64.encodestring(data)
        self.assertNotEquals(element.text, None)
        self.assertEquals(element.text, encoded_data)

    def test_to_from_xml_file(self):
        a = Attachment()
        a.file_name = self.tmpfile
        element = etree.Element('test')
        Attachment.to_parent_element(a, ns_test, element)
        element = element[0]

        data = Attachment.from_xml(element).data

        f = open(self.tmpfile, 'rb')
        fdata = f.read()
        f.close()

        self.assertEquals(data, fdata)

    def test_exception(self):
        try:
            Attachment.to_parent_element(Attachment(), ns_test)
        except:
            self.assertTrue(True)
        else:
            self.assertFalse(True)

    def test_from_xml(self):
        f = open(self.tmpfile)
        data = f.read()
        f.close()

        a = Attachment()
        a.data = data
        element = etree.Element('test')
        Attachment.to_parent_element(a, ns_test, element)
        element = element[0]
        a2 = Attachment.from_xml(element)

        self.assertEquals(data, a2.data)

    def test_add_to_schema(self):
        schema = {}
        Attachment.add_to_schema(schema)
        self.assertEquals(0, len(schema.keys()))

    def test_get_datatype(self):
        dt = Attachment.get_type_name()
        self.assertEquals('base64Binary', dt)

        dt = Attachment.get_namespace()
        assert dt == namespaces.ns_xsd

if __name__ == '__main__':
    unittest.main()
