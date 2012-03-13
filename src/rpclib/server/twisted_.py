
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

"""This module contains a server implementation that uses a TwistedWeb Resource
as transport.
"""

import logging
logger = logging.getLogger(__name__)

from twisted.web.resource import Resource

from rpclib.server.http import HttpMethodContext
from rpclib.server.http import HttpBase

from rpclib.const.http import HTTP_400
from rpclib.const.http import HTTP_405

def _reconstruct_url(request):
    server_name = request.getRequestHostname()
    server_port = request.getHost().port
    if (bool(request.isSecure()), server_port) not in [
            (True, 443), (False, 80)]:
        server_name = '%s:%d' % (server_name, server_port)

    if request.isSecure():
        url_scheme = 'https'
    else:
        url_scheme = 'http'

    return ''.join([url_scheme, "://", server_name, request.uri])

class TwistedWebMethodContext(HttpMethodContext):
    def __init__(self, app, request, content_type):
        HttpMethodContext.__init__(self, app, request, content_type)

        self.transport.type = 'twisted.web'

class TwistedWebApplication(Resource):
    """The ZeroMQ server transport."""

    isLeaf = True

    def __init__(self, app, chunked=False, max_content_length=2 * 1024 * 1024,
                                           block_length=8 * 1024):
        Resource.__init__(self)

        self.__http_base = HttpBase(app, chunked, max_content_length, block_length)

    def render_GET(self, request):
        retval = ""
        
        if request.uri.endswith('.wsdl') or request.uri.endswith('?wsdl'):
            retval = self.__handle_wsdl_request(request)

        elif "get" not in self.__http_base._allowed_http_verbs:
            request.setResponseCode(405)
            retval = HTTP_405

        else:
            request.setResponseCode(400)
            retval = HTTP_400

        return retval

    def render_POST(self, request):
        initial_ctx = TwistedWebMethodContext(self.__http_base.app, request,
                                    self.__http_base.app.out_protocol.mime_type)
        initial_ctx.in_string = [request.content.getvalue()]

        ctx, = self.__http_base.generate_contexts(initial_ctx)
        if ctx.in_error:
            ctx.out_object = ctx.in_error

        else:
            self.__http_base.get_in_object(ctx)

            if ctx.in_error:
                ctx.out_object = ctx.in_error
            else:
                self.__http_base.get_out_object(ctx)
                if ctx.out_error:
                    ctx.out_object = ctx.out_error

        self.__http_base.get_out_string(ctx)

        return ''.join(ctx.out_string)

    def __handle_wsdl_request(self, request):
        ctx = TwistedWebMethodContext(self.app, request, "text/xml; charset=utf-8")
        url = _reconstruct_url(request)

        try:
            ctx.transport.wsdl = self.app.interface.get_interface_document()

            if ctx.transport.wsdl is None:
                self.app.interface.build_interface_document(url)
                ctx.transport.wsdl = self.app.interface.get_interface_document()

            assert ctx.transport.wsdl != None

            self.event_manager.fire_event('wsdl', ctx) # implementation hook

            ctx.transport.resp_headers['Content-Length'] = str(len(ctx.transport.wsdl))
            for k,v in ctx.transport.resp_headers.items():
                request.setHeader(k,v)

            return ctx.transport.wsdl
        
        except Exception, e:
            ctx.transport.wsdl_error = e
            self.event_manager.fire_event('wsdl_exception', ctx)
            raise
