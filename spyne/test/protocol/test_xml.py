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

from lxml import etree

from spyne import MethodContext
from spyne.service import ServiceBase
from spyne.server import ServerBase
from spyne.application import Application
from spyne.decorator import srpc
from spyne.model.primitive import Unicode
from spyne.model.complex import ComplexModel
from spyne.model.complex import XmlAttribute
from spyne.service import ServiceBase
from spyne.protocol.xml import XmlDocument

from spyne.util.xml import get_xml_as_object


class TestXml(unittest.TestCase):
    def test_empty_string(self):
        class a(ComplexModel):
            b = Unicode

        elt = etree.fromstring('<a><b/></a>')
        o = get_xml_as_object(elt, a)

        assert o.b == ''

    def test_attribute_of(self):
        class C(ComplexModel):
            a = Unicode
            b = XmlAttribute(Unicode, attribute_of="a")

        class SomeService(ServiceBase):
            @srpc(C, _returns=C)
            def some_call(c):
                assert c.a == 'a'
                assert c.b == 'b'
                return c

        app = Application([SomeService], "tns", name="test_attribute_of",
                        in_protocol=XmlDocument(), out_protocol=XmlDocument())
        server = ServerBase(app)

        initial_ctx = MethodContext(server)
        initial_ctx.in_string = [
            '<some_call xmlns="tns">'
                '<c>'
                    '<a b="b">a</a>'
                '</c>'
            '</some_call>'
        ]

        ctx, = server.generate_contexts(initial_ctx)
        server.get_in_object(ctx)
        server.get_out_object(ctx)
        server.get_out_string(ctx)

        ret = etree.fromstring(''.join(ctx.out_string)).xpath('//s0:a',
                                              namespaces=app.interface.nsmap)[0]

        print etree.tostring(ret, pretty_print=True)

        assert ret.text == "a"
        assert ret.attrib['b'] == "b"

    def test_attribute_of_multi(self):
        class C(ComplexModel):
            e = Unicode(max_occurs='unbounded')
            a = XmlAttribute(Unicode, attribute_of="e")

        class SomeService(ServiceBase):
            @srpc(C, _returns=C)
            def some_call(c):
                assert c.e == ['e0', 'e1']
                assert c.a == ['a0', 'a1']
                return c

        app = Application([SomeService], "tns", name="test_attribute_of",
                          in_protocol=XmlDocument(), out_protocol=XmlDocument())
        server = ServerBase(app)

        initial_ctx = MethodContext(server)
        initial_ctx.method_request_string = '{test_attribute_of}some_call'
        initial_ctx.in_string = [
            '<some_call xmlns="tns">'
                '<c>'
                    '<e a="a0">e0</e>'
                    '<e a="a1">e1</e>'
                '</c>'
            '</some_call>'
        ]

        ctx, = server.generate_contexts(initial_ctx)
        server.get_in_object(ctx)
        server.get_out_object(ctx)
        server.get_out_string(ctx)

        ret = etree.fromstring(''.join(ctx.out_string)).xpath('//s0:e',
                                                 namespaces=app.interface.nsmap)

        print etree.tostring(ret[0], pretty_print=True)
        print etree.tostring(ret[1], pretty_print=True)

        assert ret[0].text == "e0"
        assert ret[0].attrib['a'] == "a0"
        assert ret[1].text == "e1"
        assert ret[1].attrib['a'] == "a1"

    def test_attribute_ns(self):
        class a(ComplexModel):
            b = Unicode
            c = XmlAttribute(Unicode, ns="spam", attribute_of="b")

        class SomeService(ServiceBase):
            @srpc(_returns=a)
            def some_call():
                return a(b="foo",c="bar")

        app = Application([SomeService], "tns", in_protocol=XmlDocument(),
                                                out_protocol=XmlDocument())
        server = ServerBase(app)
        initial_ctx = MethodContext(server)
        initial_ctx.in_string = ['<some_call xmlns="tns"/>']

        ctx, = server.generate_contexts(initial_ctx)
        server.get_in_object(ctx)
        server.get_out_object(ctx)
        server.get_out_string(ctx)

        elt = etree.fromstring(''.join(ctx.out_string))
        target = elt.xpath('//s0:b', namespaces=app.interface.nsmap)[0]
        target.attrib['{%s}c' % app.interface.nsmap["s1"]] == "bar"


if __name__ == '__main__':
    unittest.main()
