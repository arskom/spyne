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
import urllib
import urllib2

from datetime import datetime

class TestHttpRpc(unittest.TestCase):
    def test_404(self):
        url = 'http://localhost:9757/404'
        try:
            data = urllib2.urlopen(url).read()
        except urllib2.HTTPError, e:
            assert e.code == 404

    def test_500(self):
        url = 'http://localhost:9757/python_exception'
        try:
            data = urllib2.urlopen(url).read()
        except urllib2.HTTPError, e:
            assert e.code == 500

    def test_500_2(self):
        url = 'http://localhost:9757/soap_exception'
        try:
            data = urllib2.urlopen(url).read()
        except urllib2.HTTPError, e:
            assert e.code == 500

    def test_echo_string(self):
        url = 'http://localhost:9757/echo_string?s=punk'
        data = urllib2.urlopen(url).read()

        assert data == 'punk'

    def test_echo_integer(self):
        url = 'http://localhost:9757/echo_integer?i=444'
        data = urllib2.urlopen(url).read()

        assert data == '444'

    def test_echo_datetime(self):
        dt = datetime.now().isoformat()
        params = urllib.urlencode({
            'dt': dt,
        })

        print(params)
        url = 'http://localhost:9757/echo_datetime?%s' % str(params)
        data = urllib2.urlopen(url).read()

        assert dt == data

    def test_echo_datetime_tz(self):
        dt = datetime.now(pytz.utc).isoformat()
        params = urllib.urlencode({
            'dt': dt,
        })

        print(params)
        url = 'http://localhost:9757/echo_datetime?%s' % str(params)
        data = urllib2.urlopen(url).read()

        assert dt == data

if __name__ == '__main__':
    unittest.main()
