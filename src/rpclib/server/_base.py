
#
# rpclib - Copyright (C) Rpclib contributors.
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

"""This module contains the ServerBase class, the abstract base class for all
server transport implementations."""

import logging
logger = logging.getLogger(__name__)

from rpclib.model.fault import Fault
from rpclib._base import EventManager

class ServerBase(object):
    """This class is the abstract base class for all server transport
    implementations. Unlike the client transports, this class does not define
    a pure-virtual method that needs to be implemented by all base classes.

    If there is a call to start the main loop, it's conventionally called
    'serve_forever()'.
    """

    transport = None
    """The transport type, conventionally defined by the URI string to its
    definition."""

    supports_fanout_methods = False

    def __init__(self, app):
        self.app = app
        self.app.transport = self.transport
        if app.supports_fanout_methods and not self.supports_fanout_methods:
            logger.warning("""Your application is in fanout mode.
            note that in fanout mode, only the response from the last
            call will be returned.""")

        self.event_manager = EventManager(self)

    def generate_contexts(self, ctx, in_string_charset=None):
        """Calls create_in_document and decompose_incoming_envelope to get
        method_request string in order to generate contexts.
        """

        try:
            # sets ctx.in_document
            self.app.in_protocol.create_in_document(ctx, in_string_charset)

            # sets ctx.in_body_doc, ctx.in_header_doc and ctx.method_request_string
            self.app.in_protocol.decompose_incoming_envelope(ctx)

            # returns a list of contexts. multiple contexts are only returned
            # when supports_fanout_mode=True parameter is given to the
            # Application constructor and there's more than one method defined
            # for the given method_request_string here.
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
            ctx.in_object = None
            ctx.in_error = e
            ctx.out_error = e

    def get_out_object(self, ctx):
        """Calls the matched method using the ctx.in_object to get
        ctx.out_object."""

        assert ctx.in_error is None, "There was an error processing input string"

        # event firing is done in the rpclib.application.Application
        self.app.process_request(ctx)

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
