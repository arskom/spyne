
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

import logging
logger = logging.getLogger(__name__)

from rpclib.protocol import ProtocolBase
import urlparse

# this is not exactly rest, because it ignores http verbs.
class HttpRpc(ProtocolBase):
    def create_in_document(self, ctx, in_string_encoding=None):
        assert ctx.transport.type == 'wsgi', ("This protocol only works with "
                                              "the wsgi api.")

        logger.debug("PATH_INFO: %r" % ctx.transport.req_env['PATH_INFO'])
        logger.debug("QUERY_STRING: %r" % ctx.transport.req_env['QUERY_STRING'])

        ctx.method_request_string = '{%s}%s' % (self.app.interface.get_tns(),
                              ctx.transport.req_env['PATH_INFO'].split('/')[-1])
        logger.debug("\033[92mMethod name: %r\033[0m" % ctx.method_request_string)

        self.app.in_protocol.set_method_descriptor(ctx)

        ctx.in_header_doc = None
        ctx.in_body_doc = urlparse.parse_qs(ctx.transport.req_env['QUERY_STRING'])

        logger.debug(repr(ctx.in_body_doc))

        return ctx.in_body_doc

    def deserialize(self, ctx):
        body_class = ctx.descriptor.in_message
        if ctx.in_body_doc is not None and len(ctx.in_body_doc) > 0:
            ctx.in_object = body_class.from_dict(ctx.in_body_doc)
        else:
            ctx.in_object = [None] * len(body_class._type_info)

        self.event_manager.fire_event('deserialize', ctx)

    def serialize(self, ctx):
        result_message_class = ctx.descriptor.out_message
        result_message = result_message_class()

        # assign raw result to its wrapper, result_message
        out_type_info = result_message_class._type_info
        if len(out_type_info) > 0:
             if len(out_type_info) == 1:
                 attr_name = result_message_class._type_info.keys()[0]
                 setattr(result_message, attr_name, ctx.out_object)

             else:
                 for i in range(len(out_type_info)):
                     attr_name=result_message_class._type_info.keys()[i]
                     setattr(result_message, attr_name, ctx.out_object[i])

        wrapped_result = ctx.descriptor.out_message.to_dict(result_message)

        ctx.out_document, = wrapped_result.itervalues()

        self.event_manager.fire_event('serialize', ctx)

    def create_out_string(self, ctx, out_string_encoding=None):
        ctx.out_string = ctx.out_document
