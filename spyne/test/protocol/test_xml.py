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

import logging
logging.basicConfig(level=logging.DEBUG)

import unittest

from spyne.model.primitive import Unicode
from spyne.model.complex import ComplexModel

from spyne.util.xml import get_xml_as_object
from lxml import etree

class Test(unittest.TestCase):
    def test_empty_string(self):
        class a(ComplexModel):
            b = Unicode

        elt = etree.fromstring('<a><b/></a>')
        o = get_xml_as_object(elt, a)

        assert o.b == ''

if __name__ == '__main__':
    unittest.main()
