
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

from spyne import EventManager
from spyne.model.fault import Fault
from spyne.protocol import ProtocolBase
from spyne.interface import AllYourInterfaceDocuments


class ServerBase(object):
    """This class is the abstract base class for all server transport
    implementations. Unlike the client transports, this class does not define
    a pure-virtual method that needs to be implemented by all base classes.

    If there is a call to start the main loop, it's conventionally called
    ``serve_forever()``.
    """

    transport = None
    """The transport type, conventionally defined by the URI string to its
    definition."""

    def __init__(self, app):
        self.app = app
        self.app.transport = self.transport
        self.event_manager = EventManager(self)
        self.doc = AllYourInterfaceDocuments(app.interface)

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

        except Fault, e:
            ctx.in_object = None
            ctx.in_error = e
            ctx.out_error = e

            retval = [ctx]

        return retval

    def get_in_object(self, ctx):
        """Uses the ctx.in_string to set ctx.in_body_doc, which in turn is used
        to set ctx.in_object."""

        try:
            # sets ctx.in_object and ctx.in_header
            self.app.in_protocol.deserialize(ctx,
                                        message=self.app.in_protocol.REQUEST)

        except Fault, e:
            logger.exception(e)

            ctx.in_object = None
            ctx.in_error = e
            ctx.out_error = e

    def get_out_object(self, ctx):
        """Calls the matched method using the ctx.in_object to get
        ctx.out_object."""

        if ctx.in_error is None:
            # event firing is done in the spyne.application.Application
            self.app.process_request(ctx)
        else:
            raise ctx.in_error

    def get_out_string(self, ctx):
        """Uses the ctx.out_object to set ctx.out_document and later
        ctx.out_object."""

        assert ctx.out_document is None
        assert ctx.out_string is None

        self.app.out_protocol.serialize(ctx,
                                        message=self.app.out_protocol.RESPONSE)

        if ctx.service_class != None:
            if ctx.out_error is None:
                ctx.service_class.event_manager.fire_event(
                                            'method_return_document', ctx)
            else:
                ctx.service_class.event_manager.fire_event(
                                            'method_exception_document', ctx)

        self.app.out_protocol.create_out_string(ctx)

        if ctx.service_class != None:
            if ctx.out_error is None:
                ctx.service_class.event_manager.fire_event(
                                            'method_return_string', ctx)
            else:
                ctx.service_class.event_manager.fire_event(
                                            'method_exception_string', ctx)

        if ctx.out_string is None:
            ctx.out_string = [""]

    def serve_forever():
        """Implement your event loop here."""

        raise NotImplementedError()
