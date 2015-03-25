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

from time import time
from hashlib import md5

from twisted.internet.defer import Deferred
from twisted.internet.protocol import Protocol, Factory, connectionDone, \
    ClientFactory
from twisted.python.failure import Failure
from twisted.python import log

from spyne import EventManager, Address, ServerBase, Application
from spyne.auxproc import process_contexts
from spyne.error import InternalError


class TwistedMessagePackProtocolFactory(Factory):
    def __init__(self, tpt):
        assert isinstance(tpt, ServerBase)

        self.tpt = tpt
        self.event_manager = EventManager(self)

    def buildProtocol(self, address):
        return TwistedMessagePackProtocol(self.tpt, factory=self)


TwistedMessagePackProtocolServerFactory = TwistedMessagePackProtocolFactory


class TwistedMessagePackProtocolClientFactory(ClientFactory):
    def __init__(self, tpt, max_buffer_size=2 * 1024 * 1024):
        assert isinstance(tpt, ServerBase)

        self.tpt = tpt
        self.max_buffer_size = max_buffer_size
        self.event_manager = EventManager(self)

    def buildProtocol(self, address):
        return TwistedMessagePackProtocol(self.tpt,
                             max_buffer_size=self.max_buffer_size, factory=self)


def _cha(*args): return args


class TwistedMessagePackProtocol(Protocol):
    def __init__(self, tpt, max_buffer_size=2 * 1024 * 1024, factory=None):
        assert isinstance(tpt, ServerBase)

        self.factory = factory
        self._buffer = msgpack.Unpacker(max_buffer_size=max_buffer_size)
        self.spyne_tpt = tpt

        self.sessid = ''
        self.sent_bytes = 0
        self.recv_bytes = 0

    def gen_sessid(self, *args):
        """It's up to you to use this in a subclass."""

        retval = _cha(
            Address.from_twisted_address(self.transport.getPeer()),
            time(),
            *args
        )

        return md5(repr(retval)).hexdigest()

    def connectionMade(self):
        self.sent_bytes = 0
        self.recv_bytes = 0
        if self.factory is not None:
            self.factory.event_manager.fire_event("connection_made", self)

    def connectionLost(self, reason=connectionDone):
        if self.factory is not None:
            self.factory.event_manager.fire_event("connection_lost", self)

    def dataReceived(self, data):
        self._buffer.feed(data)
        self.recv_bytes += len(data)

        for msg in self._buffer:
            self.process_incoming_message(msg)

    def process_incoming_message(self, msg):
        p_ctx, others = self.spyne_tpt.produce_contexts(msg)
        p_ctx.transport.remote_addr = Address.from_twisted_address(
                                                       self.transport.getPeer())
        p_ctx.transport.protocol = self
        p_ctx.transport.sessid = self.sessid

        self.process_contexts(p_ctx, others)

    def transport_write(self, data):
        self.sent_bytes += len(data)
        self.transport.write(data)

    def handle_error(self, p_ctx, others, exc):
        self.spyne_tpt.get_out_string(p_ctx)

        if isinstance(exc, InternalError):
            error = self.spyne_tpt.OUT_RESPONSE_SERVER_ERROR
        else:
            error = self.spyne_tpt.OUT_RESPONSE_CLIENT_ERROR

        data = p_ctx.out_document[0]
        if isinstance(data, dict):
            data = data.values()
        out_string = msgpack.packb([
            error, msgpack.packb(data),
        ])
        self.transport_write(out_string)
        p_ctx.transport.resp_length = len(out_string)
        p_ctx.close()

        try:
            process_contexts(self, others, p_ctx, error=error)
        except Exception as e:
            # Report but ignore any exceptions from auxiliary methods.
            logger.exception(e)

    def process_contexts(self, p_ctx, others):
        if p_ctx.in_error:
            self.handle_error(p_ctx, others, p_ctx.in_error)
            return

        self.spyne_tpt.get_in_object(p_ctx)
        if p_ctx.in_error:
            logger.error(p_ctx.in_error)
            self.handle_error(p_ctx, others, p_ctx.in_error)
            return

        self.spyne_tpt.get_out_object(p_ctx)
        if p_ctx.out_error:
            self.handle_error(p_ctx, others, p_ctx.out_error)
            return

        if len(p_ctx.descriptor.out_message._type_info) > 1:
            ret = p_ctx.out_object
        else:
            ret = p_ctx.out_object[0]

        if isinstance(ret, Deferred):
            ret.addCallback(_cb_deferred, self, p_ctx, others)
            ret.addErrback(_eb_deferred, self, p_ctx, others)
            ret.addErrback(log.err)

        else:
            _cb_deferred(p_ctx.out_object, self, p_ctx, others, nowrap=True)


def _eb_deferred(retval, prot, p_ctx, others):
    p_ctx.out_error = retval.value
    tb = None

    if isinstance(retval, Failure):
        tb = retval.getTracebackObject()
        retval.printTraceback()
        p_ctx.out_error = InternalError(retval.value)

    prot.handle_error(p_ctx, others, p_ctx.out_error)
    prot.transport_write(''.join(p_ctx.out_string))
    p_ctx.transport.resp_length = len(p_ctx.out_string)
    prot.transport.loseConnection()

    return Failure(p_ctx.out_error, p_ctx.out_error.__class__, tb)


def _cb_deferred(ret, prot, p_ctx, others, nowrap=False):
    if len(p_ctx.descriptor.out_message._type_info) > 1 or nowrap:
        p_ctx.out_object = ret
    else:
        p_ctx.out_object = [ret]

    try:
        prot.spyne_tpt.get_out_string(p_ctx)
        prot.spyne_tpt.pack(p_ctx)

        out_string = ''.join(p_ctx.out_string)
        prot.transport_write(out_string)
        p_ctx.transport.resp_length = len(out_string)

    except Exception as e:
        logger.exception(e)
        prot.handle_error(p_ctx, others, InternalError(e))

    finally:
        p_ctx.close()

    process_contexts(prot.spyne_tpt, others, p_ctx)
