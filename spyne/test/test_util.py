#!/usr/bin/env python

import urllib
import unittest

from StringIO import StringIO

from wsgiref.validate import validator

from spyne.application import Application
from spyne.const import MAX_STRING_FIELD_LENGTH
from spyne.decorator import srpc
from spyne.model.complex import ComplexModel
from spyne.model.complex import Iterable
from spyne.model.primitive import Integer
from spyne.model.primitive import Unicode
from spyne.service import ServiceBase
from spyne.util.wsgi_wrapper import WsgiMounter
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


def uber(mn):
    return {
        'SCRIPT_NAME': mn,
        'QUERY_STRING': '',
        'PATH_INFO': mn,
        'REQUEST_METHOD': 'GET',
        'SERVER_NAME': 'localhost',
        'SERVER_PORT': "9999",
        'wsgi.url_scheme': 'http',
        'wsgi.version': (1,0),
        'wsgi.input': StringIO(),
        'wsgi.errors': StringIO(),
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
        'wsgi.run_once': True,
    }

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

class TestWsgiMounter(unittest.TestCase):
    def test_wsgi_mounter_1(self):
        from spyne.protocol.http import HttpRpc
        from spyne.protocol.http import HttpPattern

        s = []
        r = []

        class RootService(ServiceBase):
            @srpc(Integer, _patterns=[HttpPattern('/a/<code>')])
            def root_code(code):
                r.append(code)

        class SomeService(ServiceBase):
            @srpc(Integer, _patterns=[HttpPattern('/a/<code>')])
            def some_code(code):
                s.append(code)

        some_app = Application([SomeService], 'some', in_protocol=HttpRpc(),
                                                    out_protocol=HttpRpc())
        root_app = Application([RootService], 'root', in_protocol=HttpRpc(),
                                                    out_protocol=HttpRpc())

        wsgi_app = WsgiMounter({'some': some_app}, root=root_app)

        def start_response(code, headers):
            print code
            print headers

        ret = ''.join(validator(wsgi_app)(uber('/a/5'), start_response))
        assert r == [5]
        print(ret)

        ret = ''.join(validator(wsgi_app)(uber('/some/a/5'), start_response))
        print(ret)
        assert r == [5]
        assert s == [5]


if __name__ == '__main__':
    unittest.main()
