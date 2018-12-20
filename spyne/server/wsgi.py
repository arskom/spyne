
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


"""
A server that uses http as transport via wsgi. It doesn't contain any server
logic.
"""

import logging
logger = logging.getLogger(__name__)

import cgi
import threading
import itertools

from spyne.util.six.moves.urllib.parse import unquote, quote

try:
    from werkzeug.formparser import parse_form_data
except ImportError as _import_error:
    _local_import_error = _import_error
    def parse_form_data(*args, **kwargs):
        raise _local_import_error

from spyne.util.six.moves.http_cookies import SimpleCookie

from spyne.application import get_fault_string_from_exception
from spyne.auxproc import process_contexts
from spyne.error import RequestTooLongError
from spyne.model.binary import File
from spyne.model.fault import Fault
from spyne.protocol.http import HttpRpc
from spyne.server.http import HttpBase
from spyne.server.http import HttpMethodContext
from spyne.server.http import HttpTransportContext
from spyne.util import reconstruct_url
from spyne.util.odict import odict

from spyne.const.ansi_color import LIGHT_GREEN
from spyne.const.ansi_color import END_COLOR
from spyne.const.http import HTTP_200
from spyne.const.http import HTTP_404
from spyne.const.http import HTTP_500


try:
    from spyne.protocol.soap.mime import apply_mtom
except ImportError as _import_error:
    _local_import_error = _import_error
    def apply_mtom(*args, **kwargs):
        raise _local_import_error


def _parse_qs(qs):
    pairs = (s2 for s1 in qs.split('&') for s2 in s1.split(';'))
    retval = odict()

    for name_value in pairs:
        if name_value is None or len(name_value) == 0:
            continue
        nv = name_value.split('=', 1)

        if len(nv) != 2:
            # Handle case of a control-name with no equal sign
            nv.append(None)

        name = unquote(nv[0].replace('+', ' '))

        value = None
        if nv[1] is not None:
            value = unquote(nv[1].replace('+', ' '))

        l = retval.get(name, None)
        if l is None:
            l = retval[name] = []
        l.append(value)

    return retval


def _get_http_headers(req_env):
    retval = {}

    for k, v in req_env.items():
        if k.startswith("HTTP_"):
            retval[k[5:].lower()]= [v]

    return retval


def _gen_http_headers(headers):
    retval = []

    for k,v in headers.items():
        if isinstance(v, (list, tuple)):
            for v2 in v:
                retval.append((k, v2))
        else:
            retval.append((k, v))

    return retval


class WsgiTransportContext(HttpTransportContext):
    """The class that is used in the transport attribute of the
    :class:`WsgiMethodContext` class."""

    def __init__(self, parent, transport, req_env, content_type):
        super(WsgiTransportContext, self).__init__(parent, transport,
                                                          req_env, content_type)

        self.req_env = self.req
        """WSGI Request environment"""

        self.req_method = req_env.get('REQUEST_METHOD', None)
        """HTTP Request verb, as a convenience to users."""

    def get_path(self):
        return self.req_env['PATH_INFO']

    def get_path_and_qs(self):
        retval = quote(self.req_env.get('PATH_INFO', ''))
        qs = self.req_env.get('QUERY_STRING', None)
        if qs is not None:
            retval += '?' + qs
        return retval

    def get_cookie(self, key):
        cookie_string = self.req_env.get('HTTP_COOKIE', None)
        if cookie_string is None:
            return

        cookie = SimpleCookie()
        cookie.load(cookie_string)

        return cookie.get(key, None).value

    def get_request_method(self):
        return self.req['REQUEST_METHOD'].upper()

    def get_request_content_type(self):
        return self.req.get("CONTENT_TYPE", None)


class WsgiMethodContext(HttpMethodContext):
    """The WSGI-Specific method context. WSGI-Specific information is stored in
    the transport attribute using the :class:`WsgiTransportContext` class.
    """

    def __init__(self, transport, req_env, content_type):
        super(WsgiMethodContext, self).__init__(transport, req_env, content_type)

        self.transport = WsgiTransportContext(self, transport, req_env, content_type)
        """Holds the WSGI-specific information"""


class WsgiApplication(HttpBase):
    """A `PEP-3333 <http://www.python.org/dev/peps/pep-3333>`_
    compliant callable class.

    If you want to have a hard-coded URL in the wsdl document, this is how to do
    it: ::

        wsgi_app = WsgiApplication(...)
        wsgi_app.doc.wsdl11.build_interface_document("http://example.com")

    This is not strictly necessary -- if you don't do this, Spyne will get the
    URL from the first request, build the wsdl on-the-fly and cache it as a
    string in memory for later requests. However, if you want to make sure
    you only have this url on the WSDL, this is how to do it. Note that if
    your client takes the information in the Wsdl document seriously (not all
    do), all requests will go to the designated url above even when you get the
    Wsdl from another location, which can make testing a bit difficult. Use in
    moderation.

    Supported events:
        * ``wsdl``
            Called right before the wsdl data is returned to the client.

        * ``wsdl_exception``
            Called right after an exception is thrown during wsdl generation.
            The exception object is stored in ctx.transport.wsdl_error
            attribute.

        * ``wsgi_call``
            Called first when the incoming http request is identified as a rpc
            request.

        * ``wsgi_return``
            Called right before the output stream is returned to the WSGI
            handler.

        * ``wsgi_exception``
            Called right before returning the exception to the client.

        * ``wsgi_close``
            Called after the whole data has been returned to the client. It's
            called both from success and error cases.
    """

    def __init__(self, app, chunked=True, max_content_length=2 * 1024 * 1024,
                                                         block_length=8 * 1024):
        super(WsgiApplication, self).__init__(app, chunked, max_content_length,
                                                                   block_length)

        self._mtx_build_interface_document = threading.Lock()

        self._wsdl = None
        if self.doc.wsdl11 is not None:
            self._wsdl = self.doc.wsdl11.get_interface_document()

    def __call__(self, req_env, start_response, wsgi_url=None):
        """This method conforms to the WSGI spec for callable wsgi applications
        (PEP 333). It looks in environ['wsgi.input'] for a fully formed rpc
        message envelope, will deserialize the request parameters and call the
        method on the object returned by the get_handler() method.
        """

        url = wsgi_url
        if url is None:
            url = reconstruct_url(req_env).split('.wsdl')[0]

        if self.is_wsdl_request(req_env):
            return self.handle_wsdl_request(req_env, start_response, url)

        else:
            return self.handle_rpc(req_env, start_response)

    def is_wsdl_request(self, req_env):
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


    def handle_wsdl_request(self, req_env, start_response, url):
        ctx = WsgiMethodContext(self, req_env, 'text/xml; charset=utf-8')

        if self.doc.wsdl11 is None:
            start_response(HTTP_404,
                                  _gen_http_headers(ctx.transport.resp_headers))
            return [HTTP_404]

        if self._wsdl is None:
            self._wsdl = self.doc.wsdl11.get_interface_document()

        ctx.transport.wsdl = self._wsdl

        if ctx.transport.wsdl is None:
            try:
                self._mtx_build_interface_document.acquire()

                ctx.transport.wsdl = self._wsdl

                if ctx.transport.wsdl is None:
                    self.doc.wsdl11.build_interface_document(url)
                    ctx.transport.wsdl = self._wsdl = \
                                        self.doc.wsdl11.get_interface_document()

            except Exception as e:
                logger.exception(e)
                ctx.transport.wsdl_error = e

                self.event_manager.fire_event('wsdl_exception', ctx)

                start_response(HTTP_500,
                                  _gen_http_headers(ctx.transport.resp_headers))

                return [HTTP_500]

            finally:
                self._mtx_build_interface_document.release()

        self.event_manager.fire_event('wsdl', ctx)

        ctx.transport.resp_headers['Content-Length'] = \
                                                    str(len(ctx.transport.wsdl))
        start_response(HTTP_200, _gen_http_headers(ctx.transport.resp_headers))

        retval = ctx.transport.wsdl

        ctx.close()

        return [retval]

    def handle_error(self, p_ctx, others, error, start_response):
        """Serialize errors to an iterable of strings and return them.

        :param p_ctx: Primary (non-aux) context.
        :param others: List if auxiliary contexts (can be empty).
        :param error: One of ctx.{in,out}_error.
        :param start_response: See the WSGI spec for more info.
        """

        if p_ctx.transport.resp_code is None:
            p_ctx.transport.resp_code = \
                p_ctx.out_protocol.fault_to_http_response_code(error)

        self.get_out_string(p_ctx)
        p_ctx.out_string = [b''.join(p_ctx.out_string)]

        p_ctx.transport.resp_headers['Content-Length'] = \
                                                   str(len(p_ctx.out_string[0]))
        self.event_manager.fire_event('wsgi_exception', p_ctx)

        start_response(p_ctx.transport.resp_code,
                                _gen_http_headers(p_ctx.transport.resp_headers))

        try:
            process_contexts(self, others, p_ctx, error=error)
        except Exception as e:
            # Report but ignore any exceptions from auxiliary methods.
            logger.exception(e)

        return itertools.chain(p_ctx.out_string, self.__finalize(p_ctx))

    def handle_rpc(self, req_env, start_response):
        initial_ctx = WsgiMethodContext(self, req_env,
                                                self.app.out_protocol.mime_type)

        self.event_manager.fire_event('wsgi_call', initial_ctx)
        initial_ctx.in_string, in_string_charset = \
                                        self.__reconstruct_wsgi_request(req_env)

        contexts = self.generate_contexts(initial_ctx, in_string_charset)
        p_ctx, others = contexts[0], contexts[1:]

        if p_ctx.in_error:
            return self.handle_error(p_ctx, others, p_ctx.in_error,
                                                                 start_response)

        self.get_in_object(p_ctx)
        if p_ctx.in_error:
            logger.error(p_ctx.in_error)
            return self.handle_error(p_ctx, others, p_ctx.in_error,
                                                                 start_response)

        self.get_out_object(p_ctx)
        if p_ctx.out_error:
            return self.handle_error(p_ctx, others, p_ctx.out_error,
                                                                 start_response)

        if p_ctx.transport.resp_code is None:
            p_ctx.transport.resp_code = HTTP_200

        try:
            self.get_out_string(p_ctx)

        except Exception as e:
            logger.exception(e)
            p_ctx.out_error = Fault('Server', get_fault_string_from_exception(e))
            return self.handle_error(p_ctx, others, p_ctx.out_error,
                                                                 start_response)


        if isinstance(p_ctx.out_protocol, HttpRpc) and \
                                               p_ctx.out_header_doc is not None:
            p_ctx.transport.resp_headers.update(p_ctx.out_header_doc)

        if p_ctx.descriptor and p_ctx.descriptor.mtom:
            # when there is more than one return type, the result is
            # encapsulated inside a list. when there's just one, the result
            # is returned in a non-encapsulated form. the apply_mtom always
            # expects the objects to be inside an iterable, hence the
            # following test.
            out_type_info = p_ctx.descriptor.out_message._type_info
            if len(out_type_info) == 1:
                p_ctx.out_object = [p_ctx.out_object]

            p_ctx.transport.resp_headers, p_ctx.out_string = apply_mtom(
                    p_ctx.transport.resp_headers, p_ctx.out_string,
                    p_ctx.descriptor.out_message._type_info.values(),
                    p_ctx.out_object,
                )

        self.event_manager.fire_event('wsgi_return', p_ctx)

        if self.chunked:
            # the user has not set a content-length, so we delete it as the
            # input is just an iterable.
            if 'Content-Length' in p_ctx.transport.resp_headers:
                del p_ctx.transport.resp_headers['Content-Length']
        else:
            p_ctx.out_string = [''.join(p_ctx.out_string)]

        # if the out_string is a generator function, this hack makes the user
        # code run until first yield, which lets it set response headers and
        # whatnot before calling start_response. Is there a better way?
        try:
            len(p_ctx.out_string)  # generator?

            # nope
            p_ctx.transport.resp_headers['Content-Length'] = \
                                    str(sum([len(a) for a in p_ctx.out_string]))

            start_response(p_ctx.transport.resp_code,
                                _gen_http_headers(p_ctx.transport.resp_headers))

            retval = itertools.chain(p_ctx.out_string, self.__finalize(p_ctx))

        except TypeError:
            retval_iter = iter(p_ctx.out_string)
            try:
                first_chunk = next(retval_iter)
            except StopIteration:
                first_chunk = ''

            start_response(p_ctx.transport.resp_code,
                                _gen_http_headers(p_ctx.transport.resp_headers))

            retval = itertools.chain([first_chunk], retval_iter,
                                                        self.__finalize(p_ctx))

        try:
            process_contexts(self, others, p_ctx, error=None)
        except Exception as e:
            # Report but ignore any exceptions from auxiliary methods.
            logger.exception(e)

        return retval

    def __finalize(self, p_ctx):
        p_ctx.close()
        self.event_manager.fire_event('wsgi_close', p_ctx)

        return ()

    def __reconstruct_wsgi_request(self, http_env):
        """Reconstruct http payload using information in the http header."""

        content_type = http_env.get("CONTENT_TYPE")
        charset = None
        if content_type is not None:
            # fyi, here's what the parse_header function returns:
            # >>> import cgi; cgi.parse_header("text/xml; charset=utf-8")
            # ('text/xml', {'charset': 'utf-8'})
            content_type = cgi.parse_header(content_type)
            charset = content_type[1].get('charset', None)

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
            if data is None or len(data) == 0:
                break

            bytes_read += len(data)

            yield data

    def decompose_incoming_envelope(self, prot, ctx, message):
        """This function is only called by the HttpRpc protocol to have the wsgi
        environment parsed into ``ctx.in_body_doc`` and ``ctx.in_header_doc``.
        """

        params = {}
        wsgi_env = ctx.in_document

        if self.has_patterns:
            # http://legacy.python.org/dev/peps/pep-0333/#url-reconstruction
            domain = wsgi_env.get('HTTP_HOST', None)
            if domain is None:
                domain = wsgi_env['SERVER_NAME']
            else:
                domain = domain.partition(':')[0] # strip port info

            params = self.match_pattern(ctx,
                    wsgi_env.get('REQUEST_METHOD', ''),
                    wsgi_env.get('PATH_INFO', ''),
                    domain,
                )

        if ctx.method_request_string is None:
            ctx.method_request_string = '{%s}%s' % (
                                    prot.app.interface.get_tns(),
                                    wsgi_env['PATH_INFO'].split('/')[-1])

        logger.debug("%sMethod name: %r%s" % (LIGHT_GREEN,
                                          ctx.method_request_string, END_COLOR))

        ctx.in_header_doc = _get_http_headers(wsgi_env)
        ctx.in_body_doc = _parse_qs(wsgi_env['QUERY_STRING'])

        for k, v in params.items():
             if k in ctx.in_body_doc:
                 ctx.in_body_doc[k].extend(v)
             else:
                 ctx.in_body_doc[k] = list(v)

        verb = wsgi_env['REQUEST_METHOD'].upper()
        if verb in ('POST', 'PUT', 'PATCH'):
            stream, form, files = parse_form_data(wsgi_env,
                                             stream_factory=prot.stream_factory)

            for k, v in form.lists():
                val = ctx.in_body_doc.get(k, [])
                val.extend(v)
                ctx.in_body_doc[k] = val

            for k, v in files.items():
                val = ctx.in_body_doc.get(k, [])

                mime_type = v.headers.get('Content-Type',
                                                     'application/octet-stream')

                path = getattr(v.stream, 'name', None)
                if path is None:
                    val.append(File.Value(name=v.filename, type=mime_type,
                                                    data=[v.stream.getvalue()]))
                else:
                    v.stream.seek(0)
                    val.append(File.Value(name=v.filename, type=mime_type,
                                                    path=path, handle=v.stream))

                ctx.in_body_doc[k] = val

            for k, v in ctx.in_body_doc.items():
                if v == ['']:
                    ctx.in_body_doc[k] = [None]
