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
from rpclib.test.interop._test_soap_client_base import run_server

from rpclib.client.twisted import TwistedHttpClient
from rpclib.test.interop.server.soap_http_basic import soap_application

class TestRpclibHttpClient(unittest.TestCase):
    def setUp(self):
        run_server('http')

        self.ns = "rpclib.test.interop.server._service"
        self.client = TwistedHttpClient('http://localhost:9754/', soap_application)

    def test_echo_boolean(self):
        def eb(ret):
            raise ret

        def cb(ret):
            assert ret == True

        return self.client.service.echo_boolean(True).addCallbacks(cb, eb)

    def test_python_exception(self):
        def eb(ret):
            print(ret)

        def cb(ret):
            assert False, "must fail: %r" % ret

        return self.client.service.python_exception().addCallbacks(cb, eb)

    def test_soap_exception(self):
        def eb(ret):
            print(type(ret))

        def cb(ret):
            assert False, "must fail: %r" % ret

        return self.client.service.soap_exception().addCallbacks(cb, eb)

    def test_documented_exception(self):
        def eb(ret):
            print(ret)

        def cb(ret):
            assert False, "must fail: %r" % ret

        return self.client.service.python_exception().addCallbacks(cb, eb)
