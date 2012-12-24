#!/usr/bin/env python

import unittest

from spyne.application import Application
from spyne.const import MAX_STRING_FIELD_LENGTH
from spyne.decorator import srpc
from spyne.model.complex import ComplexModel
from spyne.model.complex import Iterable
from spyne.model.primitive import Integer
from spyne.model.primitive import Unicode
from spyne.service import ServiceBase
from spyne.util.protocol import deserialize_request_string


class TestXml(unittest.TestCase):
    def test_serialize(self):
        from spyne.util.xml import get_object_as_xml
        from lxml import etree

        class C(ComplexModel):
            __namespace__ = "tns"
            i = Integer
            s = Unicode

        c = C(i=5, s="x")

        ret = get_object_as_xml(c, C)
        print etree.tostring(ret)
        assert ret.tag == "{tns}C"

        ret = get_object_as_xml(c, C, "X")
        print etree.tostring(ret)
        assert ret.tag == "{tns}X"

        ret = get_object_as_xml(c, C, "X", no_namespace=True)
        print etree.tostring(ret)
        assert ret.tag == "X"

        ret = get_object_as_xml(c, C, no_namespace=True)
        print etree.tostring(ret)
        assert ret.tag == "C"


class TestCDict(unittest.TestCase):
    def test_cdict(self):
        from spyne.util.cdict import cdict

        class A(object):
            pass

        class B(A):
            pass

        class C(object):
            pass

        class D:
            pass

        d = cdict({A: "fun", object: "base"})

        assert d[A] == 'fun'
        assert d[B] == 'fun'
        assert d[C] == 'base'
        try:
            d[D]
        except KeyError:
            pass
        else:
            raise Exception("Must fail.")


class TestSafeRepr(unittest.TestCase):
    def test_log_repr(self):
        from spyne.model.complex import ComplexModel
        from spyne.model.primitive import Integer
        from spyne.model.primitive import String
        from spyne.model.complex import log_repr

        class Z(ComplexModel):
            z=String

        assert 128 > MAX_STRING_FIELD_LENGTH
        assert log_repr(Z(z="a"*128)) == "Z(z='%s'(...))" % ('a' * MAX_STRING_FIELD_LENGTH)


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
    def test_simple(self):
        from lxml.etree import tostring
        from spyne.util.etreeconv import root_dict_to_etree

        assert tostring(root_dict_to_etree({'a':{'b':'c'}})) == '<a><b>c</b></a>'

    def test_dict2etree(self):
        from lxml.etree import tostring
        from spyne.util.etreeconv import root_dict_to_etree

        d = {'a':{
                'int':123,
                'string':'string',
                'float':1.0,
                'true':True,
                'false':False,
                'none':None,
                }}

        xml = '<a><none/><false>False</false><string>string</string><int>123</int><float>1.0</float><true>True</true></a>'

        assert tostring(root_dict_to_etree(d)) == xml

    def test_dict2etree_nested(self):
        from lxml.etree import tostring
        from spyne.util.etreeconv import root_dict_to_etree

        d = {'a':{
                'list':[{'list1':1, 'list2':2}],
                'dict':{'dict1':[1,2], 'dict2':(3,4,)},
                }}

        xml = '<a><dict><dict1><dict1>1</dict1><dict1>2</dict1></dict1><dict2><dict2>3</dict2><dict2>4</dict2></dict2></dict><list><list><list1>1</list1><list2>2</list2></list></list></a>'

        assert tostring(root_dict_to_etree(d)) == xml


if __name__ == '__main__':
    unittest.main()
