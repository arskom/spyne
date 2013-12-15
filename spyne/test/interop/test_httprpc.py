#!/usr/bin/env python
#
# spyne - Copyright (C) Spyne contributors.
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

import time

import pytz
from spyne.util import six

if six.PY2:
    import thread

    from urllib import urlencode
    from urllib2 import urlopen
    from urllib2 import Request
    from urllib2 import HTTPError
else:
    import _thread as thread

    from urllib.parse import urlencode
    from urllib.request import urlopen
    from urllib.request import Request
    from urllib.error import HTTPError

from datetime import datetime

_server_started = False

class TestHttpRpc(unittest.TestCase):
    def setUp(self):
        global _server_started

        if not _server_started:
            def run_server():
                from spyne.test.interop.server.httprpc_pod_basic import main
                main()

            thread.start_new_thread(run_server, ())

            # FIXME: Does anybody have a better idea?
            time.sleep(2)

            _server_started = True

    def test_404(self):
        url = 'http://localhost:9751/404'
        try:
            data = urlopen(url).read()
        except HTTPError as e:
            assert e.code == 404

    def test_413(self):
        url = "http://localhost:9751"
        try:
            data = Request(url,("foo"*3*1024*1024))
        except HTTPError as e:
            assert e.code == 413

    def test_500(self):
        url = 'http://localhost:9751/python_exception'
        try:
            data = urlopen(url).read()
        except HTTPError as e:
            assert e.code == 500

    def test_500_2(self):
        url = 'http://localhost:9751/soap_exception'
        try:
            data = urlopen(url).read()
        except HTTPError as e:
            assert e.code == 500

    def test_echo_string(self):
        url = 'http://localhost:9751/echo_string?s=punk'
        data = urlopen(url).read()

        assert data == 'punk'

    def test_echo_integer(self):
        url = 'http://localhost:9751/echo_integer?i=444'
        data = urlopen(url).read()

        assert data == '444'

    def test_echo_datetime(self):
        dt = datetime.now(pytz.utc).isoformat()
        params = urlencode({
            'dt': dt,
        })

        print(params)
        url = 'http://localhost:9751/echo_datetime?%s' % str(params)
        data = urlopen(url).read()

        assert dt == data

    def test_echo_datetime_tz(self):
        dt = datetime.now(pytz.utc).isoformat()
        params = urlencode({
            'dt': dt,
        })

        print(params)
        url = 'http://localhost:9751/echo_datetime?%s' % str(params)
        data = urlopen(url).read()

        assert dt == data

if __name__ == '__main__':
    unittest.main()
