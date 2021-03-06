
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

import logging
logger = logging.getLogger(__name__)

from inspect import isgenerator

from spyne import EventManager, Ignored
from spyne.auxproc import process_contexts
from spyne.model import Fault, PushBase
from spyne.protocol import ProtocolBase
from spyne.util import Break, coroutine


class ServerBase(object):
    """This class is the abstract base class for all server transport
    implementations. Unlike the client transports, this class does not define
    a pure-virtual method that needs to be implemented by all base classes.

    If there needs to be a call to start the main loop, it's called
    ``serve_forever()`` by convention.
    """

    transport = None
    """The transport type, which is a URI string to its definition by
    convention."""

    def __init__(self, app):
        self.app = app
        self.app.transport = self.transport  # FIXME: this is weird
        self.appinit()

        self.event_manager = EventManager(self)

    @property
    def doc(self):  # for backwards compatibility
        return self.app.interface.docs

    @doc.setter
    def doc(self, value):  # for backwards compatibility
        self.app.interface.docs = doc

    def appinit(self):
        self.app.reinitialize(self)

    def generate_contexts(self, ctx, in_string_charset=None):
        """Calls create_in_document and decompose_incoming_envelope to get
        method_request string in order to generate contexts.
        """
        try:
            # sets ctx.in_document
            self.app.in_protocol.create_in_document(ctx, in_string_charset)

            # sets ctx.in_body_doc, ctx.in_header_doc and
            # ctx.method_request_string
            self.app.in_protocol.decompose_incoming_envelope(ctx,
                                                           ProtocolBase.REQUEST)

            # returns a list of contexts. multiple contexts can be returned
            # when the requested method also has bound auxiliary methods.
            retval = self.app.in_protocol.generate_method_contexts(ctx)

        except Fault as e:
            ctx.in_object = None
            ctx.in_error = e
            ctx.out_error = e

            retval = (ctx,)

            ctx.fire_event('method_exception_object')

        return retval

    def get_in_object(self, ctx):
        """Uses the ``ctx.in_string`` to set ``ctx.in_body_doc``, which in turn
        is used to set ``ctx.in_object``."""

        try:
            # sets ctx.in_object and ctx.in_header
            self.app.in_protocol.deserialize(ctx,
                                           message=self.app.in_protocol.REQUEST)

        except Fault as e:
            logger.exception(e)
            logger.debug("Failed document is: %s", ctx.in_document)

            ctx.in_object = None
            ctx.in_error = e
            ctx.out_error = e

            ctx.fire_event('method_exception_object')

    def get_out_object(self, ctx):
        """Calls the matched user function by passing it the ``ctx.in_object``
        to set ``ctx.out_object``."""

        if ctx.in_error is None:
            # event firing is done in the spyne.application.Application
            self.app.process_request(ctx)
        else:
            raise ctx.in_error

        if isinstance(ctx.out_object, (list, tuple)) \
                    and len(ctx.out_object) > 0 \
                    and isinstance(ctx.out_object[0], Ignored):
            ctx.out_object = (None,)

        elif isinstance(ctx.out_object, Ignored):
            ctx.out_object = ()

    def convert_pull_to_push(self, ctx, gen):
        oobj, = ctx.out_object
        if oobj is None:
            gen.throw(Break())

        elif isinstance(oobj, PushBase):
            pass

        elif len(ctx.pusher_stack) > 0:
            oobj = ctx.pusher_stack[-1]
            assert isinstance(oobj, PushBase)

        else:
            raise ValueError("%r is not a PushBase instance" % oobj)

        retval = self.init_interim_push(oobj, ctx, gen)
        return self.pusher_try_close(ctx, oobj, retval)

    def get_out_string_pull(self, ctx):
        """Uses the ``ctx.out_object`` to set ``ctx.out_document`` and later
        ``ctx.out_string``."""

        # This means the user wanted to override the way Spyne generates the
        # outgoing byte stream. So we leave it alone.
        if ctx.out_string is not None:
            return

        if ctx.out_document is None:
            ret = ctx.out_protocol.serialize(ctx, message=ProtocolBase.RESPONSE)

            if isgenerator(ret) and ctx.out_object is not None and \
                                                       len(ctx.out_object) == 1:
                if len(ctx.pusher_stack) > 0:
                    # we suspend request processing here because there now
                    # seems to be a PushBase waiting for input.
                    return self.convert_pull_to_push(ctx, ret)

        self.finalize_context(ctx)

    def finalize_context(self, ctx):
        if ctx.out_error is None:
            ctx.fire_event('method_return_document')
        else:
            ctx.fire_event('method_exception_document')

        ctx.out_protocol.create_out_string(ctx)

        if ctx.out_error is None:
            ctx.fire_event('method_return_string')
        else:
            ctx.fire_event('method_exception_string')

        if ctx.out_string is None:
            ctx.out_string = (b'',)

    # for backwards compatibility
    get_out_string = get_out_string_pull

    @coroutine
    def get_out_string_push(self, ctx):
        """Uses the ``ctx.out_object`` to directly set ``ctx.out_string``."""

        ret = ctx.out_protocol.serialize(ctx, message=ProtocolBase.RESPONSE)
        if isgenerator(ret):
            try:
                while True:
                    y = (yield)
                    ret.send(y)

            except Break:
                try:
                    ret.throw(Break())
                except StopIteration:
                    pass

        self.finalize_context(ctx)

    def serve_forever(self):
        """Implement your event loop here, if needed."""

        raise NotImplementedError()

    def init_interim_push(self, ret, p_ctx, gen):
        assert isinstance(ret, PushBase)
        assert p_ctx.out_stream is not None

        # we don't add interim pushers to the stack because we don't know
        # where to find them in the out_object's hierarchy. whatever finds
        # one in the serialization pipeline has to push it to pusher_stack so
        # the machinery in ServerBase can initialize them using this function.

        # fire events
        p_ctx.fire_event('method_return_push')

        def _cb_push_finish():
            process_contexts(self, (), p_ctx)

        return self.pusher_init(p_ctx, gen, _cb_push_finish, ret, interim=True)

    def pusher_init(self, p_ctx, gen, _cb_push_finish, pusher, interim):
        return pusher.init(p_ctx, gen, _cb_push_finish, None, interim)

    def pusher_try_close(self, ctx, pusher, _):
        logger.debug("Closing pusher with ret=%r", pusher)

        pusher.close()

        popped = ctx.pusher_stack.pop()
        assert popped is pusher

    def init_root_push(self, ret, p_ctx, others):
        assert isinstance(ret, PushBase)

        if ret in p_ctx.pusher_stack:
            logger.warning('PushBase reinit avoided.')
            return

        p_ctx.pusher_stack.append(ret)

        # fire events
        p_ctx.fire_event('method_return_push')

        # start push serialization
        gen = self.get_out_string_push(p_ctx)

        assert isgenerator(gen), "It looks like this protocol is not " \
                                 "async-compliant yet."

        def _cb_push_finish():
            process_contexts(self, others, p_ctx)

        retval = self.pusher_init(p_ctx, gen, _cb_push_finish, ret,
                                                                  interim=False)

        self.pusher_try_close(p_ctx, ret, retval)

        return retval

    @staticmethod
    def set_out_document_push(ctx):
        ctx.out_document = _write()
        ctx.out_document.send(None)


def _write():
    v = yield
    yield v
