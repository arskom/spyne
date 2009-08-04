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

import serializers
#import client_test
import soap_test
import service_test


def test_suite():
    suite = serializers.test_suite()
    #suite.addTests(client_test.test_suite())
    suite.addTests(soap_test.test_suite())
    suite.addTests(service_test.test_suite())
    return suite


if __name__== '__main__':
    unittest.TextTestRunner().run(test_suite())
