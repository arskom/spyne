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

from rpclib.client.http import HttpClient
from rpclib.test.interop._test_client_base import RpclibClientTestBase
from rpclib.test.interop.server.soap_http_basic import soap_application
from rpclib.util.etreeconv import root_dict_to_etree

class TestRpclibHttpClient(RpclibClientTestBase, unittest.TestCase):
    def setUp(self):
        self.client = HttpClient('http://localhost:9753/', soap_application)
        self.ns = "rpclib.test.interop.server._service"

    def test_any(self):
        val = root_dict_to_etree(self._get_xml_test_val())
        ret = self.client.service.echo_any(val)

        self.assertEquals(ret, val)

if __name__ == '__main__':
    unittest.main()
