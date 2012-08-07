
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

"""A server transport uses http as transport, and wsgi as bridge api."""

import logging
logger = logging.getLogger(__name__)

import cgi
import threading
import itertools

from spyne.auxproc import process_contexts
from spyne.model.binary import File

try:
    from urlparse import parse_qs
except ImportError: # Python 3
    from urllib.parse import parse_qs

try:
    from werkzeug.formparser import parse_form_data
except ImportError:
    pass

from spyne.server.http import HttpMethodContext
from spyne.server.http import HttpTransportContext

from spyne.error import RequestTooLongError
from spyne.error import ResourceNotFoundError

from spyne.protocol.soap.mime import apply_mtom
from spyne.util import reconstruct_url
from spyne.server.http import HttpBase

from spyne.const.ansi_color import LIGHT_GREEN
from spyne.const.ansi_color import END_COLOR
from spyne.const.http import HTTP_200
from spyne.const.http import HTTP_405
from spyne.const.http import HTTP_500


def _get_http_headers(req_env):
    retval = {}

    for k, v in req_env.items():
        if k.startswith("HTTP_"):
            retval[k[5:].lower()]= [v]

    return retval


class WsgiTransportContext(HttpTransportContext):
    """The class that is used in the transport attribute of the
    :class:`WsgiMethodContext` class."""

    def __init__(self, transport, req_env, content_type):
        HttpTransportContext.__init__(self, transport, req_env, content_type)

        self.req_env = self.req
        """WSGI Request environment"""

        self.req_method = req_env.get('REQUEST_METHOD', None)
        """HTTP Request verb, as a convenience to users."""


class WsgiMethodContext(HttpMethodContext):
    """The WSGI-Specific method context. WSGI-Specific information is stored in
    the transport attribute using the :class:`WsgiTransportContext` class.
    """

    def __init__(self, transport, req_env, content_type):
        HttpMethodContext.__init__(self, transport, req_env, content_type)

        self.transport = WsgiTransportContext(transport, req_env, content_type)
        """Holds the WSGI-specific information"""


class WsgiApplication(HttpBase):
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


    def __init__(self, app, chunked=True):
        HttpBase.__init__(self, app, chunked)

        self._allowed_http_verbs = app.in_protocol.allowed_http_verbs
        self._verb_handlers = {
            "GET": self.handle_rpc,
            "POST": self.handle_rpc,
        }
        self._mtx_build_interface_document = threading.Lock()
        self._wsdl = None
        http_routes = app.interface.http_routes
        if hasattr(self.app.in_protocol, "has_any_http_routes"):
            if self.app.in_protocol.has_any_http_routes(
                                            self.app.interface.service_method_map):
                from werkzeug.routing import Rule
                from werkzeug.exceptions import NotFound

                for k,v in self.app.interface.service_method_map.items():
                    p_service_class, p_method_descriptor = v[0]
                    for r in p_method_descriptor.http_routes:
                        # Adds url patterns and sets endpoint to method name
                        http_routes.add(Rule(r.rule, endpoint=k, methods=r.methods))

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

        elif not (self._allowed_http_verbs is None or
               verb in self._allowed_http_verbs or verb in self._verb_handlers):
            start_response(HTTP_405, [
                ('Content-Type', ''),
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
            req_env['REQUEST_METHOD'].upper() == 'GET'
            and (
                   req_env['QUERY_STRING'].lower() == 'wsdl'
                or req_env['PATH_INFO'].endswith('.wsdl')
            )
        )

    def __handle_wsdl_request(self, req_env, start_response, url):
        ctx = WsgiMethodContext(self, req_env, 'text/xml; charset=utf-8')

        ctx.transport.wsdl = self._wsdl

        if ctx.transport.wsdl is None:
            try:
                self._mtx_build_interface_document.acquire()

                ctx.transport.wsdl = self._wsdl

                if ctx.transport.wsdl is None:
                    from spyne.interface.wsdl import Wsdl11
                    wsdl = Wsdl11(self.app.interface)
                    wsdl.build_interface_document(url)
                    ctx.transport.wsdl = self._wsdl = wsdl.get_interface_document()

            except Exception, e:
                logger.exception(e)
                ctx.transport.wsdl_error = e

                # implementation hook
                self.event_manager.fire_event('wsdl_exception', ctx)

                start_response(HTTP_500, ctx.transport.resp_headers.items())

                return [""]

            finally:
                self._mtx_build_interface_document.release()

        self.event_manager.fire_event('wsdl', ctx)

        ctx.transport.resp_headers['Content-Length'] = \
                                                str(len(ctx.transport.wsdl))
        start_response(HTTP_200, ctx.transport.resp_headers.items())

        return [ctx.transport.wsdl]

    def handle_error(self, p_ctx, others, error, start_response):
        if p_ctx.transport.resp_code is None:
            p_ctx.transport.resp_code = \
                self.app.out_protocol.fault_to_http_response_code(error)

        self.get_out_string(p_ctx)
        p_ctx.out_string = [''.join(p_ctx.out_string)]

        p_ctx.transport.resp_headers['Content-Length'] = str(len(p_ctx.out_string[0]))
        self.event_manager.fire_event('wsgi_exception', p_ctx)

        start_response(p_ctx.transport.resp_code,
                                             p_ctx.transport.resp_headers.items())

        try:
            process_contexts(self, others, p_ctx, error=error)
        except Exception,e:
            # Report but ignore any exceptions from auxiliary methods.
            logger.exception(e)

        return p_ctx.out_string

    def handle_rpc(self, req_env, start_response):
        initial_ctx = WsgiMethodContext(self, req_env,
                                                self.app.out_protocol.mime_type)

        # implementation hook
        self.event_manager.fire_event('wsgi_call', initial_ctx)
        initial_ctx.in_string, in_string_charset = \
                                        self.__reconstruct_wsgi_request(req_env)

        contexts = self.generate_contexts(initial_ctx, in_string_charset)
        p_ctx, others = contexts[0], contexts[1:]

        if p_ctx.in_error:
            return self.handle_error(p_ctx, others, p_ctx.in_error, start_response)

        self.get_in_object(p_ctx)
        if p_ctx.in_error:
            logger.error(p_ctx.in_error)
            return self.handle_error(p_ctx, others, p_ctx.in_error, start_response)

        self.get_out_object(p_ctx)
        if p_ctx.out_error:
            return self.handle_error(p_ctx, others, p_ctx.out_error, start_response)

        if p_ctx.transport.resp_code is None:
            p_ctx.transport.resp_code = HTTP_200

        self.get_out_string(p_ctx)

        if p_ctx.descriptor and p_ctx.descriptor.mtom:
            # when there is more than one return type, the result is
            # encapsulated inside a list. when there's just one, the result
            # is returned in a non-encapsulated form. the apply_mtom always
            # expects the objects to be inside an iterable, hence the
            # following test.
            out_type_info = p_ctx.descriptor.out_message._type_info
            if len(out_type_info) == 1:
                out_object = [out_object]

            p_ctx.transport.resp_headers, p_ctx.out_string = apply_mtom(
                    p_ctx.transport.resp_headers, p_ctx.out_string,
                    p_ctx.descriptor.out_message._type_info.values(),
                    out_object
                )

        # implementation hook
        self.event_manager.fire_event('wsgi_return', p_ctx)

        if self.chunked:
            # the client has not set a content-length, so we delete it as the
            # input is just an iterable.
            if 'Content-Length' in p_ctx.transport.resp_headers:
                del p_ctx.transport.resp_headers['Content-Length']
        else:
            p_ctx.out_string = [''.join(p_ctx.out_string)]

        # if the out_string is a generator function, this hack lets the user
        # code run until first yield, which lets it set response headers and
        # whatnot before calling start_response. Yes it causes an additional
        # copy of the first fragment of the response to be made, but if you know
        # a better way of having generator functions execute until first yield,
        # just let us know.
        try:
            len(p_ctx.out_string) # iterator?
            # nope

            p_ctx.transport.resp_headers['Content-Length'] = \
                                 str(sum([len(a) for a in p_ctx.out_string]))

            start_response(p_ctx.transport.resp_code,
                                            p_ctx.transport.resp_headers.items())

            retval = p_ctx.out_string

        except TypeError:
            retval_iter = iter(p_ctx.out_string)
            retval = retval_iter.next()

            start_response(p_ctx.transport.resp_code,
                                            p_ctx.transport.resp_headers.items())

            retval = itertools.chain([retval], retval_iter)

        try:
            process_contexts(self, others, p_ctx, error=None)
        except Exception, e:
            # Report but ignore any exceptions from auxiliary methods.
            logger.exception(e)

        return retval
    

    def __reconstruct_wsgi_request(self, http_env):
        """Reconstruct http payload using information in the http header."""

        # fyi, here's what the parse_header function returns:
        # >>> import cgi; cgi.parse_header("text/xml; charset=utf-8")
        # ('text/xml', {'charset': 'utf-8'})
        content_type = http_env.get("CONTENT_TYPE")
        if content_type is None:
            charset = 'utf-8'
        else:
            content_type = cgi.parse_header(content_type)
            charset = content_type[1].get('charset', 'utf-8')

        return self.__wsgi_input_to_iterable(http_env), charset

    def __wsgi_input_to_iterable(self, http_env):
        istream = http_env.get('wsgi.input')

        length = str(http_env.get('CONTENT_LENGTH', self.max_content_length))
        if len(length) == 0:
            length = 0
        else:
            length = int(length)

        if length > self.max_content_length:
            raise RequestTooLongError()
        bytes_read = 0

        while bytes_read < length:
            bytes_to_read = min(self.block_length, length - bytes_read)

            if bytes_to_read + bytes_read > self.max_content_length:
                raise RequestTooLongError()

            data = istream.read(bytes_to_read)
            if data is None or data == '':
                break

            bytes_read += len(data)

            yield data

    @staticmethod
    def decompose_incoming_envelope(prot, ctx, message):
        """This function is only called by the HttpRpc protocol to have the wsgi
        environment parsed into ``ctx.in_body_doc`` and ``ctx.in_header_doc``.
        """
        if prot.has_any_http_routes(ctx.app.interface.service_method_map):
            from werkzeug.exceptions import NotFound
            if prot.map_adapter is None:
                # If url map is not binded before, binds url_map
                req_env = ctx.transport.req_env
                prot.map_adapter = ctx.app.in_protocol.get_map_adapter(
                                                    req_env['SERVER_NAME'], "/")

                for k,v in ctx.app.interface.service_method_map.items():
                    #Compiles url patterns
                    p_service_class, p_method_descriptor = v[0]
                    for r in ctx.app.interface.http_routes.iter_rules():
                        params = {}
                        if r.endpoint == k:
                            for pk,pv in p_method_descriptor.in_message.\
                                                                _type_info.items():

                                if pk in r.rule:
                                    from spyne.model.primitive import String
                                    from spyne.model.primitive import Unicode
                                    from spyne.model.primitive import Decimal

                                    if issubclass(pv, Unicode):
                                        params[pk] = ""
                                    elif issubclass(pv, Decimal):
                                        params[pk] = 0

                            prot.map_adapter.build(r.endpoint, params)

            try:
                #If PATH_INFO matches a url, Set method_request_string to mrs
                mrs, params = prot.map_adapter.match(ctx.in_document["PATH_INFO"],
                                                ctx.in_document["REQUEST_METHOD"])
                ctx.method_request_string = mrs
                for k in params:
                    params[k] = [params[k]]

            except NotFound:
                # Else set method_request_string normally
                params = {}
                ctx.method_request_string = '{%s}%s' % (prot.app.interface.get_tns(),
                                  ctx.in_document['PATH_INFO'].split('/')[-1])
        else:
            params = {}
            ctx.method_request_string = '{%s}%s' % (prot.app.interface.get_tns(),
                              ctx.in_document['PATH_INFO'].split('/')[-1])

        logger.debug("%sMethod name: %r%s" % (LIGHT_GREEN,
                                          ctx.method_request_string, END_COLOR))

        ctx.in_header_doc = _get_http_headers(ctx.in_document)
        ctx.in_body_doc = parse_qs(ctx.in_document['QUERY_STRING'])
        ctx.in_body_doc.update(params)

        if ctx.in_document['REQUEST_METHOD'].upper() in ('POST', 'PUT', 'PATCH'):
            stream, form, files = parse_form_data(ctx.in_document,
                                        stream_factory=prot.stream_factory)

            for k, v in form.lists():
                val = ctx.in_body_doc.get(k, [])
                val.extend(v)
                ctx.in_body_doc[k] = val

            for k, v in files.items():
                val = ctx.in_body_doc.get(k, [])

                mime_type = v.headers.get('Content-Type', 'application/octet-stream')

                path = getattr(v.stream, 'name', None)
                if path is None:
                    val.append(File(name=v.filename, type=mime_type,
                                                    data=[v.stream.getvalue()]))
                else:
                    v.stream.seek(0)
                    val.append(File(name=v.filename, type=mime_type, path=path,
                                                               handle=v.stream))

                ctx.in_body_doc[k] = val
