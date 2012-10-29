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

from spyne import MethodContext
from spyne.service import ServiceBase
from spyne.server import ServerBase
from spyne.application import Application
from spyne.decorator import srpc
from spyne.model.primitive import Unicode
from spyne.model.complex import ComplexModel
from spyne.model.complex import XmlAttribute
from spyne.service import ServiceBase
from spyne.interface.wsdl import Wsdl11
from spyne.protocol.xml import XmlDocument


from spyne.util.xml import get_xml_as_object
from lxml import etree

class Test(unittest.TestCase):
    def test_empty_string(self):
        class a(ComplexModel):
            b = Unicode

        elt = etree.fromstring('<a><b/></a>')
        o = get_xml_as_object(elt, a)

        assert o.b == ''

    def test_attribute_of(self):
        class a(ComplexModel):
            b = Unicode
            c = XmlAttribute(Unicode, attribute_of="b")

        class SomeService(ServiceBase):
            @srpc(_returns=a)
            def some_call():
                return a(b="foo",c="bar")

        app = Application([SomeService], "tns", in_protocol=XmlDocument(), out_protocol=XmlDocument())
        server = ServerBase(app)
        initial_ctx = MethodContext(server)
        initial_ctx.in_string = ['<some_call xmlns="tns"/>']

        ctx, = server.generate_contexts(initial_ctx)
        server.get_in_object(ctx)
        server.get_out_object(ctx)
        server.get_out_string(ctx)

        assert etree.fromstring(''.join(ctx.out_string)).xpath('//s0:b',
            namespaces=app.interface.nsmap)[0].attrib['c'] == "bar"

    def test_attribute_ns(self):
        class a(ComplexModel):
            b = Unicode
            c = XmlAttribute(Unicode, ns="spam", attribute_of="b")

        class SomeService(ServiceBase):
            @srpc(_returns=a)
            def some_call():
                return a(b="foo",c="bar")

        app = Application([SomeService], "tns", in_protocol=XmlDocument(), out_protocol=XmlDocument())
        server = ServerBase(app)
        initial_ctx = MethodContext(server)
        initial_ctx.in_string = ['<some_call xmlns="tns"/>']

        ctx, = server.generate_contexts(initial_ctx)
        server.get_in_object(ctx)
        server.get_out_object(ctx)
        server.get_out_string(ctx)

        assert etree.fromstring(''.join(ctx.out_string)).xpath('//s0:b',
            namespaces=app.interface.nsmap)[0].attrib['{%s}c'%app.interface.nsmap["s1"]] == "bar"




if __name__ == '__main__':
    unittest.main()
