#!/usr/bin/env python

from __future__ import print_function

import unittest
import pytz
import decimal

from pprint import pprint
from decimal import Decimal as D
from datetime import datetime
from lxml import etree

from spyne.const import MAX_STRING_FIELD_LENGTH

from spyne.decorator import srpc
from spyne.application import Application

from spyne.model.complex import XmlAttribute
from spyne.model.complex import ComplexModel
from spyne.model.complex import Iterable
from spyne.model.complex import Array
from spyne.model.primitive import Decimal
from spyne.model.primitive import DateTime
from spyne.model.primitive import Integer
from spyne.model.primitive import Unicode

from spyne.service import ServiceBase

from spyne.util import AttrDict, AttrDictColl

from spyne.util.protocol import deserialize_request_string

from spyne.util.dictdoc import get_dict_as_object, get_object_as_yaml, \
    get_object_as_json
from spyne.util.dictdoc import get_object_as_dict
from spyne.util.tdict import tdict

from spyne.util.xml import get_object_as_xml
from spyne.util.xml import get_xml_as_object
from spyne.util.xml import get_schema_documents
from spyne.util.xml import get_validation_schema


class TestXml(unittest.TestCase):
    def test_serialize(self):

        class C(ComplexModel):
            __namespace__ = "tns"
            i = Integer
            s = Unicode

        c = C(i=5, s="x")

        ret = get_object_as_xml(c, C)
        print(etree.tostring(ret))
        assert ret.tag == "{tns}C"

        ret = get_object_as_xml(c, C, "X")
        print(etree.tostring(ret))
        assert ret.tag == "{tns}X"

        ret = get_object_as_xml(c, C, "X", no_namespace=True)
        print(etree.tostring(ret))
        assert ret.tag == "X"

        ret = get_object_as_xml(c, C, no_namespace=True)
        print(etree.tostring(ret))
        assert ret.tag == "C"

    def test_deserialize(self):
        class Punk(ComplexModel):
            __namespace__ = 'some_namespace'

            a = Unicode
            b = Integer
            c = Decimal
            d = DateTime

        class Foo(ComplexModel):
            __namespace__ = 'some_other_namespace'

            a = Unicode
            b = Integer
            c = Decimal
            d = DateTime
            e = XmlAttribute(Integer)

            def __eq__(self, other):
                # remember that this is a test object
                assert (
                    self.a == other.a and
                    self.b == other.b and
                    self.c == other.c and
                    self.d == other.d and
                    self.e == other.e
                )

                return True

        docs = get_schema_documents([Punk, Foo])
        pprint(docs)
        assert docs['s0'].tag == '{http://www.w3.org/2001/XMLSchema}schema'
        assert docs['tns'].tag == '{http://www.w3.org/2001/XMLSchema}schema'
        print()

        print("the other namespace %r:" % docs['tns'].attrib['targetNamespace'])
        assert docs['tns'].attrib['targetNamespace'] == 'some_namespace'
        print(etree.tostring(docs['tns'], pretty_print=True))
        print()

        print("the other namespace %r:" % docs['s0'].attrib['targetNamespace'])
        assert docs['s0'].attrib['targetNamespace'] == 'some_other_namespace'
        print(etree.tostring(docs['s0'], pretty_print=True))
        print()

        foo = Foo(a=u'a', b=1, c=decimal.Decimal('3.4'),
                                    d=datetime(2011,2,20,tzinfo=pytz.utc), e=5)
        doc = get_object_as_xml(foo, Foo)
        print(etree.tostring(doc, pretty_print=True))
        foo_back = get_xml_as_object(doc, Foo)

        assert foo_back == foo

        # as long as it doesn't fail, it's ok.
        get_validation_schema([Punk, Foo])


class TestCDict(unittest.TestCase):
    def test_cdict(self):
        from spyne.util.cdict import cdict

        class A(object):
            pass

        class B(A):
            pass

        class E(B):
            pass

        class F(E):
            pass

        class C(object):
            pass

        class D:
            pass

        d = cdict({A: "fun", object: "base", F: 'zan'})

        assert d[A] == 'fun'
        assert d[B] == 'fun'
        assert d[C] == 'base'
        assert d[F] == 'zan'
        try:
            d[D]
        except KeyError:
            pass
        else:
            raise Exception("Must fail.")

class TestTDict(unittest.TestCase):
    def test_tdict_notype(self):
        d = tdict()
        d[0] = 1
        assert d[0] == 1

        d = tdict()
        d.update({0:1})
        assert d[0] == 1

        d = tdict.fromkeys([0], 1)
        assert d[0] == 1

    def test_tdict_k(self):
        d = tdict(str)
        try:
            d[0] = 1
        except TypeError:
            pass
        else:
            raise Exception("must fail")

        d = tdict(str)
        d['s'] = 1
        assert d['s'] == 1

    def test_tdict_v(self):
        d = tdict(vt=str)
        try:
            d[0] = 1
        except TypeError:
            pass
        else:
            raise Exception("must fail")

        d = tdict(vt=str)
        d[0] = 's'
        assert d[0] == 's'


class TestLogRepr(unittest.TestCase):
    def test_log_repr_simple(self):
        from spyne.model.complex import ComplexModel
        from spyne.model.primitive import String
        from spyne.util.web import log_repr

        class Z(ComplexModel):
            z=String

        l = MAX_STRING_FIELD_LENGTH + 100
        print(log_repr(Z(z="a" * l)))
        print("Z(z='%s'(...))" % ('a' * MAX_STRING_FIELD_LENGTH))

        assert log_repr(Z(z="a" * l)) == "Z(z='%s'(...))" % \
                                                ('a' * MAX_STRING_FIELD_LENGTH)
        assert log_repr(['a','b','c'], Array(String)) ==  "['a', 'b', (...)]"

    def test_log_repr_complex(self):
        from spyne.model import ByteArray
        from spyne.model import File
        from spyne.model.complex import ComplexModel
        from spyne.model.primitive import String
        from spyne.util.web import log_repr

        class Z(ComplexModel):
            _type_info = [
                ('f', File(logged=False)),
                ('t', ByteArray(logged=False)),
                ('z', Array(String)),
            ]

        l = MAX_STRING_FIELD_LENGTH + 100
        val = Z(z=["abc"] * l, t=['t'], f=File.Value(name='aaa', data=['t']))
        print(repr(val))

        assert log_repr(val) == "Z(z=['abc', 'abc', (...)])"


class TestDeserialize(unittest.TestCase):
    def test_deserialize(self):
        from spyne.protocol.soap import Soap11

        class SomeService(ServiceBase):
            @srpc(Integer, _returns=Iterable(Integer))
            def some_call(yo):
                return range(yo)

        app = Application([SomeService], 'tns', in_protocol=Soap11(),
                                                out_protocol=Soap11())

        meat = 30

        string = """
            <x:Envelope xmlns:x="http://schemas.xmlsoap.org/soap/envelope/">
                <x:Body>
                    <tns:some_call xmlns:tns="tns">
                        <tns:yo>%s</tns:yo>
                    </tns:some_call>
                </x:Body>
            </x:Envelope>
        """ % meat

        obj = deserialize_request_string(string, app)

        assert obj.yo == meat


class TestEtreeDict(unittest.TestCase):

    longMessage = True

    def test_simple(self):
        from lxml.etree import tostring
        from spyne.util.etreeconv import root_dict_to_etree
        assert tostring(root_dict_to_etree({'a':{'b':'c'}})) == '<a><b>c</b></a>'
    
    def test_not_sized(self):
        from lxml.etree import tostring
        from spyne.util.etreeconv import root_dict_to_etree

        complex_value = root_dict_to_etree({'a':{'b':1}})
        self.assertEqual(tostring(complex_value), '<a><b>1</b></a>',
            "The integer should be properly rendered in the etree")

        complex_none = root_dict_to_etree({'a':{'b':None}})
        self.assertEqual(tostring(complex_none), '<a><b/></a>',
            "None should not be rendered in the etree")
        
        simple_value = root_dict_to_etree({'a': 1})
        self.assertEqual(tostring(simple_value), '<a>1</a>',
            "The integer should be properly rendered in the etree")
        
        none_value = root_dict_to_etree({'a': None})
        self.assertEqual(tostring(none_value), '<a/>',
            "None should not be rendered in the etree")
        
        string_value = root_dict_to_etree({'a': 'lol'})
        self.assertEqual(tostring(string_value), '<a>lol</a>',
            "A string should be rendered as a string")
        
        complex_string_value = root_dict_to_etree({'a': {'b': 'lol'}})
        self.assertEqual(tostring(complex_string_value), '<a><b>lol</b></a>',
            "A string should be rendered as a string")


class TestDictDoc(unittest.TestCase):
    def test_the(self):
        class C(ComplexModel):
            __namespace__ = "tns"
            i = Integer
            s = Unicode
            a = Array(DateTime)

            def __eq__(self, other):
                print("Yaaay!")
                return  self.i == other.i and \
                        self.s == other.s and \
                        self.a == other.a

        c = C(i=5, s="x", a=[datetime(2011,12,22, tzinfo=pytz.utc)])

        for iw, ca in ((False,dict), (True,dict), (False,list), (True, list)):
            print()
            print('complex_as:', ca)
            d = get_object_as_dict(c, C, complex_as=ca)
            print(d)
            o = get_dict_as_object(d, C, complex_as=ca)
            print(o)
            print(c)
            assert o == c

class TestAttrDict(unittest.TestCase):
    def test_attr_dict(self):
        assert AttrDict(a=1)['a'] == 1

    def test_attr_dict_coll(self):
        assert AttrDictColl('SomeDict').SomeDict.NAME == 'SomeDict'
        assert AttrDictColl('SomeDict').SomeDict(a=1)['a'] == 1
        assert AttrDictColl('SomeDict').SomeDict(a=1).NAME == 'SomeDict'

class TestYaml(unittest.TestCase):
    def test_deser(self):
        class C(ComplexModel):
            a = Unicode
            b = Decimal

        ret = get_object_as_yaml(C(a='burak', b=D(30)), C)
        assert ret == """C:
    a: burak
    b: '30'
"""

class TestJson(unittest.TestCase):
    def test_deser(self):
        class C(ComplexModel):
            a = Unicode
            b = Decimal

        ret = get_object_as_json(C(a='burak', b=D(30)), C)
        assert ret == '["burak", "30"]'
        ret = get_object_as_json(C(a='burak', b=D(30)), C, complex_as=dict)
        assert ret == '{"a": "burak", "b": "30"}'

class TestFifo(unittest.TestCase):
    def test_msgpack_fifo(self):
        import msgpack

        v1 = [1, 2, 3, 4]
        v2 = [5, 6, 7, 8]
        v3 = {"a": 9, "b": 10, "c": 11}

        s1 = msgpack.packb(v1)
        s2 = msgpack.packb(v2)
        s3 = msgpack.packb(v3)

        unpacker = msgpack.Unpacker()
        unpacker.feed(s1)
        unpacker.feed(s2)
        unpacker.feed(s3[:4])

        assert iter(unpacker).next() == v1
        assert iter(unpacker).next() == v2
        try:
            iter(unpacker).next()
        except StopIteration:
            pass
        else:
            raise Exception("must fail")

        unpacker.feed(s3[4:])
        assert iter(unpacker).next() == v3


if __name__ == '__main__':
    unittest.main()
