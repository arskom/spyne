
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

# FIXME: this is maybe still too soap-centric.

import logging
logger = logging.getLogger(__name__)

import cgi

from rpclib import TransportContext
from rpclib import MethodContext

from rpclib.error import NotFoundError
from rpclib.protocol.soap.mime import apply_mtom
from rpclib.util import reconstruct_url
from rpclib.server import ServerBase


HTTP_500 = '500 Internal server error'
HTTP_200 = '200 OK'
HTTP_404 = '404 Method Not Found'
HTTP_405 = '405 Method Not Allowed'


def reconstruct_wsgi_request(http_env):
    """Reconstruct http payload using information in the http header"""

    input = http_env.get('wsgi.input')
    try:
        length = int(http_env.get("CONTENT_LENGTH"))
    except ValueError:
        length = 0

    # fyi, here's what the parse_header function returns:
    # >>> import cgi; cgi.parse_header("text/xml; charset=utf-8")
    # ('text/xml', {'charset': 'utf-8'})
    content_type = cgi.parse_header(http_env.get("CONTENT_TYPE"))
    charset = content_type[1].get('charset',None)
    if charset is None:
        charset = 'ascii'

    return input.read(length), charset


class WsgiTransportContext(TransportContext):
    def __init__(self, req_env, content_type):
        TransportContext.__init__(self, 'wsgi')

        self.req_env = req_env
        self.resp_headers = {
            'Content-Type': content_type,
            'Content-Length': '0',
        }
        self.resp_code = None
        self.req_method = req_env.get('REQUEST_METHOD', None)
        self.wsdl_error = None


class WsgiMethodContext(MethodContext):
    def __init__(self, app, req_env, content_type):
        MethodContext.__init__(self, app)

        self.transport = WsgiTransportContext(req_env, content_type)


class WsgiApplication(ServerBase):
    transport = 'http://schemas.xmlsoap.org/soap/http'

    def __init__(self, app):
        ServerBase.__init__(self, app)

        self._allowed_http_verbs = app.in_protocol.allowed_http_verbs

    def __call__(self, req_env, start_response, wsgi_url=None):
        '''This method conforms to the WSGI spec for callable wsgi applications
        (PEP 333). It looks in environ['wsgi.input'] for a fully formed rpc
        message envelope, will deserialize the request parameters and call the
        method on the object returned by the get_handler() method.
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
        # /stuff/stuff/stuff/serviceName/?wsdl with anything between ? and wsdl.

        return (
            req_env['REQUEST_METHOD'].lower() == 'get'
            and (
                   req_env['QUERY_STRING'].endswith('wsdl')
                or req_env['PATH_INFO'].endswith('wsdl')
            )
        )

    def __handle_wsdl_request(self, req_env, start_response, url):
        ctx = WsgiMethodContext(self.app, req_env, 'text/xml; charset=utf-8')

        try:
            wsdl = self.app.interface.get_interface_document()
            if wsdl is None:
                self.app.interface.build_interface_document(url)
                wsdl = self.app.interface.get_interface_document()

            assert wsdl != None

            self.event_manager.fire_event('wsdl',ctx) # implementation hook

            ctx.transport.resp_headers['Content-Length'] = str(len(wsdl))
            start_response(HTTP_200, ctx.transport.resp_headers.items())

            return [wsdl]

        except Exception, e:
            logger.exception(e)
            ctx.transport.wsdl_error = e
            # implementation hook
            self.event_manager.fire_event('wsdl_exception', ctx)

            start_response(HTTP_500, ctx.transport.resp_headers.items())

            return [""]

    def __handle_rpc(self, req_env, start_response):
        ctx = WsgiMethodContext(self.app, req_env,
                                                self.app.out_protocol.mime_type)

        # implementation hook
        self.event_manager.fire_event('wsgi_call', ctx)

        ctx.in_string, in_string_charset = reconstruct_wsgi_request(req_env)

        try:
            self.get_in_object(ctx, in_string_charset)
        except NotFoundError, e:
            pass

        if ctx.in_error:
            out_object = ctx.in_error
            if ctx.transport.resp_code is None:
                ctx.transport.resp_code = HTTP_500

        else:
            if ctx.service_class == None:
                if ctx.transport.resp_code is None:
                    ctx.transport.resp_code = HTTP_500

                ctx.out_string = [ctx.transport.resp_code]

                self.event_manager.fire_event('wsgi_method_not_found', ctx)

                start_response(ctx.transport.resp_code, ctx.transport.resp_headers.items())
                return ctx.out_string

            self.get_out_object(ctx)
            if ctx.out_error is None:
                ctx.transport.resp_code = HTTP_200
            else:
                ctx.transport.resp_code = HTTP_500

        self.get_out_string(ctx)

        # implementation hook
        self.event_manager.fire_event('wsgi_return', ctx)

        if ctx.descriptor and ctx.descriptor.mtom:
            # when there is more than one return type, the result is
            # encapsulated inside a list. when there's just one, the result
            # is returned in a non-encapsulated form. the apply_mtom always
            # expects the objects to be inside an iterable, hence the following
            # test.
            out_type_info = ctx.descriptor.out_message._type_info
            if len(out_type_info) == 1:
                out_object = [out_object]

            ctx.transport.resp_headers, ctx.out_string = apply_mtom(
                    ctx.transport.resp_headers, ctx.out_string,
                    ctx.descriptor.out_message._type_info.values(),
                    out_object
                )

        # We can't set the content-length if we want to support any kind of
        # python iterable as output. We can't iterate and count, that defeats
        # the whole point.
        del ctx.transport.resp_headers['Content-Length']

        # initiate the response
        start_response(ctx.transport.resp_code, ctx.transport.resp_headers.items())

        return ctx.out_string
