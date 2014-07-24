
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

from spyne import EventManager
from spyne.auxproc import process_contexts
from spyne.interface import AllYourInterfaceDocuments
from spyne.model import Fault
from spyne.model import PushBase
from spyne.protocol import ProtocolBase
from spyne.util import Break
from spyne.util import coroutine


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
        self.doc = AllYourInterfaceDocuments(app.interface)

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

            ctx.in_object = None
            ctx.in_error = e
            ctx.out_error = e

    def get_out_object(self, ctx):
        """Calls the matched user function by passing it the ``ctx.in_object``
        to set ``ctx.out_object``."""

        if ctx.in_error is None:
            # event firing is done in the spyne.application.Application
            self.app.process_request(ctx)
        else:
            raise ctx.in_error

    def get_out_string_pull(self, ctx):
        """Uses the ``ctx.out_object`` to set ``ctx.out_document`` and later
        ``ctx.out_string``."""

        # This means the user wanted to override the way Spyne generates the
        # outgoing byte stream. So we leave it alone.
        if ctx.out_string is not None:
            return

        if ctx.out_document is None:
            ret = ctx.out_protocol.serialize(ctx, message=ProtocolBase.RESPONSE)
            if isgenerator(ret):
                oobj, = ctx.out_object
                if oobj is None:
                    ret.throw(Break())

                else:
                    assert isinstance(oobj, PushBase), \
                                          "%r is not a PushBase instance" % oobj

                    self.run_push(oobj, ctx, [], ret)
                    oobj.close()

        if ctx.service_class != None:
            if ctx.out_error is None:
                ctx.service_class.event_manager.fire_event(
                                            'method_return_document', ctx)
            else:
                ctx.service_class.event_manager.fire_event(
                                            'method_exception_document', ctx)

        ctx.out_protocol.create_out_string(ctx)

        if ctx.service_class != None:
            if ctx.out_error is None:
                ctx.service_class.event_manager.fire_event(
                                            'method_return_string', ctx)
            else:
                ctx.service_class.event_manager.fire_event(
                                            'method_exception_string', ctx)

        if ctx.out_string is None:
            ctx.out_string = [""]


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

    def serve_forever(self):
        """Implement your event loop here, if needed."""

        raise NotImplementedError()

    def run_push(self, ret, p_ctx, others, gen):
        assert isinstance(ret, PushBase)

        assert p_ctx.out_stream is not None

        # fire events
        p_ctx.app.event_manager.fire_event('method_return_push', p_ctx)
        if p_ctx.service_class is not None:
            p_ctx.service_class.event_manager.fire_event('method_return_push', p_ctx)

        def _cb_push_finish():
            process_contexts(self, others, p_ctx)

        ret.init(p_ctx, p_ctx.out_stream, gen, _cb_push_finish, None)
