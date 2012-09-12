#!/usr/bin/env python

import unittest


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
    def test_safe_repr(self):
        from spyne.model.complex import ComplexModel
        from spyne.model.primitive import Integer
        from spyne.model.primitive import String
        from spyne.util import safe_repr

        class Z(ComplexModel):
            z=String

        assert safe_repr(Z(z="a"*128)) == "Z(z='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'(...))"


if __name__ == '__main__':
    unittest.main()
