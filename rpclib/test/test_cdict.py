#!/usr/bin/env python

import unittest

from rpclib.util.cdict import cdict

class A(object):
    pass

class B(A):
    pass

class C(object):
    pass

class D:
    pass

class TestCDict(unittest.TestCase):
    def test_cdict(self):
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

if __name__ == '__main__':
    unittest.main()
