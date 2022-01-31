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

import sys
import unittest
import decimal
import datetime

from pprint import pprint
from base64 import b64encode

from lxml import etree
from lxml.builder import E

from spyne import MethodContext, rpc, ByteArray, File, AnyXml, Ignored
from spyne.context import FakeContext
from spyne.const import RESULT_SUFFIX
from spyne.service import Service
from spyne.server import ServerBase
from spyne.application import Application
from spyne.decorator import srpc
from spyne.util.six import BytesIO
from spyne.model import Fault, Integer, Decimal, Unicode, Date, DateTime, \
    XmlData, Array, ComplexModel, XmlAttribute, Mandatory as M
from spyne.protocol.xml import XmlDocument, SchemaValidationError

from spyne.util import six
from spyne.util.xml import get_xml_as_object, get_object_as_xml, \
    get_object_as_xml_polymorphic, get_xml_as_object_polymorphic
from spyne.server.wsgi import WsgiApplication
from spyne.const.xml import NS_XSI


class TestXml(unittest.TestCase):
    def test_empty_string(self):
        class a(ComplexModel):
            b = Unicode

        elt = etree.fromstring('<a><b/></a>')
        o = get_xml_as_object(elt, a)

        assert o.b == ''

    def test_ignored(self):
        d = decimal.Decimal('1e100')

        class SomeService(Service):
            @srpc(Decimal(120,4), _returns=Decimal)
            def some_call(p):
                print(p)
                print(type(p))
                assert type(p) == decimal.Decimal
                assert d == p
                return Ignored(p)

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

        logging.info(etree.tostring(elt, pretty_print=True).decode('utf8'))
        assert 0 == len(list(elt))


    def test_xml_data(self):
        class C(ComplexModel):
            a = XmlData(Unicode)
            b = XmlAttribute(Unicode)

        class SomeService(Service):
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

        class SomeService(Service):
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
        if not six.PY2:
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
        class SomeService(Service):
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
        class SomeService(Service):
            @srpc(Unicode(pattern=u'x'), _returns=Unicode)
            def some_call(s):
                test(should, never, reach, here)

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

        class SomeService(Service):
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

        class SomeService(Service):
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

    def test_bare_sub_name_ns(self):
        class Action(ComplexModel):
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

    def test_bytearray(self):
        v = b'aaaa'
        elt = get_object_as_xml([v], ByteArray, 'B')
        eltstr = etree.tostring(elt)
        print(eltstr)
        assert elt.text == b64encode(v).decode('ascii')

    def test_any_xml_text(self):
        v = u"<roots><bloody/></roots>"
        elt = get_object_as_xml(v, AnyXml, 'B', no_namespace=True)
        eltstr = etree.tostring(elt)
        print(eltstr)
        assert etree.tostring(elt[0], encoding="unicode") == v

    def test_any_xml_bytes(self):
        v = b"<roots><bloody/></roots>"

        elt = get_object_as_xml(v, AnyXml, 'B', no_namespace=True)
        eltstr = etree.tostring(elt)
        print(eltstr)
        assert etree.tostring(elt[0]) == v

    def test_any_xml_elt(self):
        v = E.roots(E.bloody(E.roots()))
        elt = get_object_as_xml(v, AnyXml, 'B')
        eltstr = etree.tostring(elt)
        print(eltstr)
        assert etree.tostring(elt[0]) == etree.tostring(v)

    def test_file(self):
        v = b'aaaa'
        f = BytesIO(v)
        elt = get_object_as_xml(File.Value(handle=f), File, 'B')
        eltstr = etree.tostring(elt)
        print(eltstr)
        assert elt.text == b64encode(v).decode('ascii')

    def test_fault_detail_as_dict(self):
        elt = get_object_as_xml(Fault(detail={"this": "that"}), Fault)
        eltstr = etree.tostring(elt)
        print(eltstr)
        assert b'<detail><this>that</this></detail>' in eltstr

    def test_xml_encoding(self):
        ctx = FakeContext(out_document=E.rain(u"yağmur"))
        XmlDocument(encoding='iso-8859-9').create_out_string(ctx)
        s = b''.join(ctx.out_string)
        assert u"ğ".encode('iso-8859-9') in s

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

    def test_polymorphic_roundtrip(self):

        class B(ComplexModel):
            __namespace__ = 'some_ns'
            _type_info = {
                '_b': Unicode,
            }

            def __init__(self):
                super(B, self).__init__()
                self._b = "b"

        class C(B):
            __namespace__ = 'some_ns'
            _type_info = {
                '_c': Unicode,
            }

            def __init__(self):
                super(C, self).__init__()
                self._c = "c"

        class A(ComplexModel):
            __namespace__ = 'some_ns'
            _type_info = {
                '_a': Unicode,
                '_b': B,
            }

            def __init__(self, b=None):
                super(A, self).__init__()
                self._a = 'a'
                self._b = b

        a = A(b=C())
        elt = get_object_as_xml_polymorphic(a, A)
        xml_string = etree.tostring(elt, pretty_print=True)
        if six.PY2:
            print(xml_string, end="")
        else:
            sys.stdout.buffer.write(xml_string)

        element_tree = etree.fromstring(xml_string)
        new_a = get_xml_as_object_polymorphic(elt, A)

        assert new_a._a == a._a, (a._a, new_a._a)
        assert new_a._b._b == a._b._b, (a._b._b, new_a._b._b)
        assert new_a._b._c == a._b._c, (a._b._c, new_a._b._c)


class TestIncremental(unittest.TestCase):
    def test_one(self):
        class SomeComplexModel(ComplexModel):
            s = Unicode
            i = Integer

        v = SomeComplexModel(s='a', i=1),

        class SomeService(Service):
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

        class SomeService(Service):
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


if __name__ == '__main__':
    unittest.main()
