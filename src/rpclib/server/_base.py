
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

"""A soap server that uses http as transport, and wsgi as bridge api"""

import logging
logger = logging.getLogger(__name__)

from rpclib.model.exception import Fault
from rpclib._base import EventManager

HTTP_500 = '500 Internal server error'
HTTP_200 = '200 OK'
HTTP_405 = '405 Method Not Allowed'

class ValidationError(Fault):
    pass

class ServerBase(object):
    transport = None

    def __init__(self, app):
        self.app = app
        self.app.transport = self.transport
        self.event_manager = EventManager(self)

    def get_in_object(self, ctx, in_string_charset=None):
        self.app.in_protocol.create_in_document(ctx, in_string_charset)

        try:
            # sets the ctx.in_body_doc and ctx.in_header_doc properties
            self.app.in_protocol.decompose_incoming_envelope(ctx)

            if ctx.service_class != None:
                ctx.service_class.event_manager.fire_event('decompose_envelope',
                                                                        ctx)
            self.app.in_protocol.deserialize(ctx)

        except Fault,e:
            ctx.in_object = None
            ctx.in_error = e
            ctx.out_error = e

    def get_out_object(self, ctx):
        self.app.process_request(ctx, ctx.in_object)

    def get_out_string(self, ctx):
        assert ctx.out_document is None
        assert ctx.out_string is None

        self.app.out_protocol.serialize(ctx)

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
