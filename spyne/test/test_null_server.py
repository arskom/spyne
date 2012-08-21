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

from spyne.interface.wsdl import Wsdl11
from spyne.protocol.soap import Soap11

from spyne.model.primitive import String
from spyne.application import Application
from spyne.decorator import srpc
from spyne.service import ServiceBase
from spyne.server.null import NullServer

class TestNullServer(unittest.TestCase):
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

    def test_call(self):
        queue = set()

        class MessageService(ServiceBase):
            @srpc(String, String)
            def send_message(s, k):
                queue.add((s,k))

        application = Application([MessageService], 'some_tns',
            interface=Wsdl11(), in_protocol=Soap11(), out_protocol=Soap11())

        server = NullServer(application)

        queue.clear()
        server.service.send_message("zabaaa", k="hobaa")
        assert set([("zabaaa","hobaa")]) == queue

        queue.clear()
        server.service.send_message(k="hobaa")
        assert set([(None,"hobaa")]) == queue

        queue.clear()
        server.service.send_message("zobaaa", s="hobaa")
        assert set([("hobaa", None)]) == queue

if __name__ == '__main__':
    unittest.main()
