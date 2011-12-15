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
from lxml import etree

from rpclib.protocol.soap import Soap11
from rpclib.model.binary import ByteArray
from rpclib.model.binary import _bytes_join
import rpclib.const.xml_ns

ns_xsd = rpclib.const.xml_ns.xsd
ns_test = 'test_namespace'

class TestBinary(unittest.TestCase):
    def setUp(self):
        self.data = map(chr, xrange(256))

    def test_data(self):
        element = etree.Element('test')
        Soap11().to_parent_element(ByteArray, self.data, ns_test, element)
        print etree.tostring(element, pretty_print=True)
        element = element[0]

        a2 = Soap11().from_element(ByteArray, element)
        self.assertEquals(_bytes_join(self.data), _bytes_join(a2))

if __name__ == '__main__':
    unittest.main()
