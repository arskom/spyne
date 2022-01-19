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

import io

import msgpack

from time import time
from hashlib import md5
from collections import deque, OrderedDict
from itertools import chain

from twisted.internet import reactor
from twisted.internet.task import deferLater
from twisted.internet.defer import Deferred, CancelledError
from twisted.internet.protocol import Protocol, Factory, connectionDone, \
    ClientFactory
from twisted.python.failure import Failure

from spyne import EventManager, Address, ServerBase, Fault
from spyne.auxproc import process_contexts
from spyne.error import InternalError
from spyne.server.twisted import log_and_let_go


class TwistedMessagePackProtocolFactory(Factory):
    IDLE_TIMEOUT_SEC = None

    def __init__(self, tpt):
        assert isinstance(tpt, ServerBase)

        self.tpt = tpt
        self.event_manager = EventManager(self)

    def buildProtocol(self, address):
        retval = TwistedMessagePackProtocol(self.tpt, factory=self)

        if self.IDLE_TIMEOUT_SEC is not None:
            retval.IDLE_TIMEOUT_SEC = self.IDLE_TIMEOUT_SEC

        return retval

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


class TwistedMessagePackProtocol(Protocol):
    IDLE_TIMEOUT_SEC = 0
    IDLE_TIMEOUT_MSG = 'idle timeout'
    MAX_INACTIVE_CONTEXTS = float('inf')

    def __init__(self, tpt, max_buffer_size=2 * 1024 * 1024, out_chunk_size=0,
                      out_chunk_delay_sec=1, max_in_queue_size=0, factory=None):
        """Twisted protocol implementation for Spyne's MessagePack transport.

        :param tpt: Spyne transport. It's an app-wide instance.
        :param max_buffer_size: Max. encoded message size.
        :param out_chunk_size: Split
        :param factory: Twisted protocol factory

        Supported events:
            * ``outresp_flushed(ctx, ctxid, data)``
                Called right after response data is flushed to the socket.
                    * ctx: Always None
                    * ctxid: Integer equal to ``id(ctx)``
                    * data: Flushed bytes object

        """

        from spyne.server.msgpack import MessagePackTransportBase
        assert isinstance(tpt, MessagePackTransportBase), \
            "Expected {!r} got {!r}".format(MessagePackTransportBase, type(tpt))

        self.spyne_tpt = tpt
        self._buffer = msgpack.Unpacker(raw=True,
                                                max_buffer_size=max_buffer_size)
        self.out_chunk_size = out_chunk_size
        self.out_chunk_delay_sec = out_chunk_delay_sec
        self.max_in_queue_size = max_in_queue_size
        self.factory = factory

        self.sessid = ''
        self._delaying = None
        self.sent_bytes = 0
        self.recv_bytes = 0
        self.idle_timer = None
        self.out_chunks = deque()
        self.inreq_queue = OrderedDict()
        self.inactive_queue = deque()
        self.disconnecting = False  # FIXME: should we use this to raise an
                                    # invalid connection state exception ?

    @staticmethod
    def gen_chunks(l, n):
        """Yield successive n-sized chunks from l."""
        if isinstance(l, io.BufferedIOBase):
            while True:
                data = l.read(n)
                if not data:
                    break
                yield data
            l.close()

        else:
            for i in range(0, len(l), n):
                yield l[i:i+n]

    def gen_sessid(self, *args):
        """It's up to you to use this in a subclass."""

        retval = _cha(
            Address.from_twisted_address(self.transport.getPeer()),
            time(),
            *args
        )

        return md5(repr(retval).encode('utf8')).hexdigest()

    def connectionMade(self):
        logger.debug("%08x connection made", id(self))
        self.sessid = ''
        self._delaying = None
        self.sent_bytes = 0
        self.recv_bytes = 0
        self.idle_timer = None
        self.out_chunks = deque()
        self.inreq_queue = OrderedDict()
        self.inactive_queue = deque()
        self.active_queue = dict()
        self.disconnecting = False  # FIXME: should we use this to raise an
                                    # invalid connection state exception ?

        self._reset_idle_timer()
        if self.factory is not None:
            self.factory.event_manager.fire_event("connection_made", self)

    def connectionLost(self, reason=connectionDone):
        if reason is connectionDone:
            logger.debug("%08x connection done", id(self))
        else:
            logger.debug("%08x connection lost: %s", id(self), reason)
        self.disconnecting = False
        if self.factory is not None:
            self.factory.event_manager.fire_event("connection_lost", self)
        self._cancel_idle_timer()

    def _cancel_idle_timer(self):
        if self.idle_timer is not None:
            if not self.idle_timer.called:
                # FIXME: Workaround for a bug in Twisted 18.9.0 when
                #        DelayedCall.debug == True
                try:
                    self.idle_timer.cancel()
                except AttributeError:
                    del self.idle_timer.func
                    del self.idle_timer.args
                    del self.idle_timer.kw

            self.idle_timer = None

    def dataReceived(self, data):
        self._buffer.feed(data)
        self.recv_bytes += len(data)

        self._reset_idle_timer()

        for msg in self._buffer:
            try:
                self.process_incoming_message(msg)
            except Exception as e:
                # If you get this error, you are in serious trouble
                # This needs to be fixed ASAP
                logger.error(
                           "Error %r while processing incoming data %r", e, msg)
                raise

            if self.disconnecting:
                return

    def _reset_idle_timer(self):
        if self.idle_timer is not None:
            t = self.idle_timer
            self.idle_timer = None
            if not t.called:
                t.cancel()

        if self.IDLE_TIMEOUT_SEC is not None and self.IDLE_TIMEOUT_SEC > 0:
            self.idle_timer = deferLater(reactor, self.IDLE_TIMEOUT_SEC,
                                   self.loseConnection, self.IDLE_TIMEOUT_MSG) \
                .addErrback(self._err_idle_cancelled) \
                .addErrback(self._err_idle_cancelled_unknown_error)

    def _err_idle_cancelled(self, err):
        err.trap(CancelledError)

        # do nothing.

    def _err_idle_cancelled_unknown_error(self, err):
        logger.error("Sessid %s error cancelling idle timer: %s",
                                                self.sessid, err.getTraceback())
        self.idle_timer = None

    def loseConnection(self, reason=None):
        self.disconnecting = True
        self.idle_timer = None
        logger.debug("Aborting connection because %s", reason)
        self.transport.abortConnection()

    def process_incoming_message(self, msg, oob=None):
        p_ctx, others = self.spyne_tpt.produce_contexts(msg)
        p_ctx.oob_ctx = oob
        p_ctx.transport.remote_addr = Address.from_twisted_address(
                                                       self.transport.getPeer())
        p_ctx.transport.protocol = self
        p_ctx.transport.sessid = self.sessid

        self.inactive_queue.append((p_ctx, others))
        self.process_inactive()

    @property
    def num_active_contexts(self):
        return len(self.inreq_queue)

    @property
    def num_inactive_contexts(self):
        return len(self.inactive_queue)

    def process_inactive(self):
        peer = self.transport.getPeer()
        addr_str = Address.from_twisted_address(peer)

        if self.max_in_queue_size == 0:
            while self.num_inactive_contexts > 0:
                p_ctx, others = self.inactive_queue.popleft()
                self.active_queue[id(p_ctx)] = p_ctx

                self.inreq_queue[id(p_ctx)] = None
                self.process_contexts(p_ctx, others)

        else:
            while self.num_active_contexts < self.max_in_queue_size and \
                                                 self.num_inactive_contexts > 0:
                p_ctx, others = self.inactive_queue.popleft()
                self.active_queue[id(p_ctx)] = p_ctx

                self.inreq_queue[id(p_ctx)] = None
                self.process_contexts(p_ctx, others)

            if self.num_active_contexts > self.MAX_INACTIVE_CONTEXTS:
                logger.error("%s Too many inactive contexts. "
                                                "Closing connection.", addr_str)
                self.loseConnection("Too many inactive contexts")

        logger.debug("%s active %d inactive %d", addr_str,
                           self.num_active_contexts, self.num_inactive_contexts)

    def enqueue_outresp_data(self, ctxid, data):
        assert self.inreq_queue[ctxid] is None
        self.inreq_queue[ctxid] = data

        for k, v in list(self.inreq_queue.items()):
            if v is None:
                break

            self.out_write(v)
            self.spyne_tpt.event_manager.fire_event('outresp_flushed',
                                                                     None, k, v)
            del self.inreq_queue[k]
            self.active_queue[k].close()
            del self.active_queue[k]

        self.process_inactive()

    def out_write(self, reqdata):
        if self.out_chunk_size == 0:
            if isinstance(reqdata, io.BufferedIOBase):
                nbytes = reqdata.tell()
                reqdata.seek(0)
                self.transport.write(reqdata.read())
            else:
                nbytes = len(reqdata)
                self.transport.write(reqdata)

            self.sent_bytes += nbytes

        else:
            if isinstance(reqdata, io.BufferedIOBase):
                reqdata.seek(0)

            chunks = self.gen_chunks(reqdata, self.out_chunk_size)
            self.out_chunks.append(chunks)
            deferLater(reactor, 0, self._write_single_chunk)

    def _wait_for_next_chunk(self):
        return deferLater(reactor, self.out_chunk_delay_sec,
                                                       self._write_single_chunk)

    def _write_single_chunk(self):
        try:
            chunk = next(chain.from_iterable(self.out_chunks))
        except StopIteration:
            chunk = None
            self.out_chunks.clear()

        if chunk is None:
            self._delaying = None

            logger.debug("%s no more chunks...", self.sessid)

        else:
            self.transport.write(chunk)
            self.sent_bytes += len(chunk)

            if self.connected and not self.disconnecting:
                self._delaying = self._wait_for_next_chunk()

                logger.debug("%s One chunk of %d bytes written. Delaying "
                          "before next chunk write...", self.sessid, len(chunk))

            else:
                logger.debug("%s Disconnection detected, discarding "
                                                "remaining chunks", self.sessid)
                self.out_chunks.clear()

    def handle_error(self, p_ctx, others, exc):
        self.spyne_tpt.get_out_string(p_ctx)

        if isinstance(exc, InternalError):
            error = self.spyne_tpt.OUT_RESPONSE_SERVER_ERROR
        else:
            error = self.spyne_tpt.OUT_RESPONSE_CLIENT_ERROR

        data = p_ctx.out_document[0]
        if isinstance(data, dict):
            data = list(data.values())

        # tag debug responses with the one from the relevant request
        tag = getattr(p_ctx.transport, 'tag', None)
        if tag is None:
            out_object = (error, msgpack.packb(data))
        else:
            out_object = (error, msgpack.packb(data), tag)

        if p_ctx.oob_ctx is not None:
            p_ctx.oob_ctx.d.callback(out_object)
            return

        if p_ctx.transport is not None:
            out_string = msgpack.packb(out_object)
            p_ctx.transport.resp_length = len(out_string)
            self.enqueue_outresp_data(id(p_ctx), out_string)

        try:
            process_contexts(self, others, p_ctx, error=error)

        except Exception as e:
            # Report but ignore any exceptions from auxiliary methods.
            logger.error("Exception ignored from aux method: %r", e)
            logger.exception(e)

    def _register_callbacks(self, d, p_ctx, others):
        return d \
            .addCallback(self._cb_deferred, p_ctx, others) \
            .addErrback(self._eb_deferred, p_ctx, others) \
            .addErrback(log_and_let_go, logger)

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

        ret = p_ctx.out_object
        if isinstance(ret, Deferred):
            self._register_callbacks(ret, p_ctx, others)

        else:
            ret = p_ctx.out_object[0]
            if isinstance(ret, Deferred):
                self._register_callbacks(ret, p_ctx, others)

            else:
                self._cb_deferred(p_ctx.out_object, p_ctx, others, nowrap=True)

    def _eb_deferred(self, fail, p_ctx, others):
        assert isinstance(fail, Failure)

        if isinstance(fail.value, Fault):
            p_ctx.out_error = fail.value

        else:
            p_ctx.out_error = InternalError(fail.value)
            if not getattr(fail, 'logged', False):
                logger.error(fail.getTraceback())

        try:
            self.handle_error(p_ctx, others, p_ctx.out_error)

        except Exception as e:
            logger.exception(e)
            raise

    def _cb_deferred(self, ret, p_ctx, others, nowrap=False):
        # this means callback is not invoked directly instead of as part of a
        # deferred chain
        if not nowrap:
            # if there is one return value or the output is bare (which means
            # there can't be anything other than 1 return value case) use the
            # enclosing list. otherwise, the return value is a tuple anyway, so
            # leave it be.
            if p_ctx.descriptor.is_out_bare():
                p_ctx.out_object = [ret]

            else:
                if len(p_ctx.descriptor.out_message._type_info) > 1:
                    p_ctx.out_object = ret
                else:
                    p_ctx.out_object = [ret]

        if p_ctx.oob_ctx is not None:
            assert isinstance(p_ctx.oob_ctx.d, Deferred)

            p_ctx.oob_ctx.d.callback(p_ctx.out_object)
            return

        try:
            self.spyne_tpt.get_out_string(p_ctx)
            self.spyne_tpt.pack(p_ctx)

            out_string = b''.join(p_ctx.out_string)
            p_ctx.transport.resp_length = len(out_string)

            self.enqueue_outresp_data(id(p_ctx), out_string)

        except Exception as e:
            logger.exception(e)
            logger.error("%r", p_ctx)
            self.handle_error(p_ctx, others, InternalError(e))

        finally:
            p_ctx.close()

        process_contexts(self.spyne_tpt, others, p_ctx)
