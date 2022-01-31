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

import gc
import unittest

from lxml import etree

from spyne import Ignored
from spyne import const
from spyne.interface.wsdl import Wsdl11
from spyne.protocol.xml import XmlDocument

from spyne.model.complex import Array
from spyne.model.primitive import Boolean
from spyne.model.primitive import String
from spyne.application import Application
from spyne.decorator import srpc
from spyne.service import Service
from spyne.server.null import NullServer

class TestNullServer(unittest.TestCase):
    def test_empty_return_type(self):
        class MessageService(Service):
            @srpc(String)
            def send_message(s):
                return s

        application = Application([MessageService], 'some_tns',
                          in_protocol=XmlDocument(), out_protocol=XmlDocument())

        assert None == NullServer(application).service.send_message("zabaaa")

    def test_ignored(self):
        class MessageService(Service):
            @srpc(String, _returns=String)
            def send_message_1(s):
                return Ignored("xyz")

            @srpc(String)
            def send_message_2(s):
                return Ignored("xyz")

            @srpc(String, _returns=String)
            def send_message_3(s):
                return "OK"

        application = Application([MessageService], 'some_tns',
                          in_protocol=XmlDocument(), out_protocol=XmlDocument())

        server = NullServer(application)
        assert Ignored("xyz") == server.service.send_message_1("zabaaa")
        assert Ignored("xyz") == server.service.send_message_2("zabaaa")
        assert "OK" == server.service.send_message_3("zabaaa")

    def test_call_one_arg(self):
        queue = set()

        class MessageService(Service):
            @srpc(String)
            def send_message(s):
                queue.add(s)

        application = Application([MessageService], 'some_tns',
                          in_protocol=XmlDocument(), out_protocol=XmlDocument())

        server = NullServer(application)
        server.service.send_message("zabaaa")

        assert set(["zabaaa"]) == queue

    def test_call_two_args(self):
        queue = set()

        class MessageService(Service):
            @srpc(String, String)
            def send_message(s, k):
                queue.add((s,k))

        application = Application([MessageService], 'some_tns',
                          in_protocol=XmlDocument(), out_protocol=XmlDocument())

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

    def test_ostr(self):
        queue = set()

        class MessageService(Service):
            @srpc(String, String, _returns=Array(String))
            def send_message(s, k):
                queue.add((s, k))
                return [s, k]

        application = Application([MessageService], 'some_tns',
                        in_protocol=XmlDocument(), out_protocol=XmlDocument())

        ostr_server = NullServer(application, ostr=True)

        queue.clear()
        ret = ostr_server.service.send_message("zabaaa", k="hobaa")
        assert set([("zabaaa","hobaa")]) == queue
        assert etree.fromstring(b''.join(ret)).xpath('//tns:string/text()',
                 namespaces=application.interface.nsmap) == ['zabaaa', 'hobaa']

        queue.clear()
        ostr_server.service.send_message(k="hobaa")
        assert set([(None,"hobaa")]) == queue

        queue.clear()
        ostr_server.service.send_message("zobaaa", s="hobaa")
        assert set([("hobaa", None)]) == queue

    def test_no_gc_collect(self):
        class PingService(Service):
            @srpc(_returns=Boolean)
            def ping():
                return True

        application = Application(
            [PingService], 'some_tns',
            in_protocol=XmlDocument(), out_protocol=XmlDocument())

        server = NullServer(application)
        origin_collect = gc.collect
        origin_MIN_GC_INTERVAL = const.MIN_GC_INTERVAL
        try:
            gc.collect = lambda : 1/0
            with self.assertRaises(ZeroDivisionError):
                const.MIN_GC_INTERVAL = 0
                server.service.ping()
            # No raise
            const.MIN_GC_INTERVAL = float('inf')
            server.service.ping()
        finally:
            gc.collect = origin_collect
            const.MIN_GC_INTERVAL = origin_MIN_GC_INTERVAL


if __name__ == '__main__':
    unittest.main()
