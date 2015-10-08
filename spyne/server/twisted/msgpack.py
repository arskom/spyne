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
from collections import deque
from itertools import chain

from twisted.python import log
from twisted.internet import reactor
from twisted.internet.task import deferLater
from twisted.internet.defer import Deferred, CancelledError
from twisted.internet.protocol import Protocol, Factory, connectionDone, \
    ClientFactory
from twisted.python.failure import Failure

from spyne import EventManager, Address, ServerBase
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
        assert isinstance(tpt, ServerBase), \
                                        "%r is not a ServerBase instance" % tpt

        self.tpt = tpt
        self.max_buffer_size = max_buffer_size
        self.event_manager = EventManager(self)

    def buildProtocol(self, address):
        return TwistedMessagePackProtocol(self.tpt,
                             max_buffer_size=self.max_buffer_size, factory=self)


def _cha(*args):
    return args


IDLE_TIMEOUT = 'idle timeout'


class TwistedMessagePackProtocol(Protocol):
    IDLE_TIMEOUT_SEC = 0

    def __init__(self, tpt, max_buffer_size=2 * 1024 * 1024, out_chunk_size=0,
                                           out_chunk_delay_sec=1, factory=None):
        """Twisted protocol implementation for Spyne's MessagePack transport.

        :param tpt: Spyne transport.
        :param max_buffer_size: Max. encoded message size.
        :param out_chunk_size: Split
        :param factory: Twisted protocol factory
        """

        from spyne.server.msgpack import MessagePackTransportBase
        assert isinstance(tpt, MessagePackTransportBase)

        self.factory = factory
        self._buffer = msgpack.Unpacker(max_buffer_size=max_buffer_size)
        self.spyne_tpt = tpt

        self.sessid = ''
        self.sent_bytes = 0
        self.recv_bytes = 0
        self.out_chunks = deque()
        self.out_chunk_size = out_chunk_size
        self.out_chunk_delay_sec = out_chunk_delay_sec
        self._delaying = None
        self.idle_timer = None
        self.disconnecting = False  # FIXME: should we use this to raise an
                                    # invalid connection state exception ?

    @staticmethod
    def gen_chunks(l, n):
        """Yield successive n-sized chunks from l."""
        for i in range(0, len(l), n):
            yield l[i:i+n]

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
        self._reset_idle_timer()
        if self.factory is not None:
            self.factory.event_manager.fire_event("connection_made", self)

    def connectionLost(self, reason=connectionDone):
        self.disconnecting = False
        if self.factory is not None:
            self.factory.event_manager.fire_event("connection_lost", self)
        if self.idle_timer is not None:
            self.idle_timer.cancel()

    def dataReceived(self, data):
        self._buffer.feed(data)
        self.recv_bytes += len(data)

        self._reset_idle_timer()

        for msg in self._buffer:
            self.process_incoming_message(msg)

    def _reset_idle_timer(self):
        if self.idle_timer is not None:
            self.idle_timer.cancel()

        if self.IDLE_TIMEOUT_SEC > 0:
            self.idle_timer = deferLater(reactor, self.IDLE_TIMEOUT_SEC,
                                          self.loseConnection, IDLE_TIMEOUT) \
                .addErrback(self._err_idle_cancelled)

    def _err_idle_cancelled(self, err):
        err.trap(CancelledError)

        # do nothing.

    def loseConnection(self, reason=None):
        self.disconnecting = True
        self.idle_timer = None
        logger.debug("Aborting connection because %s", reason)
        self.transport.abortConnection()

    def process_incoming_message(self, msg):
        p_ctx, others = self.spyne_tpt.produce_contexts(msg)
        p_ctx.transport.remote_addr = Address.from_twisted_address(
                                                       self.transport.getPeer())
        p_ctx.transport.protocol = self
        p_ctx.transport.sessid = self.sessid

        self.process_contexts(p_ctx, others)

    def transport_write(self, data):
        if self.out_chunk_size == 0:
            self.transport.write(data)
            self.sent_bytes += len(data)

        else:
            self.out_chunks.append(self.gen_chunks(data, self.out_chunk_size))
            self._write_single_chunk()

    def _wait_for_next_chunk(self):
        return deferLater(reactor, self.out_chunk_delay_sec,
                                                       self._write_single_chunk)

    def _write_single_chunk(self):
        try:
            chunk = chain(*self.out_chunks).next()
        except StopIteration:
            chunk = None
            self.out_chunks.clear()

        if chunk is None:
            self._delaying = None

            logger.debug("%s no more chunks...", self.sessid)

        else:
            self.transport.write(chunk)
            self.sent_bytes += len(chunk)

            self._delaying = self._wait_for_next_chunk()

            logger.debug("%s One chunk of %d bytes written. "
                           "Waiting for next chunk...", self.sessid, len(chunk))

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
            ret.addCallbacks(_cb_deferred, _eb_deferred,
                             [self, p_ctx, others], {},
                             [self, p_ctx, others], {})
            ret.addErrback(log.err)

        else:
            _cb_deferred(p_ctx.out_object, self, p_ctx, others, nowrap=True)


def _eb_deferred(fail, prot, p_ctx, others):
    p_ctx.out_error = fail.value
    tb = None

    if isinstance(fail, Failure):
        tb = fail.getTracebackObject()
        fail.printTraceback()
        p_ctx.out_error = InternalError(fail.value)

    prot.handle_error(p_ctx, others, p_ctx.out_error)

    data_len = 0
    for data in p_ctx.out_string:
        prot.transport_write(data)
        data_len += len(data)

    p_ctx.transport.resp_length = data_len

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
