
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

"""This module contains a server implementation that uses a Twisted Web Resource
as transport.
"""

import logging
logger = logging.getLogger(__name__)

from pprint import pformat

from twisted.web.resource import Resource

from rpclib.server.http import HttpMethodContext
from rpclib.server.http import HttpBase

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

class TwistedHttpTransport(HttpBase):
    @staticmethod
    def decompose_incoming_envelope(prot, ctx):
        """This function is only called by the HttpRpc protocol to have the
        twisted web's Request object is parsed into ``ctx.in_body_doc`` and
        ``ctx.in_header_doc``.
        """
        request = ctx.in_document

        ctx.method_request_string = '{%s}%s' % (prot.app.interface.get_tns(),
                              request.path.split('/')[-1])

        logger.debug("\033[92mMethod name: %r\033[0m" % ctx.method_request_string)

        ctx.in_header_doc = request.headers
        ctx.in_body_doc = request.args

class TwistedWebResource(Resource):
    """A server transport that exposes the application as a twisted web
    Resource.
    """

    isLeaf = True

    def __init__(self, app, chunked=False, max_content_length=2 * 1024 * 1024,
                                           block_length=8 * 1024):
        Resource.__init__(self)

        self.http_transport = TwistedHttpTransport(app, chunked,
                                            max_content_length, block_length)
        self._wsdl = None

    def render_GET(self, request):
        _ahv = self.http_transport._allowed_http_verbs
        if request.uri.endswith('.wsdl') or request.uri.endswith('?wsdl'):
            return self.__handle_wsdl_request(request)

        elif not (_ahv is None or "GET" in _ahv):
            request.setResponseCode(405)
            return HTTP_405

        else:
            return self.handle_rpc(request)

    def render_POST(self, request):
        return self.handle_rpc(request)

    def handle_rpc(self, request):
        initial_ctx = HttpMethodContext(self.http_transport, request,
                                    self.http_transport.app.out_protocol.mime_type)
        logger.debug("%s %s %s" % (request, request.__class__, pformat(vars(request))))
        initial_ctx.in_string = [request.content.getvalue()]

        contexts = self.http_transport.generate_contexts(initial_ctx)
        p_ctx, others = contexts[0], contexts[1:]
        if p_ctx.in_error:
            p_ctx.out_object = p_ctx.in_error

        else:
            self.http_transport.get_in_object(p_ctx)

            if p_ctx.in_error:
                p_ctx.out_object = p_ctx.in_error
            else:
                self.http_transport.get_out_object(p_ctx)
                if p_ctx.out_error:
                    p_ctx.out_object = p_ctx.out_error

        self.http_transport.get_out_string(p_ctx)

        self.aux.process_contexts(others)

        return ''.join(p_ctx.out_string)

    def __handle_wsdl_request(self, request):
        ctx = HttpMethodContext(self.http_transport, request,
                                                      "text/xml; charset=utf-8")
        url = _reconstruct_url(request)

        try:
            ctx.transport.wsdl = self._wsdl

            if ctx.transport.wsdl is None:
                from rpclib.interface.wsdl.wsdl11 import Wsdl11
                wsdl = Wsdl11(self.app.interface)
                wsdl.build_interface_document(url)
                self._wsdl = ctx.transport.wsdl = wsdl.get_interface_document()

            assert ctx.transport.wsdl != None

            self.event_manager.fire_event('wsdl', ctx) # implementation hook

            for k,v in ctx.transport.resp_headers.items():
                request.setHeader(k,v)

            return ctx.transport.wsdl
        
        except Exception, e:
            ctx.transport.wsdl_error = e
            self.event_manager.fire_event('wsdl_exception', ctx)
            raise
