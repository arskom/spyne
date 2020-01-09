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

from datetime import datetime

from spyne.test.interop._test_soap_client_base import server_started
from spyne.util import thread, urlencode, urlopen, Request, HTTPError


_server_started = False


class TestHttpRpc(unittest.TestCase):
    def setUp(self):
        global _server_started
        from spyne.test.interop.server.httprpc_pod_basic import main, port

        if not _server_started:
            def run_server():
                main()

            thread.start_new_thread(run_server, ())

            # FIXME: Does anybody have a better idea?
            time.sleep(2)

            _server_started = True

        self.base_url = 'http://localhost:%d' % port[0]

    def test_404(self):
        url = '%s/404' % self.base_url
        try:
            data = urlopen(url).read()
        except HTTPError as e:
            assert e.code == 404

    def test_413(self):
        url = self.base_url
        try:
            data = Request(url,("foo"*3*1024*1024))
        except HTTPError as e:
            assert e.code == 413

    def test_500(self):
        url = '%s/python_exception' % self.base_url
        try:
            data = urlopen(url).read()
        except HTTPError as e:
            assert e.code == 500

    def test_500_2(self):
        url = '%s/soap_exception' % self.base_url
        try:
            data = urlopen(url).read()
        except HTTPError as e:
            assert e.code == 500

    def test_echo_string(self):
        url = '%s/echo_string?s=punk' % self.base_url
        data = urlopen(url).read()

        assert data == b'punk'

    def test_echo_integer(self):
        url = '%s/echo_integer?i=444' % self.base_url
        data = urlopen(url).read()

        assert data == b'444'

    def test_echo_datetime(self):
        dt = datetime.now(pytz.utc).isoformat().encode('ascii')
        params = urlencode({
            'dt': dt,
        })

        print(params)
        url = '%s/echo_datetime?%s' % (self.base_url, str(params))
        data = urlopen(url).read()

        assert dt == data

    def test_echo_datetime_tz(self):
        dt = datetime.now(pytz.utc).isoformat().encode('ascii')
        params = urlencode({
            'dt': dt,
        })

        print(params)
        url = '%s/echo_datetime?%s' % (self.base_url, str(params))
        data = urlopen(url).read()

        assert dt == data


if __name__ == '__main__':
    unittest.main()
