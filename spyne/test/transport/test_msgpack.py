
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

import msgpack

from spyne import Application, ServiceBase, rpc
from spyne.model import Unicode
from spyne.protocol.msgpack import MessagePackDocument

from twisted.trial import  unittest


class TestMessagePackServer(unittest.TestCase):
     def gen_prot(self, app):
        from spyne.server.twisted.msgpack import TwistedMessagePackProtocol
        from twisted.test.proto_helpers import StringTransportWithDisconnection
        from spyne.server.msgpack import MessagePackServerBase

        prot = TwistedMessagePackProtocol(MessagePackServerBase(app))
        transport = StringTransportWithDisconnection()
        prot.makeConnection(transport)
        transport.protocol = prot

        return prot

     def test_roundtrip(self):
        v = "yaaay!"
        class SomeService(ServiceBase):
            @rpc(Unicode, _returns=Unicode)
            def yay(ctx, u):
                return u

        app = Application([SomeService], 'tns',
                                in_protocol=MessagePackDocument(),
                                out_protocol=MessagePackDocument())

        prot = self.gen_prot(app)
        request = msgpack.packb({'yay': [v]})
        prot.dataReceived(msgpack.packb([1, request]))
        val = prot.transport.value()
        print repr(val)
        val = msgpack.unpackb(val)
        print repr(val)

        self.assertEquals(val, [0, msgpack.packb(v)])

     def test_roundtrip_deferred(self):
        from twisted.internet import reactor
        from twisted.internet.task import deferLater

        v = "yaaay!"
        p_ctx = []
        class SomeService(ServiceBase):
            @rpc(Unicode, _returns=Unicode)
            def yay(ctx, u):
                def _cb():
                    return u
                p_ctx.append(ctx)
                return deferLater(reactor, 0.1, _cb)

        app = Application([SomeService], 'tns',
                                in_protocol=MessagePackDocument(),
                                out_protocol=MessagePackDocument())

        prot = self.gen_prot(app)
        request = msgpack.packb({'yay': [v]})
        def _ccb(_):
            val = prot.transport.value()
            print repr(val)
            val = msgpack.unpackb(val)
            print repr(val)

            self.assertEquals(val, [0, msgpack.packb(v)])

        prot.dataReceived(msgpack.packb([1, request]))

        return p_ctx[0].out_object[0].addCallback(_ccb)

