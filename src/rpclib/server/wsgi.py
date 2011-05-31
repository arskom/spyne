
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

"""An rpc server that uses http as transport, and wsgi as bridge api"""

# FIXME: this is still too soap-centric.

import logging
logger = logging.getLogger(__name__)

import traceback

from rpclib._base import MethodContext
from rpclib.model.exception import Fault
from rpclib.protocol.soap.mime import apply_mtom
from rpclib.util import reconstruct_url
from rpclib.server import ServerBase

HTTP_500 = '500 Internal server error'
HTTP_200 = '200 OK'
HTTP_404 = '404 Method Not Found'
HTTP_405 = '405 Method Not Allowed'

class ValidationError(Fault):
    pass

class WsgiMethodContext(MethodContext):
    def __init__(self, app, req_env, content_type):
        self.http_req_env = req_env
        self.http_resp_headers = {
            'Content-Type': content_type,
            'Content-Length': '0',
        }

        MethodContext.__init__(self, app)

class Application(ServerBase):
    transport = 'http://schemas.xmlsoap.org/soap/http'

    def __init__(self, app):
        ServerBase.__init__(self, app)

        self._allowed_http_verbs = app.in_protocol.allowed_http_verbs

    def __call__(self, req_env, start_response, wsgi_url=None):
        '''This method conforms to the WSGI spec for callable wsgi applications
        (PEP 333). It looks in environ['wsgi.input'] for a fully formed rpc
        message envelope, will deserialize the request parameters and call the
        method on the object returned by the get_handler() method.

        @param the http environment
        @param a callable that begins the response message
        @param the optional url

        @returns the string representation of the rpc message
        '''

        url = wsgi_url
        if url is None:
            url = reconstruct_url(req_env).split('.wsdl')[0]

        if self.__is_wsdl_request(req_env):
            return self.__handle_wsdl_request(req_env, start_response, url)

        elif not (req_env['REQUEST_METHOD'].upper() in self._allowed_http_verbs):
            start_response(HTTP_405, [
                ('Content-type', ''),
                ('Allow', ', '.join(self._allowed_http_verbs)),
            ])
            return ['']

        else:
            return self.__handle_rpc(req_env, start_response)

    def __is_wsdl_request(self, req_env):
        # Get the wsdl for the service. Assume path_info matches pattern:
        # /stuff/stuff/stuff/serviceName.wsdl or
        # /stuff/stuff/stuff/serviceName/?wsdl

        return (
            req_env['REQUEST_METHOD'].lower() == 'get'
            and (
                   req_env['QUERY_STRING'].endswith('wsdl')
                or req_env['PATH_INFO'].endswith('wsdl')
            )
        )

    def __handle_wsdl_request(self, req_env, start_response, url):
        http_resp_headers = {'Content-Type': 'text/xml'}

        try:
            wsdl = self.app.interface.get_interface_document()
            if wsdl is None:
                self.app.interface.build_interface_document(url)
                wsdl = self.app.interface.get_interface_document()
            assert wsdl != None
            
            self.on_wsdl(req_env, wsdl) # implementation hook

            http_resp_headers['Content-Length'] = str(len(wsdl))
            start_response(HTTP_200, http_resp_headers.items())

            return [wsdl]

        except Exception, e:
            logger.error(traceback.format_exc())

            # implementation hook
            self.on_wsdl_exception(req_env, e)

            start_response(HTTP_500, http_resp_headers.items())

            return [""]

    def __handle_rpc(self, req_env, start_response):
        ctx = WsgiMethodContext(self.app, req_env,
                                                self.app.out_protocol.mime_type)

        # implementation hook
        self.on_wsgi_call(req_env)

        ret = self.app.in_protocol.reconstruct_wsgi_request(req_env)
        in_string, in_string_charset = ret

        in_object = self.get_in_object(ctx, in_string, in_string_charset)

        return_code = HTTP_200
        if ctx.in_error:
            out_object = ctx.in_error
            return_code = HTTP_500

        else:
            if ctx.service_class == None:
                start_response(HTTP_404, ctx.http_resp_headers.items())
                return ['']

            out_object = self.get_out_object(ctx, in_object)
            if ctx.out_error:
                out_object = ctx.out_error
                return_code = HTTP_500

        out_fragments = self.get_out_string(ctx, out_object)

        # implementation hook
        self.on_wsgi_return(req_env, ctx.http_resp_headers, out_fragments)

        if ctx.descriptor and ctx.descriptor.mtom:
            # when there are more than one return type, the result is 
            # encapsulated inside a list. when there's just one, the result
            # is returned unencapsulated. the apply_mtom always expects the
            # objects to be inside an iterable, hence the following test.
            out_type_info = ctx.descriptor.out_message._type_info
            if len(out_type_info) == 1:
                out_object = [out_object]

            ctx.http_resp_headers, out_fragments = apply_mtom(ctx.http_resp_headers,
                    out_fragments, ctx.descriptor.out_message._type_info.values(),
                    out_object)

        # initiate the response
        del ctx.http_resp_headers['Content-Length']
        start_response(return_code, ctx.http_resp_headers.items())

        return out_fragments

    def on_wsgi_call(self, environ):
        '''This is the first method called when this WSGI app is invoked.

        @param the wsgi environment
        '''
        pass

    def on_wsdl(self, environ, wsdl):
        '''This is called when a wsdl is requested.

        @param the wsgi environment
        @param the wsdl string
        '''
        pass

    def on_wsdl_exception(self, environ, exc):
        '''Called when an exception occurs durring wsdl generation.

        @param the wsgi environment
        @param exc the exception
        @param the fault response string
        '''
        pass

    def on_wsgi_return(self, environ, http_headers, return_str):
        '''Called before the application returns.

        @param the wsgi environment
        @param http response headers as dict
        @param return string of the rpc message
        '''
        pass
