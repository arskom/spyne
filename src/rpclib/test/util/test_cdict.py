#!/usr/bin/env python
#
# rpclib - Copyright (C) Rpclib contributors.
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

import unittest

from rpclib.util.cdict import cdict

class TestClassDict(unittest.TestCase):
    def test_cdict(self):
        d = cdict()

        class A(object):
            pass

        class B(A):
            pass

        class C(A):
            pass

        class D(object):
            pass

        d[A] = 1
        d[C] = 2

        self.assertEquals(d[A], 1)
        self.assertEquals(d[B], 1)
        self.assertEquals(d[C], 2)

        try:
            d[D]
            raise Exception("Must fail")
        except KeyError:
            pass

        try:
            d[object]
            raise Exception("Must fail")
        except KeyError:
            pass

if __name__ == '__main__':
    unittest.main()
