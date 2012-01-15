
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

"""An rpc server that uses http as transport, and wsgi as bridge api."""

import logging
logger = logging.getLogger(__name__)

import cgi

from rpclib import TransportContext
from rpclib import MethodContext

from rpclib.error import RequestTooLongError
from rpclib.protocol.soap.mime import apply_mtom
from rpclib.util import reconstruct_url
from rpclib.server import ServerBase

from rpclib.const.http import HTTP_200
from rpclib.const.http import HTTP_405
from rpclib.const.http import HTTP_500

MAX_CONTENT_LENGTH = 2 * 1024 * 1024
BLOCK_LENGTH = 8 * 1024

def _wsgi_input_to_iterable(http_env):
    istream = http_env.get('wsgi.input')

    length = http_env.get('CONTENT_LENGTH', str(MAX_CONTENT_LENGTH))
    if len(length) == 0:
        length = 0
    else:
        length = int(length)

    if length > MAX_CONTENT_LENGTH:
        raise RequestTooLongError()
    bytes_read = 0

    while bytes_read < length:
        bytes_to_read = min(BLOCK_LENGTH, length - bytes_read)

        if bytes_to_read + bytes_read > MAX_CONTENT_LENGTH:
            raise RequestTooLongError()

        data = istream.read(bytes_to_read)
        if data is None:
            break

        bytes_read += len(data)

        yield data

def reconstruct_wsgi_request(http_env):
    """Reconstruct http payload using information in the http header."""

    # fyi, here's what the parse_header function returns:
    # >>> import cgi; cgi.parse_header("text/xml; charset=utf-8")
    # ('text/xml', {'charset': 'utf-8'})
    content_type = cgi.parse_header(http_env.get("CONTENT_TYPE"))
    charset = content_type[1].get('charset', 'utf-8')

    return _wsgi_input_to_iterable(http_env), charset


class WsgiTransportContext(TransportContext):
    """The class that is used in the transport attribute of the
    :class:`WsgiMethodContext` class."""

    def __init__(self, req_env, content_type):
        TransportContext.__init__(self, 'wsgi')

        self.req_env = req_env
        """WSGI Request environment"""

        self.resp_headers = {
            'Content-Type': content_type,
            'Content-Length': None,
        }
        """HTTP Response headers."""

        self.resp_code = None
        """HTTP Response code."""

        self.req_method = req_env.get('REQUEST_METHOD', None)
        """HTTP Request verb, as a convenience to users."""

        self.wsdl = None
        """The WSDL document that is being returned. Only relevant when handling
        WSDL requests."""

        self.wsdl_error = None
        """The error when handling WSDL requests."""

    def get_mime_type(self):
        return self.resp_headers['Content-Type']

    def set_mime_type(self, what):
        self.resp_headers['Content-Type'] = what

    mime_type = property(get_mime_type, set_mime_type)
    """Provides an easy way to set outgoing mime type. Synonym for
    `content_type`"""

    content_type = property(get_mime_type, set_mime_type)
    """Provides an easy way to set outgoing mime type. Synonym for
    `mime_type`"""


class WsgiMethodContext(MethodContext):
    """The WSGI-Specific method context. WSGI-Specific information is stored in
    the transport attribute using the :class:`WsgiTransportContext` class.
    """

    def __init__(self, app, req_env, content_type):
        MethodContext.__init__(self, app)

        self.transport = WsgiTransportContext(req_env, content_type)
        """Holds the WSGI-specific information"""

class WsgiApplication(ServerBase):
    '''A `PEP-3333 <http://www.python.org/dev/peps/pep-3333/#preface-for-readers-of-pep-333>`_
    compliant callable class.

    Supported events:
        * ``wsdl``
            Called right before the wsdl data is returned to the client.

        * ``wsdl_exception``
            Called right after an exception is thrown during wsdl generation.
            The exception object is stored in ctx.transport.wsdl_error attribute.

        * ``wsgi_call``
            Called first when the incoming http request is identified as a rpc
            request.

        * ``wsgi_return``
            Called right before the output stream is returned to the WSGI handler.

        * ``wsgi_error``
            Called right before returning the exception to the client.
    '''

    transport = 'http://schemas.xmlsoap.org/soap/http'

    def __init__(self, app):
        ServerBase.__init__(self, app)

        self._allowed_http_verbs = app.in_protocol.allowed_http_verbs
        self._verb_handlers = {
            "GET": self.handle_rpc,
            "POST": self.handle_rpc,
        }

    def __call__(self, req_env, start_response, wsgi_url=None):
        '''This method conforms to the WSGI spec for callable wsgi applications
        (PEP 333). It looks in environ['wsgi.input'] for a fully formed rpc
        message envelope, will deserialize the request parameters and call the
        method on the object returned by the get_handler() method.
        '''

        url = wsgi_url
        verb = req_env['REQUEST_METHOD'].upper()
        if url is None:
            url = reconstruct_url(req_env).split('.wsdl')[0]

        if self.__is_wsdl_request(req_env):
            return self.__handle_wsdl_request(req_env, start_response, url)

        elif not (verb in self._allowed_http_verbs or verb in self._verb_handlers):
            start_response(HTTP_405, [
                ('Content-type', ''),
                ('Allow', ', '.join(self._allowed_http_verbs)),
            ])
            return ['']

        else:
            return self._verb_handlers[verb](req_env, start_response)

    def __is_wsdl_request(self, req_env):
        # Get the wsdl for the service. Assume path_info matches pattern:
        # /stuff/stuff/stuff/serviceName.wsdl or
        # /stuff/stuff/stuff/serviceName/?wsdl

        return (
            req_env['REQUEST_METHOD'].lower() == 'get'
            and (
                   req_env['QUERY_STRING'] == 'wsdl'
                or req_env['PATH_INFO'].endswith('.wsdl')
            )
        )

    def __handle_wsdl_request(self, req_env, start_response, url):
        ctx = WsgiMethodContext(self.app, req_env, 'text/xml; charset=utf-8')
        try:
            ctx.transport.wsdl = self.app.interface.get_interface_document()
            if ctx.transport.wsdl is None:
                self.app.interface.build_interface_document(url)
                ctx.transport.wsdl = self.app.interface.get_interface_document()

            assert ctx.transport.wsdl != None

            self.event_manager.fire_event('wsdl', ctx) # implementation hook

            ctx.transport.resp_headers['Content-Length'] = str(len(ctx.transport.wsdl))
            start_response(HTTP_200, ctx.transport.resp_headers.items())

            return [ctx.transport.wsdl]

        except Exception, e:
            logger.exception(e)
            ctx.transport.wsdl_error = e

            # implementation hook
            self.event_manager.fire_event('wsdl_exception', ctx)

            start_response(HTTP_500, ctx.transport.resp_headers.items())

            return [""]

    def handle_error(self, ctx, error, start_response):
        if ctx.transport.resp_code is None:
            ctx.transport.resp_code = \
                self.app.out_protocol.fault_to_http_response_code(error)

        self.get_out_string(ctx)
        ctx.out_string = [''.join(ctx.out_string)]

        ctx.transport.resp_headers['Content-Length'] = str(len(ctx.out_string[0]))
        self.event_manager.fire_event('wsgi_exception', ctx)

        start_response(ctx.transport.resp_code,
                                             ctx.transport.resp_headers.items())
        return ctx.out_string

    def handle_rpc(self, req_env, start_response):
        initial_ctx = WsgiMethodContext(self.app, req_env,
                                                self.app.out_protocol.mime_type)

        # implementation hook
        self.event_manager.fire_event('wsgi_call', initial_ctx)
        initial_ctx.in_string, in_string_charset = reconstruct_wsgi_request(req_env)

        # note that in fanout mode, only the response from the last
        # call will be returned.
        for ctx in self.generate_contexts(initial_ctx, in_string_charset):
            if ctx.in_error:
                return self.handle_error(ctx, ctx.in_error, start_response)

            self.get_in_object(ctx)
            if ctx.in_error:
                logger.error(ctx.in_error)
                return self.handle_error(ctx, ctx.in_error, start_response)

            self.get_out_object(ctx)
            if ctx.out_error:
                return self.handle_error(ctx, ctx.out_error, start_response)

            if ctx.transport.resp_code is None:
                ctx.transport.resp_code = HTTP_200

            self.get_out_string(ctx)

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

        # implementation hook
        self.event_manager.fire_event('wsgi_return', ctx)

        # the client has not set a content-length, so we delete it as the input
        # is just an iterable.
        if ctx.transport.resp_headers['Content-Length'] is None:
            del ctx.transport.resp_headers['Content-Length']

        # initiate the response
        start_response(ctx.transport.resp_code, ctx.transport.resp_headers.items())

        return ctx.out_string
