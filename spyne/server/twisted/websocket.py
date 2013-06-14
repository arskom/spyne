
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

"""The ``spyne.server.twisted`` module contains a server transport compatible
with the Twisted event loop. It uses the TwistedWebResource object as transport.

Also see the twisted examples in the examples directory of the source
distribution.

If you want to have a hard-coded URL in the wsdl document, this is how to do
it: ::

    resource = TwistedWebResource(...)
    resource.http_transport.doc.wsdl11.build_interface_document("http://example.com")

This is not strictly necessary -- if you don't do this, Spyne will get the
URL from the first request, build the wsdl on-the-fly and cache it as a
string in memory for later requests. However, if you want to make sure
you only have this url on the WSDL, this is how to do it. Note that if
your client takes the information in wsdl seriously, all requests will go
to the designated url above which can make testing a bit difficult. Use
in moderation.

This module is EXPERIMENTAL. Your mileage may vary. Patches are welcome.
"""


from __future__ import absolute_import

import logging
logger = logging.getLogger(__name__)

from inspect import isgenerator

from spyne.error import InternalError
from twisted.python.log import err
from twisted.internet.interfaces import IPullProducer
from twisted.internet.defer import Deferred
from twisted.internet.protocol import Factory
from twisted.web.iweb import UNKNOWN_LENGTH
from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET
from twisted.python import log

# FIXME: Switch to:
#    from twisted.web.websockets import WebSocketsProtocol
#    from twisted.web.websockets import WebSocketsResource
#    from twisted.web.websockets import CONTROLS

from spyne.util._twisted_ws import WebSocketsProtocol
from spyne.util._twisted_ws import WebSocketsResource
from spyne.util._twisted_ws import CONTROLS

from zope.interface import implements

from spyne import MethodContext
from spyne import TransportContext
from spyne.auxproc import process_contexts
from spyne.const.ansi_color import LIGHT_GREEN
from spyne.const.ansi_color import END_COLOR
from spyne.const.http import HTTP_404
from spyne.model import PushBase
from spyne.model.complex import ComplexModel
from spyne.model.fault import Fault
from spyne.server import ServerBase
from spyne.server.http import HttpBase
from spyne.server.http import HttpMethodContext


class WebSocketTransportContext(TransportContext):
    def __init__(self, transport, type, client_handle, parent):
        TransportContext.__init__(self, transport, type)

        self.client_handle = client_handle
        """TwistedWebSocketProtocol instance."""

        self.parent = parent
        """Parent Context"""


class WebSocketMethodContext(MethodContext):
    def __init__(self, transport, client_handle):
        MethodContext.__init__(self, transport)

        self.transport = WebSocketTransportContext(transport, 'ws',
                                                            client_handle, self)


class TwistedWebSocketProtocol(WebSocketsProtocol):
    """A protocol that parses and generates messages in a WebSocket stream."""

    def __init__(self, transport, bookkeep=False, _clients=None):
        self._spyne_transport = transport
        self._clients = _clients
        self.__app_id = id(self)
        if bookkeep:
            self.connectionMade = self._connectionMade
            self.connectionLost = self._connectionLost

    @property
    def app_id(self):
        return self.__app_id

    @app_id.setter
    def app_id(self, what):
        entry = self._clients.get(self.__app_id, None)

        if entry:
            del self._clients[old_id]
            self._clients[what] = entry

        self.__app_id = what

    def _connectionMade(self):
        WebSocketsProtocol.connectionMade(self)

        self._clients[self.app_id] = self

    def _connectionLost(self, reason):
        del self._clients[id(self)]


    def frameReceived(self, opcode, data, fin):
        tpt = self._spyne_transport

        initial_ctx = WebSocketMethodContext(tpt, client_handle=self)
        initial_ctx.in_string = [data]

        contexts = tpt.generate_contexts(initial_ctx)
        p_ctx, others = contexts[0], contexts[1:]

        if p_ctx.in_error:
            p_ctx.out_object = p_ctx.in_error

        else:
            tpt.get_in_object(p_ctx)

            if p_ctx.in_error:
                p_ctx.out_object = p_ctx.in_error

            else:
                tpt.get_out_object(p_ctx)
                if p_ctx.out_error:
                    p_ctx.out_object = p_ctx.out_error

        def _cb_deferred(retval, cb=True):
            if cb and len(p_ctx.descriptor.out_message._type_info) <= 1:
                p_ctx.out_object = [retval]
            else:
                p_ctx.out_object = retval

            tpt.get_out_string(p_ctx)
            self.sendFrame(opcode, ''.join(p_ctx.out_string), fin)
            p_ctx.close()
            process_contexts(tpt, others, p_ctx)

        def _eb_deferred(retval):
            p_ctx.out_error = retval.value
            if not issubclass(retval.type, Fault):
                retval.printTraceback()

            tpt.get_out_string(p_ctx)
            self.sendFrame(opcode, ''.join(p_ctx.out_string), fin)
            p_ctx.close()

        ret = p_ctx.out_object
        if isinstance(ret, (list, tuple)):
            ret = ret[0]

        if isinstance(ret, Deferred):
            ret.addCallback(_cb_deferred)
            ret.addErrback(_eb_deferred)

        elif isinstance(ret, PushBase):
            raise NotImplementedError()

        else:
            _cb_deferred(p_ctx.out_object, cb=False)


class TwistedWebSocketFactory(Factory):
    def __init__(self, app, bookkeep=False, _clients=None):
        self.app = app
        self.transport = ServerBase(app)
        self.bookkeep = bookkeep
        self._clients = _clients
        if _clients is None:
            self._clients = {}

    def buildProtocol(self, addr):
        return TwistedWebSocketProtocol(self.transport, self.bookkeep,
                                                                self._clients)

class _Fake(object):
    pass


def _FakeWrap(cls):
    class _Ret(ComplexModel):
        _type_info = {"ugh ": cls}

    return _Ret


class _FakeCtx(object):
    def __init__(self, obj, cls):
        self.out_object = obj
        self.out_error = None
        self.descriptor = _Fake()
        self.descriptor.out_message = cls


class InvalidRequestError(Exception):
    pass


class TwistedWebSocketResource(WebSocketsResource):
    def __init__(self, app, bookkeep=False, clients=None):
        self.app = app
        self.clients = clients
        if clients is None:
            self.clients = {}

        if bookkeep:
            self.propagate = self.do_propagate

        WebSocketsResource.__init__(self, TwistedWebSocketFactory(app,
                                                       bookkeep, self.clients))

    def propagate(self):
        raise InvalidRequestError("You must enable bookkeeping to have "
                                  "message propagation work.")

    def get_doc(self, obj, cls=None):
        if cls is None:
            cls = obj.__class__

        op = self.app.out_protocol
        ctx = _FakeCtx(obj, cls)
        op.serialize(ctx, op.RESPONSE)
        op.create_out_string(ctx)

        return ''.join(ctx.out_string)

    def do_propagate(self, obj, cls=None):
        doc = self.get_doc(obj, cls)

        for c in self.clients.itervalues():
            print 'sending to', c
            c.sendFrame(CONTROLS.TEXT, doc, True)
