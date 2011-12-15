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

import pytz
import unittest

try:
    from urllib import urlencode
    from urllib2 import urlopen
    from urllib2 import HTTPError
except ImportError:
    from urllib.parse import urlencode
    from urllib.request import urlopen
    from urllib.error import HTTPError

from datetime import datetime

class TestHttpRpc(unittest.TestCase):
    def test_404(self):
        url = 'http://localhost:9757/404'
        try:
            data = urlopen(url).read()
        except HTTPError, e:
            assert e.code == 404

    def test_500(self):
        url = 'http://localhost:9757/python_exception'
        try:
            data = urlopen(url).read()
        except HTTPError, e:
            assert e.code == 500

    def test_500_2(self):
        url = 'http://localhost:9757/soap_exception'
        try:
            data = urlopen(url).read()
        except HTTPError, e:
            assert e.code == 500

    def test_echo_string(self):
        url = 'http://localhost:9757/echo_string?s=punk'
        data = urlopen(url).read()

        assert data == 'punk'

    def test_echo_integer(self):
        url = 'http://localhost:9757/echo_integer?i=444'
        data = urlopen(url).read()

        assert data == '444'

    def test_echo_datetime(self):
        dt = datetime.now().isoformat()
        params = urlencode({
            'dt': dt,
        })

        print(params)
        url = 'http://localhost:9757/echo_datetime?%s' % str(params)
        data = urlopen(url).read()

        assert dt == data

    def test_echo_datetime_tz(self):
        dt = datetime.now(pytz.utc).isoformat()
        params = urlencode({
            'dt': dt,
        })

        print(params)
        url = 'http://localhost:9757/echo_datetime?%s' % str(params)
        data = urlopen(url).read()

        assert dt == data

if __name__ == '__main__':
    unittest.main()
