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

from rpclib.application import Application
from rpclib.const import xml_ns as ns
from rpclib.decorator import rpc
from rpclib.model.complex import Array
from rpclib.model.complex import ComplexModel
from rpclib.model.primitive import AnyXml
from rpclib.model.primitive import DateTime
from rpclib.model.primitive import Integer
from rpclib.model.primitive import Unicode
from rpclib.model.primitive import UnsignedLong
from rpclib.protocol.http import HttpRpc
from rpclib.protocol.soap import Soap11
from rpclib.service import ServiceBase
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

    def test_interface(self):
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

        print smm

        raise NotImplementedError('test something!')
if __name__ == '__main__':
    unittest.main()
