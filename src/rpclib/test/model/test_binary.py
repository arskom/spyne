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

import base64
import os
import shutil
import unittest
from tempfile import mkstemp
from lxml import etree

from rpclib.model.binary import ByteArray
import rpclib.const.xml_ns

ns_xsd = rpclib.const.xml_ns.xsd
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

        element = etree.Element('test')
        ByteArray.to_parent_element([data], ns_test, element)
        element = element[0]
        encoded_data = base64.encodestring(data)
        self.assertNotEquals(element.text, None)
        self.assertEquals(element.text, encoded_data)

    def test_from_xml(self):
        f = open(self.tmpfile)
        data = f.read()
        f.close()

        ByteArray.to_parent_element([data], ns_test, element)
        element = element[0]
        a2 = ByteArray.from_xml(element)

        self.assertEquals(data, a2.data)

    def test_add_to_schema(self):
        schema = {}
        ByteArray.add_to_schema(schema)
        self.assertEquals(0, len(schema.keys()))

    def test_get_datatype(self):
        dt = ByteArray.get_type_name()
        self.assertEquals('base64Binary', dt)

        dt = ByteArray.get_namespace()
        assert dt == ns_xsd

if __name__ == '__main__':
    unittest.main()
