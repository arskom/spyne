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

from spyne import MethodContext, TransportContext
from spyne.auxproc import process_contexts
from spyne.error import ValidationError
from spyne.model import Fault
from spyne.server import ServerBase


OUT_RESPONSE_NO_ERROR = 0
OUT_RESPONSE_CLIENT_ERROR = 1
OUT_RESPONSE_SERVER_ERROR = 2

IN_REQUEST = 1

def _process_v1_msg(prot, msg):
    header = None
    body = msg[1]
    if not isinstance(body, basestring):
        raise ValidationError(body, "Body must be a bytestream.")

    if len(msg) > 2:
        header = msg[2]
        if not isinstance(header, dict):
            raise ValidationError(header, "Header must be a dict.")
        for k,v in header.items():
            header[k] = msgpack.unpackb(v)

    ctx = MessagePackMethodContext(prot)
    ctx.in_string = [body]
    ctx.transport.in_header = header

    return ctx


class MessagePackTransportContext(TransportContext):
    def __init__(self, parent, transport):
        super(MessagePackTransportContext, self).__init__(parent, transport)

        self.in_header = None
        self.protocol = None


class MessagePackMethodContext(MethodContext):
    def __init__(self, transport):
        super(MessagePackMethodContext, self).__init__(transport)

        self.transport = MessagePackTransportContext(self, transport)


class MessagePackServerBase(ServerBase):
    """Contains the transport protocol logic but not the transport itself.

    Subclasses should implement logic to move bitstreams in and out of this
    class."""

    def __init__(self, app):
        super(MessagePackServerBase, self).__init__(app)

        self._version_map = {
            IN_REQUEST: _process_v1_msg
        }

    def produce_contexts(self, msg):
        """msg = [IN_REQUEST, body, header]"""

        logger.debug("Request object: %r", msg)

        if not isinstance(msg, list):
            raise ValidationError("Request must be a list")

        if not len(msg) >= 2:
            raise ValidationError("Request must have at least two elements.")

        if not isinstance(msg[0], int):
            raise ValidationError("Request version must be an integer.")

        processor = self._version_map.get(msg[0], None)
        if processor is None:
            raise ValidationError("Unknown request version")

        initial_ctx = processor(self, msg)
        contexts = self.generate_contexts(initial_ctx)

        return contexts[0], contexts[1:]

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
            contexts.out_error = Fault('Server', "Internal serialization Error.")
            return self.handle_error(contexts, others, contexts.out_error)

    def handle_error(self, p_ctx, others, error):
        self.get_out_string(p_ctx)

        try:
            process_contexts(self, others, p_ctx, error=error)
        except Exception as e:
            # Report but ignore any exceptions from auxiliary methods.
            logger.exception(e)

    def handle_transport_error(self, error):
        return msgpack.pack(str(error))

    def pack(self, ctx):
        ctx.out_string = msgpack.packb({OUT_RESPONSE_NO_ERROR: ''.join(ctx.out_string)}),
