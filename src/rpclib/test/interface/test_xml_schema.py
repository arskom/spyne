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

from rpclib.model.primitive import AnyXml
from rpclib.model.complex import ComplexModel
from rpclib.const import xml_ns as ns
from rpclib.util.xml import get_schema_documents

class TestXmlSchema(unittest.TestCase):
    def test_any_tag(self):
        class SomeType(ComplexModel):
            __namespace__ = "zo"

            anything = AnyXml(schema_tag='{%s}any' % ns.xsd, namespace='##other',
                                                         process_contents='lax')

        docs = get_schema_documents([SomeType])
        from lxml import etree
        print etree.tostring(docs['tns'], pretty_print=True)
        any = docs['tns'].xpath('//xsd:any', namespaces={'xsd': ns.xsd})
        assert len(any) == 1
        assert any[0].attrib['namespace'] == '##other'
        assert any[0].attrib['processContents'] == 'lax'

if __name__ == '__main__':
    unittest.main()
