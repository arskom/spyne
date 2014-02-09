
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

"""The ``spyne.server.twisted`` module contains a server transport compatible
with the Twisted event loop. It uses the TwistedWebResource object as transport.

Also see the twisted examples in the examples directory of the source
distribution.

If you want to have a hard-coded URL in the wsdl document, this is how to do
it: ::

    resource = TwistedWebResource(...)
    resource.http_transport.doc.wsdl11.build_interface_document("http://example.com")

This is not strictly necessary -- if you don't do this, Spyne will get the
URL from the first request, build the wsdl on-the-fly and cache it as a
string in memory for later requests. However, if you want to make sure
you only have this url on the WSDL, this is how to do it. Note that if
your client takes the information in wsdl seriously, all requests will go
to the designated url above which can make testing a bit difficult. Use
in moderation.

This module is EXPERIMENTAL. Your mileage may vary. Patches are welcome.
"""


from __future__ import absolute_import

import logging
logger = logging.getLogger(__name__)

from inspect import isgenerator

from spyne.error import InternalError
from twisted.python.log import err
from twisted.internet.defer import Deferred
from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET

from spyne.auxproc import process_contexts
from spyne.const.ansi_color import LIGHT_GREEN
from spyne.const.ansi_color import END_COLOR
from spyne.const.http import HTTP_404
from spyne.model import PushBase
from spyne.model.fault import Fault
from spyne.server.http import HttpBase
from spyne.server.http import HttpMethodContext
from spyne.server.http import HttpTransportContext
from spyne.server.twisted._base import Producer



def _reconstruct_url(request):
    server_name = request.getRequestHostname()
    server_port = request.getHost().port
    if (bool(request.isSecure()), server_port) not in [(True, 443), (False, 80)]:
        server_name = '%s:%d' % (server_name, server_port)

    if request.isSecure():
        url_scheme = 'https'
    else:
        url_scheme = 'http'

    return ''.join([url_scheme, "://", server_name, request.uri])


class TwistedHttpTransportContext(HttpTransportContext):

    def set_mime_type(self, what):
        super(TwistedHttpTransportContext, self).set_mime_type(what)
        self.req.setHeader('Content-Type', what)


class TwistedHttpMethodContext(HttpMethodContext):

    default_transport_context = TwistedHttpTransportContext


class TwistedHttpTransport(HttpBase):
    @staticmethod
    def decompose_incoming_envelope(prot, ctx, message):
        """This function is only called by the HttpRpc protocol to have the
        twisted web's Request object is parsed into ``ctx.in_body_doc`` and
        ``ctx.in_header_doc``.
        """

        request = ctx.in_document

        ctx.method_request_string = '{%s}%s' % (prot.app.interface.get_tns(),
                                                    request.path.split('/')[-1])

        logger.debug("%sMethod name: %r%s" % (LIGHT_GREEN,
                                          ctx.method_request_string, END_COLOR))

        ctx.in_header_doc = dict(request.requestHeaders.getAllRawHeaders())
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
        if request.uri.endswith('.wsdl') or request.uri.endswith('?wsdl'):
            return self.__handle_wsdl_request(request)

        else:
            return self.handle_rpc(request)

    def render_POST(self, request):
        return self.handle_rpc(request)

    def handle_rpc_error(self, p_ctx, others, error, request):
        resp_code = p_ctx.transport.resp_code
        # If user code set its own response code, don't touch it.
        if resp_code is None:
            resp_code = p_ctx.out_protocol.fault_to_http_response_code(error)

        request.setResponseCode(int(resp_code[:3]))

        # In case user code set its own out_* attributes before failing.
        p_ctx.out_document = None
        p_ctx.out_string = None

        p_ctx.out_object = error
        self.http_transport.get_out_string(p_ctx)

        retval = ''.join(p_ctx.out_string)

        p_ctx.close()

        process_contexts(self.http_transport, others, p_ctx, error=error)

        return retval

    def handle_rpc(self, request):
        initial_ctx = TwistedHttpMethodContext(self.http_transport, request,
                                 self.http_transport.app.out_protocol.mime_type)
        initial_ctx.in_string = [request.content.getvalue()]

        contexts = self.http_transport.generate_contexts(initial_ctx)
        p_ctx, others = contexts[0], contexts[1:]

        if p_ctx.in_error:
            return self.handle_rpc_error(p_ctx, others, p_ctx.in_error, request)

        else:
            self.http_transport.get_in_object(p_ctx)

            if p_ctx.in_error:
                return self.handle_rpc_error(p_ctx, others, p_ctx.in_error,
                                                                        request)

            self.http_transport.get_out_object(p_ctx)
            if p_ctx.out_error:
                return self.handle_rpc_error(p_ctx, others, p_ctx.out_error,
                                                                        request)

        ret = p_ctx.out_object[0]
        if isinstance(ret, Deferred):
            ret.addCallback(_cb_deferred, request, p_ctx, others, self)
            ret.addErrback(_eb_deferred, request, p_ctx, others, self)

        elif isinstance(ret, PushBase):
            _init_push(ret, request, p_ctx, others, self)
        else:
            _cb_deferred(p_ctx.out_object, request, p_ctx, others, self, cb=False)

        return NOT_DONE_YET

    def __handle_wsdl_request(self, request):
        ctx = TwistedHttpMethodContext(self.http_transport, request,
                                                      "text/xml; charset=utf-8")
        url = _reconstruct_url(request)

        if self.http_transport.doc.wsdl11 is None:
            return HTTP_404

        if self._wsdl is None:
            self._wsdl = self.http_transport.doc.wsdl11.get_interface_document()

        ctx.transport.wsdl = self._wsdl

        try:
            if self._wsdl is None:
                self.http_transport.doc.wsdl11.build_interface_document(url)
                ctx.transport.wsdl = self._wsdl = \
                         self.http_transport.doc.wsdl11.get_interface_document()

            assert ctx.transport.wsdl is not None

            self.http_transport.event_manager.fire_event('wsdl', ctx)

            return ctx.transport.wsdl

        except Exception as e:
            ctx.transport.wsdl_error = e
            self.http_transport.event_manager.fire_event('wsdl_exception', ctx)
            raise

        finally:
            ctx.close()


def _cb_request_finished(request, p_ctx):
    request.finish()
    p_ctx.close()

def _eb_request_finished(request, p_ctx):
    err(request)
    p_ctx.close()
    request.finish()


def _init_push(ret, request, p_ctx, others, resource):
    assert isinstance(ret, PushBase)

    p_ctx.out_stream = request

    # fire events
    p_ctx.app.event_manager.fire_event('method_return_push', p_ctx)
    if p_ctx.service_class is not None:
        p_ctx.service_class.event_manager.fire_event('method_return_push', p_ctx)

    gen = resource.http_transport.get_out_string_push(p_ctx)

    assert isgenerator(gen), "It looks like this protocol is not " \
                             "async-compliant. Yet."

    def _cb_push_finish():
        p_ctx.out_stream.finish()
        process_contexts(resource.http_transport, others, p_ctx)

    retval = ret.init(p_ctx, request, gen, _cb_push_finish, None)
    """:type : Deferred"""

    if isinstance(retval, Deferred):
        def _eb_push_close(f):
            ret.close()

        def _cb_push_close(r):
            def _eb_inner(f):
                return f

            if r is None:
                ret.close()
            else:
                r.addCallback(_cb_push_close).addErrback(_eb_inner)

        retval.addCallback(_cb_push_close).addErrback(_eb_push_close)

    else:
        ret.close()

    return retval


def _cb_deferred(ret, request, p_ctx, others, resource, cb=True):
    if cb and len(p_ctx.descriptor.out_message._type_info) <= 1:
        p_ctx.out_object = [ret]
    else:
        p_ctx.out_object = ret

    retval = None
    if isinstance(ret, PushBase):
        retval = _init_push(ret, request, p_ctx, others, resource)
    else:
        resource.http_transport.get_out_string(p_ctx)

        producer = Producer(p_ctx.out_string, request)
        producer.deferred.addCallback(_cb_request_finished, p_ctx, others, resource)
        producer.deferred.addErrback(_eb_request_finished, p_ctx, others, resource)

        request.registerProducer(producer, False)

    process_contexts(resource.http_transport, others, p_ctx)

    return retval

def _eb_deferred(retval, request, p_ctx, others, resource):
    p_ctx.out_error = retval.value
    if not issubclass(retval.type, Fault):
        retval.printTraceback()
        p_ctx.out_error = InternalError(retval.value)

    ret = resource.handle_rpc_error(p_ctx, others, p_ctx.out_error, request)
    request.write(ret)
    request.finish()
