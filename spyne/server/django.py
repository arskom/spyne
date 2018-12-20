# encoding: utf-8
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

"""The ``spyne.server.django`` module contains a Django-compatible Http
transport. It's a thin wrapper around
:class:`spyne.server.wsgi.WsgiApplication`.

This module is EXPERIMENTAL. Tests and patches are welcome.
"""

from __future__ import absolute_import

import logging
logger = logging.getLogger(__name__)

from functools import update_wrapper

from spyne.application import get_fault_string_from_exception, Application
from spyne.auxproc import process_contexts
from spyne.interface import AllYourInterfaceDocuments
from spyne.model.fault import Fault
from spyne.protocol.soap import Soap11
from spyne.protocol.http import HttpRpc
from spyne.server.http import HttpBase, HttpMethodContext, HttpTransportContext
from spyne.server.wsgi import WsgiApplication
from spyne.util import _bytes_join

from django.http import HttpResponse, HttpResponseNotAllowed, Http404
from django.views.decorators.csrf import csrf_exempt

try:
    from django.http import StreamingHttpResponse
except ImportError as _import_error:
    _local_import_error = _import_error
    def StreamingHttpResponse(*args, **kwargs):
        raise _local_import_error

class DjangoApplication(WsgiApplication):
    """You should use this for regular RPC."""

    HttpResponseObject = HttpResponse

    # noinspection PyMethodOverriding
    # because this is VERY similar to a Wsgi app
    # but not that much.
    def __call__(self, request):
        retval = self.HttpResponseObject()

        def start_response(status, headers):
            # Status is one of spyne.const.http
            status, reason = status.split(' ', 1)

            retval.status_code = int(status)
            for header, value in headers:
                retval[header] = value

        environ = request.META.copy()

        # FIXME: No idea what these two did.
        #        They were commented out to fix compatibility issues with
        #        Django-1.2.x
        # See http://github.com/arskom/spyne/issues/222.

        # If you don't override wsgi.input django and spyne will read
        # the same buffer twice. If django read whole buffer spyne
        # would hang waiting for extra request data. Use DjangoServer instead
        # of monkeypatching wsgi.inpu.

        #environ['wsgi.input'] = request
        #environ['wsgi.multithread'] = False

        response = WsgiApplication.__call__(self, environ, start_response)
        self.set_response(retval, response)

        return retval

    def set_response(self, retval, response):
        retval.content = _bytes_join(response, b"")


class StreamingDjangoApplication(DjangoApplication):
    """You should use this when you're generating HUGE data as response.

    New in Django 1.5.
    """

    HttpResponseObject = StreamingHttpResponse

    def set_response(self, retval, response):
        retval.streaming_content = response


class DjangoHttpTransportContext(HttpTransportContext):
    def get_path(self):
        return self.req.path

    def get_request_method(self):
        return self.req.method

    def get_request_content_type(self):
        return self.req.META['CONTENT_TYPE']

    def get_path_and_qs(self):
        return self.req.get_full_path()

    def get_cookie(self, key):
        return self.req.COOKIES[key]


class DjangoHttpMethodContext(HttpMethodContext):
    default_transport_context = DjangoHttpTransportContext


class DjangoServer(HttpBase):
    """Server talking in Django request/response objects."""

    def __init__(self, app, chunked=False, cache_wsdl=True):
        super(DjangoServer, self).__init__(app, chunked=chunked)
        self._wsdl = None
        self._cache_wsdl = cache_wsdl

    def handle_rpc(self, request, *args, **kwargs):
        """Handle rpc request.

        :params request: Django HttpRequest instance.
        :returns: HttpResponse instance.

        """
        contexts = self.get_contexts(request)
        p_ctx, others = contexts[0], contexts[1:]

        if p_ctx.in_error:
            return self.handle_error(p_ctx, others, p_ctx.in_error)

        self.get_in_object(p_ctx)
        if p_ctx.in_error:
            logger.error(p_ctx.in_error)
            return self.handle_error(p_ctx, others, p_ctx.in_error)

        self.get_out_object(p_ctx)
        if p_ctx.out_error:
            return self.handle_error(p_ctx, others, p_ctx.out_error)

        try:
            self.get_out_string(p_ctx)

        except Exception as e:
            logger.exception(e)
            p_ctx.out_error = Fault('Server',
                                    get_fault_string_from_exception(e))
            return self.handle_error(p_ctx, others, p_ctx.out_error)

        have_protocol_headers = (isinstance(p_ctx.out_protocol, HttpRpc) and
                                 p_ctx.out_header_doc is not None)

        if have_protocol_headers:
            p_ctx.transport.resp_headers.update(p_ctx.out_header_doc)

        if p_ctx.descriptor and p_ctx.descriptor.mtom:
            raise NotImplementedError

        if self.chunked:
            response = StreamingHttpResponse(p_ctx.out_string)
        else:
            response = HttpResponse(b''.join(p_ctx.out_string))

        return self.response(response, p_ctx, others)

    def handle_wsdl(self, request, *args, **kwargs):
        """Return services WSDL."""
        ctx = HttpMethodContext(self, request,
                                'text/xml; charset=utf-8')

        if self.doc.wsdl11 is None:
            raise Http404('WSDL is not available')

        if self._wsdl is None:
            # Interface document building is not thread safe so we don't use
            # server interface document shared between threads. Instead we
            # create and build interface documents in current thread. This
            # section can be safely repeated in another concurrent thread.
            doc = AllYourInterfaceDocuments(self.app.interface)
            doc.wsdl11.build_interface_document(request.build_absolute_uri())
            wsdl = doc.wsdl11.get_interface_document()

            if self._cache_wsdl:
                self._wsdl = wsdl
        else:
            wsdl = self._wsdl

        ctx.transport.wsdl = wsdl

        response = HttpResponse(ctx.transport.wsdl)
        return self.response(response, ctx, ())

    def handle_error(self, p_ctx, others, error):
        """Serialize errors to an iterable of strings and return them.

        :param p_ctx: Primary (non-aux) context.
        :param others: List if auxiliary contexts (can be empty).
        :param error: One of ctx.{in,out}_error.
        """

        if p_ctx.transport.resp_code is None:
            p_ctx.transport.resp_code = \
                           p_ctx.out_protocol.fault_to_http_response_code(error)

        self.get_out_string(p_ctx)
        resp = HttpResponse(b''.join(p_ctx.out_string))
        return self.response(resp, p_ctx, others, error)

    def get_contexts(self, request):
        """Generate contexts for rpc request.

        :param request: Django HttpRequest instance.
        :returns: generated contexts
        """

        initial_ctx = DjangoHttpMethodContext(self, request,
                                                self.app.out_protocol.mime_type)

        initial_ctx.in_string = [request.body]
        return self.generate_contexts(initial_ctx)

    def response(self, response, p_ctx, others, error=None):
        """Populate response with transport headers and finalize it.

        :param response: Django HttpResponse.
        :param p_ctx: Primary (non-aux) context.
        :param others: List if auxiliary contexts (can be empty).
        :param error: One of ctx.{in,out}_error.
        :returns: Django HttpResponse

        """
        for h, v in p_ctx.transport.resp_headers.items():
            if v is not None:
                response[h] = v

        if p_ctx.transport.resp_code:
            response.status_code = int(p_ctx.transport.resp_code[:3])

        try:
            process_contexts(self, others, p_ctx, error=error)
        except Exception as e:
            # Report but ignore any exceptions from auxiliary methods.
            logger.exception(e)

        p_ctx.close()

        return response


class DjangoView(object):
    """Represent spyne service as Django class based view."""

    application = None
    server = None
    services = ()
    tns = 'spyne.application'
    name = 'Application'
    in_protocol = Soap11(validator='lxml')
    out_protocol = Soap11()
    interface = None
    chunked = False
    cache_wsdl = True

    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head',
                         'options', 'trace']

    def __init__(self, server, **kwargs):
        self.server = server

        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    def as_view(cls, **initkwargs):
        """Register application, server and create new view.

        :returns: callable view function
        """

        # sanitize keyword arguments
        for key in initkwargs:
            if key in cls.http_method_names:
                raise TypeError("You tried to pass in the %s method name as a "
                                "keyword argument to %s(). Don't do that."
                                % (key, cls.__name__))
            if not hasattr(cls, key):
                raise TypeError("%s() received an invalid keyword %r. as_view "
                                "only accepts arguments that are already "
                                "attributes of the class." % (cls.__name__,
                                                              key))

        def get(key):
            value = initkwargs.get(key)
            return value if value is not None else getattr(cls, key)

        application = get('application') or Application(
            services=get('services'),
            tns=get('tns'),
            name=get('name'),
            in_protocol=get('in_protocol'),
            out_protocol=get('out_protocol'),
        )
        server = get('server') or DjangoServer(application,
                                               chunked=get('chunked'),
                                               cache_wsdl=get('cache_wsdl'))

        def view(request, *args, **kwargs):
            self = cls(server=server, **initkwargs)
            if hasattr(self, 'get') and not hasattr(self, 'head'):
                self.head = self.get
            self.request = request
            self.args = args
            self.kwargs = kwargs
            return self.dispatch(request, *args, **kwargs)

        # take name and docstring from class
        update_wrapper(view, cls, updated=())

        # and possible attributes set by decorators
        # like csrf_exempt from dispatch
        update_wrapper(view, cls.dispatch, assigned=())
        return view

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        # Try to dispatch to the right method; if a method doesn't exist,
        # defer to the error handler. Also defer to the error handler if the
        # request method isn't on the approved list.
        if request.method.lower() in self.http_method_names:
            handler = getattr(self, request.method.lower(),
                              self.http_method_not_allowed)
        else:
            handler = self.http_method_not_allowed
        return handler(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return self.server.handle_wsdl(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.server.handle_rpc(request, *args, **kwargs)

    def http_method_not_allowed(self, request, *args, **kwargs):
        logger.warning('Method Not Allowed (%s): %s', request.method,
                       request.path, extra={'status_code': 405, 'request':
                                            self.request})
        return HttpResponseNotAllowed(self._allowed_methods())

    def options(self, request, *args, **kwargs):
        """Handle responding to requests for the OPTIONS HTTP verb."""

        response = HttpResponse()
        response['Allow'] = ', '.join(self._allowed_methods())
        response['Content-Length'] = '0'
        return response

    def _allowed_methods(self):
        return [m.upper() for m in self.http_method_names if hasattr(self, m)]
