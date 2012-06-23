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
import unittest

from spyne.application import Application
from spyne.const import xml_ns as ns
from spyne.decorator import rpc
from spyne.model.complex import Array
from spyne.model.complex import ComplexModel
from spyne.model.primitive import AnyXml
from spyne.model.primitive import DateTime
from spyne.model.primitive import Integer
from spyne.model.primitive import Unicode
from spyne.model.primitive import UnsignedLong
from spyne.protocol.http import HttpRpc
from spyne.protocol.soap import Soap11
from spyne.service import ServiceBase
from spyne.util.xml import get_schema_documents


class TestXmlSchema(unittest.TestCase):
    def test_any_tag(self):
        logging.basicConfig(level=logging.DEBUG)

        class SomeType(ComplexModel):
            __namespace__ = "zo"

            anything = AnyXml(schema_tag='{%s}any' % ns.xsd, namespace='##other',
                                                         process_contents='lax')

        from lxml import etree

        docs = get_schema_documents([SomeType])
        print(etree.tostring(docs['tns'], pretty_print=True))
        any = docs['tns'].xpath('//xsd:any', namespaces={'xsd': ns.xsd})

        assert len(any) == 1
        assert any[0].attrib['namespace'] == '##other'
        assert any[0].attrib['processContents'] == 'lax'

    def __test_interface(self):
        import logging
        logging.basicConfig(level=logging.DEBUG)
        class KeyValuePair(ComplexModel):
            __namespace__ = "1"
            key = Unicode
            value = Unicode

        class Something(ComplexModel):
            __namespace__ = "2"
            d = DateTime
            i = Integer

        class SomethingElse(ComplexModel):
            __namespace__ = "3"
            a = AnyXml
            b = UnsignedLong
            se = Something

        class Service(ServiceBase):
            @rpc(SomethingElse, _returns=Array(KeyValuePair))
            def some_call(ctx, sth):
                pass

        application = Application([Service],
            in_protocol=HttpRpc(),
            out_protocol=Soap11(),
            name='Service', tns='target_namespace'
        )

        imports = application.interface.imports
        smm = application.interface.service_method_map

        print(smm)

        raise NotImplementedError('test something!')

if __name__ == '__main__':
    unittest.main()
