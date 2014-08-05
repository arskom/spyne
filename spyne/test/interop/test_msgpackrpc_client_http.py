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

from spyne.client.http import HttpClient
from spyne.test.interop._test_soap_client_base import SpyneClientTestBase
from spyne.test.interop.server.msgpackrpc_http_basic import msgpackrpc_application
from spyne.util.etreeconv import root_dict_to_etree

class TestSpyneHttpClient(SpyneClientTestBase, unittest.TestCase):
    def setUp(self):
        SpyneClientTestBase.setUp(self, 'msgpack_rpc_http')

        self.client = HttpClient('http://localhost:9754/', msgpackrpc_application)
        self.ns = "spyne.test.interop.server"

    @unittest.skip("MessagePackRpc does not support header")
    def test_echo_in_header(self):
        pass

    @unittest.skip("MessagePackRpc does not support header")
    def test_send_out_header(self):
        pass


if __name__ == '__main__':
    unittest.main()
