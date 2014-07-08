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

from webtest import TestApp
from webtest.app import AppError

from spyne import MethodContext, rpc
from spyne._base import FakeContext
from spyne.const import RESULT_SUFFIX
from spyne.service import ServiceBase
from spyne.server import ServerBase
from spyne.application import Application
from spyne.decorator import srpc
from spyne.util.six import StringIO
from spyne.model import Fault
from spyne.model.primitive import Integer
from spyne.model.primitive import Decimal
from spyne.model.primitive import Unicode
from spyne.model.primitive import Date
from spyne.model.primitive import DateTime
from spyne.model.complex import XmlData
from spyne.model.complex import Array
from spyne.model.complex import ComplexModel
from spyne.model.complex import XmlAttribute
from spyne.model.complex import Mandatory as M
from spyne.protocol.xml import XmlDocument
from spyne.protocol.xml import SchemaValidationError
from spyne.util.xml import get_xml_as_object, get_object_as_xml
from spyne.server.wsgi import WsgiApplication


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

        app = Application([SomeService], "tns", name="test_attribute_of",
                        in_protocol=XmlDocument(), out_protocol=XmlDocument())
        server = ServerBase(app)
        initial_ctx = MethodContext(server)
        initial_ctx.in_string = [
            '<some_call xmlns="tns">'
                '<c b="b">a</c>'
            '</some_call>'
        ]

        ctx, = server.generate_contexts(initial_ctx)
        server.get_in_object(ctx)
        server.get_out_object(ctx)
        server.get_out_string(ctx)

        print(ctx.out_string)
        pprint(app.interface.nsmap)

        ret = etree.fromstring(''.join(ctx.out_string)).xpath(
            '//tns:some_call' + RESULT_SUFFIX, namespaces=app.interface.nsmap)[0]

        print(etree.tostring(ret, pretty_print=True))

        assert ret.text == "a"
        assert ret.attrib['b'] == "b"

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

        ret = ''.join(ctx.out_string)
        print(ret)
        ret = etree.fromstring(ret)
        ret = ret.xpath('//s0:a', namespaces=app.interface.nsmap)[0]

        print(etree.tostring(ret, pretty_print=True))

        assert ret.text == "a"
        assert ret.attrib['b'] == "b"

    def test_multiple_attribute_of_multiple_rpc(self):
        """
        Tests the following:

        1. Support for multiple attributes on a single element.
        2. Correctness of attribute definition -- extension applied to correct 'attribute_of' element.
        3. Another class/rpc with same element/attribute name works correctly.
        """


        class CMA(ComplexModel):
            a = Unicode
            ab = XmlAttribute(Unicode, attribute_of="a")
            ac = XmlAttribute(Unicode, attribute_of="a")
            ad = XmlAttribute(Integer, attribute_of="a")

            b = Integer
            bb = XmlAttribute(Unicode, attribute_of="b")

        class CMB(ComplexModel):
            b = Integer
            bb = XmlAttribute(Unicode, attribute_of="b")



        class SomeService(ServiceBase):
            @srpc(CMA, _returns=CMA)
            def some_call(cma):
                assert cma.a == 'a'
                assert cma.ab == 'b'
                assert cma.ac == 'c'
                assert cma.ad == 5
                assert cma.b == 9
                assert cma.bb == "attrib bb"
                return cma

            @srpc(CMB, _returns=CMB)
            def another_call(cmb):
                assert cmb.b == 9
                assert cmb.bb == 'attrib bb'
                return cmb

        app = Application([SomeService], "tns", name="test_multiple_attribute_of",
                        in_protocol=XmlDocument(), out_protocol=XmlDocument())
        server = ServerBase(app)

        # test some_call(CMA)

        initial_ctx = MethodContext(server)
        initial_ctx.in_string = [
            '<some_call xmlns="tns">'
                '<cma>'
                    '<a ab="b" ac="c" ad="5">a</a>'
                    '<b bb="attrib bb">9</b>'
                '</cma>'
            '</some_call>'
        ]

        ctx, = server.generate_contexts(initial_ctx)
        server.get_in_object(ctx)
        server.get_out_object(ctx)
        server.get_out_string(ctx)

        ret = ''.join(ctx.out_string)
        print(ret)
        ret = etree.fromstring(ret)
        ret = ret.xpath('//s0:a', namespaces=app.interface.nsmap)[0]

        print(etree.tostring(ret, pretty_print=True))

        assert ret.text == "a"
        assert ret.attrib['ab'] == "b"
        assert ret.attrib['ac'] == "c"
        assert int(ret.attrib['ad']) == 5

        ret = ret.xpath('//s0:b', namespaces=app.interface.nsmap)[0]
        print(etree.tostring(ret, pretty_print=True))

        assert ret.text == "9"
        assert ret.attrib['bb'] == "attrib bb"

        # test another_call(CMB)

        initial_ctx = MethodContext(server)
        initial_ctx.in_string = [
            '<another_call xmlns="tns">'
                '<cmb>'
                    '<b bb="attrib bb">9</b>'
                '</cmb>'
            '</another_call>'
        ]

        ctx, = server.generate_contexts(initial_ctx)
        server.get_in_object(ctx)
        server.get_out_object(ctx)
        server.get_out_string(ctx)

        ret = ''.join(ctx.out_string)
        print(ret)
        ret = etree.fromstring(ret)
        ret = ret.xpath('//s0:b', namespaces=app.interface.nsmap)[0]

        print(etree.tostring(ret, pretty_print=True))

        assert ret.text == "9"
        assert ret.attrib['bb'] == "attrib bb"


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

        print(etree.tostring(ret[0], pretty_print=True))
        print(etree.tostring(ret[1], pretty_print=True))

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

        print(etree.tostring(elt, pretty_print=True))
        assert target.attrib['{%s}c' % app.interface.nsmap["s1"]] == "bar"

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
        initial_ctx = MethodContext(server)
        initial_ctx.in_string = ['<some_call xmlns="tns"><p>%s</p></some_call>'
                                                                            % d]

        ctx, = server.generate_contexts(initial_ctx)
        server.get_in_object(ctx)
        server.get_out_object(ctx)
        server.get_out_string(ctx)

        elt = etree.fromstring(''.join(ctx.out_string))

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
            etree.fromstring('<d>2013-04-05</d>'),
            etree.fromstring('<d>2013-04-05+02:00</d>'),
            etree.fromstring('<d>2013-04-05-02:00</d>'),
            etree.fromstring('<d>2013-04-05Z</d>'),
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
        assert d.microsecond == 123457

    def _get_ctx(self, server, in_string):
        initial_ctx = MethodContext(server)
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
            '<some_call xmlns="tns">'
                '<s>hello</s>'
            '</some_call>'
        ])
        server.get_out_object(ctx)
        server.get_out_string(ctx)
        ret = etree.fromstring(''.join(ctx.out_string)).xpath(
            '//tns:some_call%s/text()' % RESULT_SUFFIX,
            namespaces=app.interface.nsmap)[0]
        assert ret == 'hello'


        # Invalid call
        ctx = self._get_ctx(server, [
            '<some_call xmlns="tns">'
                # no mandatory elements here...
            '</some_call>'
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
            '<some_call xmlns="tns">'
                '<s>Ğ</s>'
            '</some_call>'
        )

        resp = server({
            'QUERY_STRING': '',
            'PATH_INFO': '/',
            'REQUEST_METHOD': 'POST',
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '80',
            'wsgi.input': StringIO(req),
            "wsgi.url_scheme": 'http',
        }, lambda x,y: print(x,y))

        assert 'Ğ' in ''.join(resp)

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
            '<some_call xmlns="tns">'
                # no mandatory elements at all...
            '</some_call>'
        ])
        self.assertRaises(SchemaValidationError, server.get_out_object, ctx)

        ctx = self._get_ctx(server, [
            '<some_call xmlns="tns">'
                '<c>'
                    # no mandatory elements here...
                '</c>'
            '</some_call>'
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
            '<some_call xmlns="tns">'
                # no mandatory elements at all...
            '</some_call>'
        ])
        self.assertRaises(SchemaValidationError, server.get_out_object, ctx)

        ctx = self._get_ctx(server, [
            '<some_call xmlns="tns">'
                '<c>'
                    # no mandatory elements here...
                '</c>'
            '</some_call>'
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
        ostr = ctx.out_stream = StringIO()
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
        ostr = ctx.out_stream = StringIO()
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


if __name__ == '__main__':
    unittest.main()
