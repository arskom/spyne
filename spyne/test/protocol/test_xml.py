#!/usr/bin/env python
# encoding: utf-8
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

from __future__ import print_function

import logging
logging.basicConfig(level=logging.DEBUG)


import unittest
import decimal
import datetime

from pprint import pprint

from lxml import etree


from spyne import MethodContext, rpc
from spyne._base import FakeContext
from spyne.const import RESULT_SUFFIX
from spyne.service import ServiceBase
from spyne.server import ServerBase
from spyne.application import Application
from spyne.decorator import srpc
from spyne.util.six import BytesIO
from spyne.model import Fault, Integer, Decimal, Unicode, Date, DateTime, \
    XmlData, Array, ComplexModel, XmlAttribute, Mandatory as M
from spyne.protocol.xml import XmlDocument
from spyne.protocol.xml import SchemaValidationError

from spyne.util import six
from spyne.util.xml import get_xml_as_object, get_object_as_xml
from spyne.server.wsgi import WsgiApplication
from spyne.const.xml import NS_XSI


class TestXml(unittest.TestCase):
    def test_empty_string(self):
        class a(ComplexModel):
            b = Unicode

        elt = etree.fromstring('<a><b/></a>')
        o = get_xml_as_object(elt, a)

        assert o.b == ''

    def test_xml_data(self):
        class C(ComplexModel):
            a = XmlData(Unicode)
            b = XmlAttribute(Unicode)

        class SomeService(ServiceBase):
            @srpc(C, _returns=C)
            def some_call(c):
                assert c.a == 'a'
                assert c.b == 'b'
                return c

        app = Application([SomeService], "tns", name="test_xml_data",
                        in_protocol=XmlDocument(), out_protocol=XmlDocument())
        server = ServerBase(app)
        initial_ctx = MethodContext(server, MethodContext.SERVER)
        initial_ctx.in_string = [
            b'<some_call xmlns="tns">'
                b'<c b="b">a</c>'
            b'</some_call>'
        ]

        ctx, = server.generate_contexts(initial_ctx)
        server.get_in_object(ctx)
        server.get_out_object(ctx)
        server.get_out_string(ctx)

        print(ctx.out_string)
        pprint(app.interface.nsmap)

        ret = etree.fromstring(b''.join(ctx.out_string)).xpath(
            '//tns:some_call' + RESULT_SUFFIX, namespaces=app.interface.nsmap)[0]

        print(etree.tostring(ret, pretty_print=True))

        assert ret.text == "a"
        assert ret.attrib['b'] == "b"

    def test_wrapped_array(self):
        parent = etree.Element('parent')
        val = ['a', 'b']
        cls = Array(Unicode, namespace='tns')
        XmlDocument().to_parent(None, cls, val, parent, 'tns')
        print(etree.tostring(parent, pretty_print=True))
        xpath = parent.xpath('//x:stringArray/x:string/text()',
                                                        namespaces={'x': 'tns'})
        assert xpath == val

    def test_simple_array(self):
        class cls(ComplexModel):
            __namespace__ = 'tns'
            s = Unicode(max_occurs='unbounded')
        val = cls(s=['a', 'b'])

        parent = etree.Element('parent')
        XmlDocument().to_parent(None, cls, val, parent, 'tns')
        print(etree.tostring(parent, pretty_print=True))
        xpath = parent.xpath('//x:cls/x:s/text()', namespaces={'x': 'tns'})
        assert xpath == val.s

    def test_decimal(self):
        d = decimal.Decimal('1e100')

        class SomeService(ServiceBase):
            @srpc(Decimal(120,4), _returns=Decimal)
            def some_call(p):
                print(p)
                print(type(p))
                assert type(p) == decimal.Decimal
                assert d == p
                return p

        app = Application([SomeService], "tns", in_protocol=XmlDocument(),
                                                out_protocol=XmlDocument())
        server = ServerBase(app)
        initial_ctx = MethodContext(server, MethodContext.SERVER)
        initial_ctx.in_string = [
            b'<some_call xmlns="tns"><p>',
            str(d).encode('ascii'),
            b'</p></some_call>'
        ]

        ctx, = server.generate_contexts(initial_ctx)
        server.get_in_object(ctx)
        server.get_out_object(ctx)
        server.get_out_string(ctx)

        elt = etree.fromstring(b''.join(ctx.out_string))

        print(etree.tostring(elt, pretty_print=True))
        target = elt.xpath('//tns:some_callResult/text()',
                                              namespaces=app.interface.nsmap)[0]
        assert target == str(d)

    def test_subs(self):
        from lxml import etree
        from spyne.util.xml import get_xml_as_object
        from spyne.util.xml import get_object_as_xml

        m = {
            "s0": "aa",
            "s2": "cc",
            "s3": "dd",
        }

        class C(ComplexModel):
            __namespace__ = "aa"
            a = Integer
            b = Integer(sub_name="bb")
            c = Integer(sub_ns="cc")
            d = Integer(sub_ns="dd", sub_name="dd")

        elt = get_object_as_xml(C(a=1, b=2, c=3, d=4), C)
        print(etree.tostring(elt, pretty_print=True))

        assert elt.xpath("s0:a/text()",  namespaces=m) == ["1"]
        assert elt.xpath("s0:bb/text()", namespaces=m) == ["2"]
        assert elt.xpath("s2:c/text()",  namespaces=m) == ["3"]
        assert elt.xpath("s3:dd/text()", namespaces=m) == ["4"]

        c = get_xml_as_object(elt, C)
        print(c)
        assert c.a == 1
        assert c.b == 2
        assert c.c == 3
        assert c.d == 4

    def test_sub_attributes(self):
        from lxml import etree
        from spyne.util.xml import get_xml_as_object
        from spyne.util.xml import get_object_as_xml

        m = {
            "s0": "aa",
            "s2": "cc",
            "s3": "dd",
        }

        class C(ComplexModel):
            __namespace__ = "aa"
            a = XmlAttribute(Integer)
            b = XmlAttribute(Integer(sub_name="bb"))
            c = XmlAttribute(Integer(sub_ns="cc"))
            d = XmlAttribute(Integer(sub_ns="dd", sub_name="dd"))

        elt = get_object_as_xml(C(a=1, b=2, c=3, d=4), C)
        print(etree.tostring(elt, pretty_print=True))

        assert elt.xpath("//*/@a")  == ["1"]
        assert elt.xpath("//*/@bb") == ["2"]
        assert elt.xpath("//*/@s2:c", namespaces=m)  == ["3"]
        assert elt.xpath("//*/@s3:dd", namespaces=m) == ["4"]

        c = get_xml_as_object(elt, C)
        print(c)
        assert c.a == 1
        assert c.b == 2
        assert c.c == 3
        assert c.d == 4

    def test_dates(self):
        d = Date
        xml_dates = [
            etree.fromstring(b'<d>2013-04-05</d>'),
            etree.fromstring(b'<d>2013-04-05+02:00</d>'),
            etree.fromstring(b'<d>2013-04-05-02:00</d>'),
            etree.fromstring(b'<d>2013-04-05Z</d>'),
        ]

        for xml_date in xml_dates:
            c = get_xml_as_object(xml_date, d)
            assert isinstance(c, datetime.date) == True
            assert c.year == 2013
            assert c.month == 4
            assert c.day == 5

    def test_datetime_usec(self):
        fs = etree.fromstring
        d = get_xml_as_object(fs('<d>2013-04-05T06:07:08.123456</d>'), DateTime)
        assert d.microsecond == 123456

        # rounds up
        d = get_xml_as_object(fs('<d>2013-04-05T06:07:08.1234567</d>'), DateTime)
        assert d.microsecond == 123457

        # rounds down
        d = get_xml_as_object(fs('<d>2013-04-05T06:07:08.1234564</d>'), DateTime)
        assert d.microsecond == 123456

        # rounds up as well
        d = get_xml_as_object(fs('<d>2013-04-05T06:07:08.1234565</d>'), DateTime)
        # FIXME: this is very interesting. why?
        if six.PY3:
            assert d.microsecond == 123456
        else:
            assert d.microsecond == 123457

    def _get_ctx(self, server, in_string):
        initial_ctx = MethodContext(server, MethodContext.SERVER)
        initial_ctx.in_string = in_string
        ctx, = server.generate_contexts(initial_ctx)
        server.get_in_object(ctx)
        return ctx

    def test_mandatory_elements(self):
        class SomeService(ServiceBase):
            @srpc(M(Unicode), _returns=Unicode)
            def some_call(s):
                assert s == 'hello'
                return s

        app = Application([SomeService], "tns", name="test_mandatory_elements",
                          in_protocol=XmlDocument(validator='lxml'),
                          out_protocol=XmlDocument())
        server = ServerBase(app)

        # Valid call with all mandatory elements in
        ctx = self._get_ctx(server, [
            b'<some_call xmlns="tns">'
                b'<s>hello</s>'
            b'</some_call>'
        ])
        server.get_out_object(ctx)
        server.get_out_string(ctx)
        ret = etree.fromstring(b''.join(ctx.out_string)).xpath(
            '//tns:some_call%s/text()' % RESULT_SUFFIX,
            namespaces=app.interface.nsmap)[0]
        assert ret == 'hello'

        # Invalid call
        ctx = self._get_ctx(server, [
            b'<some_call xmlns="tns">'
                # no mandatory elements here...
            b'</some_call>'
        ])
        self.assertRaises(SchemaValidationError, server.get_out_object, ctx)

    def test_unicode_chars_in_exception(self):
        class SomeService(ServiceBase):
            @srpc(Unicode(pattern=u'x'), _returns=Unicode)
            def some_call(s):
                test(never,reaches,here)

        app = Application([SomeService], "tns", name="test_mandatory_elements",
                          in_protocol=XmlDocument(validator='lxml'),
                          out_protocol=XmlDocument())
        server = WsgiApplication(app)

        req = (
            u'<some_call xmlns="tns">'
                u'<s>Ğ</s>'
            u'</some_call>'
        ).encode('utf8')

        print("AAA")
        resp = server({
            'QUERY_STRING': '',
            'PATH_INFO': '/',
            'REQUEST_METHOD': 'POST',
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '80',
            'wsgi.input': BytesIO(req),
            "wsgi.url_scheme": 'http',
        }, lambda x, y: print(x,y))
        print("AAA")

        assert u'Ğ'.encode('utf8') in b''.join(resp)

    def test_mandatory_subelements(self):
        class C(ComplexModel):
            foo = M(Unicode)

        class SomeService(ServiceBase):
            @srpc(C.customize(min_occurs=1), _returns=Unicode)
            def some_call(c):
                assert c is not None
                assert c.foo == 'hello'
                return c.foo

        app = Application(
            [SomeService], "tns", name="test_mandatory_subelements",
            in_protocol=XmlDocument(validator='lxml'),
            out_protocol=XmlDocument())
        server = ServerBase(app)

        ctx = self._get_ctx(server, [
            b'<some_call xmlns="tns">'
                # no mandatory elements at all...
            b'</some_call>'
        ])
        self.assertRaises(SchemaValidationError, server.get_out_object, ctx)

        ctx = self._get_ctx(server, [
            b'<some_call xmlns="tns">'
                b'<c>'
                    # no mandatory elements here...
                b'</c>'
            b'</some_call>'
        ])
        self.assertRaises(SchemaValidationError, server.get_out_object, ctx)

    def test_mandatory_element_attributes(self):
        class C(ComplexModel):
            bar = XmlAttribute(M(Unicode))

        class SomeService(ServiceBase):
            @srpc(C.customize(min_occurs=1), _returns=Unicode)
            def some_call(c):
                assert c is not None
                assert hasattr(c, 'foo')
                assert c.foo == 'hello'
                return c.foo

        app = Application(
            [SomeService], "tns", name="test_mandatory_element_attributes",
            in_protocol=XmlDocument(validator='lxml'),
            out_protocol=XmlDocument())
        server = ServerBase(app)

        ctx = self._get_ctx(server, [
            b'<some_call xmlns="tns">'
                # no mandatory elements at all...
            b'</some_call>'
        ])
        self.assertRaises(SchemaValidationError, server.get_out_object, ctx)

        ctx = self._get_ctx(server, [
            b'<some_call xmlns="tns">'
                b'<c>'
                    # no mandatory elements here...
                b'</c>'
            b'</some_call>'
        ])
        self.assertRaises(SchemaValidationError, server.get_out_object, ctx)


class TestIncremental(unittest.TestCase):
    def test_one(self):
        class SomeComplexModel(ComplexModel):
            s = Unicode
            i = Integer

        v = SomeComplexModel(s='a', i=1),

        class SomeService(ServiceBase):
            @rpc(_returns=SomeComplexModel)
            def get(ctx):
                return v

        desc = SomeService.public_methods['get']
        ctx = FakeContext(out_object=v, descriptor=desc)
        ostr = ctx.out_stream = BytesIO()
        XmlDocument(Application([SomeService], __name__)) \
                             .serialize(ctx, XmlDocument.RESPONSE)

        elt = etree.fromstring(ostr.getvalue())
        print(etree.tostring(elt, pretty_print=True))

        assert elt.xpath('x:getResult/x:i/text()',
                                            namespaces={'x':__name__}) == ['1']
        assert elt.xpath('x:getResult/x:s/text()',
                                            namespaces={'x':__name__}) == ['a']

    def test_many(self):
        class SomeComplexModel(ComplexModel):
            s = Unicode
            i = Integer

        v = [
            SomeComplexModel(s='a', i=1),
            SomeComplexModel(s='b', i=2),
            SomeComplexModel(s='c', i=3),
            SomeComplexModel(s='d', i=4),
            SomeComplexModel(s='e', i=5),
        ]

        class SomeService(ServiceBase):
            @rpc(_returns=Array(SomeComplexModel))
            def get(ctx):
                return v

        desc = SomeService.public_methods['get']
        ctx = FakeContext(out_object=[v], descriptor=desc)
        ostr = ctx.out_stream = BytesIO()
        XmlDocument(Application([SomeService], __name__)) \
                            .serialize(ctx, XmlDocument.RESPONSE)

        elt = etree.fromstring(ostr.getvalue())
        print(etree.tostring(elt, pretty_print=True))

        assert elt.xpath('x:getResult/x:SomeComplexModel/x:i/text()',
                        namespaces={'x': __name__}) == ['1', '2', '3', '4', '5']
        assert elt.xpath('x:getResult/x:SomeComplexModel/x:s/text()',
                        namespaces={'x': __name__}) == ['a', 'b', 'c', 'd', 'e']

    def test_bare_sub_name_ns(self):
        class Action (ComplexModel):
            class Attributes(ComplexModel.Attributes):
                sub_ns = "SOME_NS"
                sub_name = "Action"
            data = XmlData(Unicode)
            must_understand = XmlAttribute(Unicode)

        elt = get_object_as_xml(Action("x", must_understand="y"), Action)
        eltstr = etree.tostring(elt)
        print(eltstr)
        assert eltstr == b'<ns0:Action xmlns:ns0="SOME_NS" must_understand="y">x</ns0:Action>'

    def test_null_mandatory_attribute(self):
        class Action (ComplexModel):
            data = XmlAttribute(M(Unicode))

        elt = get_object_as_xml(Action(), Action)
        eltstr = etree.tostring(elt)
        print(eltstr)
        assert eltstr == b'<Action/>'

    def test_fault_detail_as_dict(self):
        elt = get_object_as_xml(Fault(detail={"this": "that"}), Fault)
        eltstr = etree.tostring(elt)
        print(eltstr)
        assert b'<detail><this>that</this></detail>' in eltstr

    def test_default(self):
        class SomeComplexModel(ComplexModel):
            _type_info = [
                ('a', Unicode),
                ('b', Unicode(default='default')),
            ]

        obj = XmlDocument().from_element(
            None, SomeComplexModel,
            etree.fromstring("""
                <hey>
                    <a>string</a>
                </hey>
            """)
        )

        # xml schema says it should be None
        assert obj.b == 'default'

        obj = XmlDocument().from_element(
            None, SomeComplexModel,
            etree.fromstring("""
                <hey>
                    <a>string</a>
                    <b xsi:nil="true" xmlns:xsi="%s"/>
                </hey>
            """ % NS_XSI)
        )

        # xml schema says it should be 'default'
        assert obj.b == 'default'

        obj = XmlDocument(replace_null_with_default=False).from_element(
            None, SomeComplexModel,
            etree.fromstring("""
                <hey>
                    <a>string</a>
                    <b xsi:nil="true" xmlns:xsi="%s"/>
                </hey>
            """ % NS_XSI)
        )

        # xml schema says it should be 'default'
        assert obj.b is None


if __name__ == '__main__':
    unittest.main()
