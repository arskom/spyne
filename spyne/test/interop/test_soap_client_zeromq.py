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

from spyne.client.zeromq import ZeroMQClient

from spyne.test.interop._test_soap_client_base import SpyneClientTestBase
from spyne.test.interop.server.soap11.soap_http_basic import soap11_application


class TestSpyneZmqClient(SpyneClientTestBase, unittest.TestCase):
    def setUp(self):
        SpyneClientTestBase.setUp(self, 'zeromq')

        self.client = ZeroMQClient('tcp://localhost:55555', soap11_application)
        self.ns = "spyne.test.interop.server._service"

if __name__ == '__main__':
    unittest.main()
