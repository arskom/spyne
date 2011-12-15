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

from rpclib.interface.wsdl import Wsdl11
from rpclib.protocol.soap import Soap11

from rpclib.model.primitive import String
from rpclib.application import Application
from rpclib.decorator import srpc
from rpclib.service import ServiceBase
from rpclib.server.null import NullServer

class TestNullServer(unittest.TestCase):
    def test_fanout(self):
        arr = set()

        class MessageService1(ServiceBase):
            @srpc()
            def send_message():
                arr.add(1)

        class MessageService2(ServiceBase):
            @srpc()
            def send_message():
                arr.add(2)

        application = Application([MessageService1,MessageService2], 'some_tns',
            interface=Wsdl11(), in_protocol=Soap11(), out_protocol=Soap11(),
            supports_fanout_methods=True)

        server = NullServer(application)
        server.service.send_message()

        assert set([1,2]) == arr

    def test_call(self):
        queue = set()

        class MessageService(ServiceBase):
            @srpc(String)
            def send_message(s):
                queue.add(s)

        application = Application([MessageService], 'some_tns',
            interface=Wsdl11(), in_protocol=Soap11(), out_protocol=Soap11())

        server = NullServer(application)
        server.service.send_message("zabaaa")

        assert set(["zabaaa"]) == queue

if __name__ == '__main__':
    unittest.main()
