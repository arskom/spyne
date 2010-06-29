
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

import test_binary
import test_clazz
import test_primitive

def suite():
    loader = unittest.TestLoader()

    suite = loader.loadTestsFromTestCase(test_primitive.TestPrimitive)
    suite.addTests(test_clazz.suite())
    suite.addTests(test_binary.suite())

    return suite

if __name__== '__main__':
    unittest.TextTestRunner().run(suite())
