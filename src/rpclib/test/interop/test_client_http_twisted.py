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

from twisted.trial import unittest

from rpclib.client.twisted_ import TwistedHttpClient
from rpclib.test.interop.server.soap_http_basic import soap_application

from twisted.internet import reactor

class TestRpclibHttpClient(unittest.TestCase):
    def setUp(self):
        self.ns = "rpclib.test.interop.server._service"
        self.client = TwistedHttpClient('http://localhost:9753/', soap_application)

    def test_echo_boolean(self):
        error = None

        def eb(ret):
            raise ret

        def cb(ret):
            assert ret == True

        return self.client.service.echo_boolean(True).addCallbacks(cb, eb)
