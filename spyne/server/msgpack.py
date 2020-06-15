# encoding: utf8
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

from __future__ import absolute_import

import logging
logger = logging.getLogger(__name__)

import msgpack

from mmap import mmap
from collections import OrderedDict

from spyne import MethodContext, TransportContext, Address
from spyne.auxproc import process_contexts
from spyne.error import ValidationError, InternalError
from spyne.server import ServerBase
from spyne.util.six import binary_type

try:
    from twisted.internet.defer import Deferred
except ImportError as e:
    def Deferred(*_, **__): raise e


MSGPACK_SHELL_OVERHEAD = 10


def _process_v1_msg(prot, msg):
    header = None
    body = msg[1]
    if not isinstance(body, (binary_type, mmap, memoryview)):
        raise ValidationError(body, "Body must be a bytestream.")

    if len(msg) > 2:
        header = msg[2]
        if not isinstance(header, dict):
            raise ValidationError(header, "Header must be a dict.")
        for k, v in header.items():
            header[k] = msgpack.unpackb(v)

    ctx = MessagePackMethodContext(prot, MessagePackMethodContext.SERVER)
    ctx.in_string = [body]
    ctx.transport.in_header = header

    return ctx


class MessagePackTransportContext(TransportContext):
    def __init__(self, parent, transport):
        super(MessagePackTransportContext, self).__init__(parent, transport)

        self.in_header = None
        self.protocol = None
        self.inreq_queue = OrderedDict()
        self.request_len = None

    def get_peer(self):
        if self.protocol is not None:
            peer = self.protocol.transport.getPeer()
            return Address.from_twisted_address(peer)


class MessagePackOobMethodContext(object):
    __slots__ = 'd'

    def __init__(self):
        if Deferred is not None:
            self.d = Deferred()
        else:
            self.d = None

    def close(self):
        if self.d is not None and not self.d.called:
            self.d.cancel()


class MessagePackMethodContext(MethodContext):
    TransportContext = MessagePackTransportContext

    def __init__(self, transport, way):
        self.oob_ctx = None

        super(MessagePackMethodContext, self).__init__(transport, way)

    def close(self):
        super(MessagePackMethodContext, self).close()
        if self.transport is not None:
            self.transport.protocol = None
            self.transport = None

        if self.oob_ctx is not None:
            self.oob_ctx.close()


class MessagePackTransportBase(ServerBase):
    # These are all placeholders that need to be overridden in subclasses
    OUT_RESPONSE_NO_ERROR = None
    OUT_RESPONSE_CLIENT_ERROR = None
    OUT_RESPONSE_SERVER_ERROR = None

    IN_REQUEST = None

    def __init__(self, app):
        super(MessagePackTransportBase, self).__init__(app)

        self._version_map = {
            self.IN_REQUEST: _process_v1_msg
        }

    def produce_contexts(self, msg):
        """Produce contexts based on incoming message.

        :param msg: Parsed request in this format: `[IN_REQUEST, body, header]`
        """

        if not isinstance(msg, (list, tuple)):
            logger.debug("Incoming request: %r", msg)
            raise ValidationError(msg, "Request must be a list")

        if not len(msg) >= 2:
            logger.debug("Incoming request: %r", msg)
            raise ValidationError(len(msg), "Request must have at least two "
                                                          "elements. It has %r")

        if not isinstance(msg[0], int):
            logger.debug("Incoming request: %r", msg)
            raise ValidationError(msg[0], "Request version must be an integer. "
                                                                    "It was %r")

        processor = self._version_map.get(msg[0], None)
        if processor is None:
            logger.debug("Invalid incoming request: %r", msg)
            raise ValidationError(msg[0], "Unknown request type %r")

        msglen = len(msg[1])
        # shellen = len(msgpack.packb(msg))
        # logger.debug("Shell size: %d, message size: %d, diff: %d",
        #                                     shellen, msglen, shellen - msglen)
        # some approx. msgpack overhead based on observations of what's above.
        msglen += MSGPACK_SHELL_OVERHEAD

        initial_ctx = processor(self, msg)
        contexts = self.generate_contexts(initial_ctx)

        p_ctx, others = contexts[0], contexts[1:]
        p_ctx.transport.request_len = msglen

        return p_ctx, others

    def process_contexts(self, contexts):
        p_ctx, others = contexts[0], contexts[1:]

        if p_ctx.in_error:
            return self.handle_error(p_ctx, others, p_ctx.in_error)

        self.get_in_object(p_ctx)
        if p_ctx.in_error:
            logger.error(p_ctx.in_error)
            return self.handle_error(p_ctx, others, p_ctx.in_error)

        self.get_out_object(p_ctx)
        if p_ctx.out_error:
            return self.handle_error(p_ctx, others, p_ctx.out_error)

        try:
            self.get_out_string(p_ctx)

        except Exception as e:
            logger.exception(e)
            contexts.out_error = InternalError("Serialization Error.")
            return self.handle_error(contexts, others, contexts.out_error)

    def handle_error(self, p_ctx, others, error):
        self.get_out_string(p_ctx)

        try:
            process_contexts(self, others, p_ctx, error=error)
        except Exception as e:
            # Report but ignore any exceptions from auxiliary methods.
            logger.exception(e)

    def handle_transport_error(self, error):
        return msgpack.dumps(str(error))

    def pack(self, ctx):
        ctx.out_string = msgpack.packb([self.OUT_RESPONSE_NO_ERROR,
                                                     b''.join(ctx.out_string)]),


class MessagePackServerBase(MessagePackTransportBase):
    """Contains the transport protocol logic but not the transport itself.

    Subclasses should implement logic to move bitstreams in and out of this
    class."""

    OUT_RESPONSE_NO_ERROR = 0
    OUT_RESPONSE_CLIENT_ERROR = 1
    OUT_RESPONSE_SERVER_ERROR = 2

    IN_REQUEST = 1
