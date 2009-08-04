#
# soaplib - Copyright (C) 2009 Aaron Bickell, Jamie Kirkpatrick
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

import primitive_test
import clazz_test
import binary_test


def test_suite():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(primitive_test.test)
    suite.addTests(clazz_test.test_suite())
    suite.addTests(binary_test.test_suite())
    return suite

if __name__== '__main__':
    unittest.TextTestRunner().run(test_suite())
