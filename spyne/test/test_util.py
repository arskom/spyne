#!/usr/bin/env python

import unittest

from spyne.application import Application
from spyne.const import MAX_STRING_FIELD_LENGTH
from spyne.decorator import srpc
from spyne.model.complex import Iterable
from spyne.model.primitive import Integer
from spyne.service import ServiceBase
from spyne.util.protocol import deserialize_request_string

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

if __name__ == '__main__':
    unittest.main()
