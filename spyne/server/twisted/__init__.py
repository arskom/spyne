
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

This module is EXPERIMENTAL. Your mileage may vary. Patches are welcome.
"""

import logging
logger = logging.getLogger(__name__)

from twisted.python.log import err
from twisted.internet.interfaces import IPullProducer
from twisted.internet.defer import Deferred
from twisted.web.iweb import IBodyProducer
from twisted.web.iweb import UNKNOWN_LENGTH
from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET

from zope.interface import implements

from spyne.auxproc import process_contexts
from spyne.server.http import HttpMethodContext
from spyne.server.http import HttpBase

from spyne.const.ansi_color import LIGHT_GREEN
from spyne.const.ansi_color import END_COLOR
from spyne.const.http import HTTP_405


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


class _Producer(object):
    implements(IPullProducer)

    deferred = None

    def __init__(self, body, consumer):
        """:param body: an iterable of strings"""

        # check to see if we can determine the length
        try:
            len(body) # iterator?
            self.length = sum([len(fragment) for fragment in body])
            self.body = iter(body)

        except TypeError:
            self.length = UNKNOWN_LENGTH
            self.body = body

        self.deferred = Deferred()
        self.consumer = consumer

    def resumeProducing(self):
        try:
            chunk = self.body.next()
        except StopIteration, e:
            self.consumer.unregisterProducer()
            if self.deferred is not None:
                self.deferred.callback(self.consumer)
                self.deferred = None
            return

        self.consumer.write(chunk)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        if self.deferred is not None:
            self.deferred.errback(
                               Exception("Consumer asked us to stop producing"))
        self.deferred = None


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

    def handle_error(self, p_ctx, others, error, request):
        resp_code = self.http_transport.app.out_protocol \
                                            .fault_to_http_response_code(error)

        request.setResponseCode(int(resp_code[:3]))

        p_ctx.out_object = error
        self.http_transport.get_out_string(p_ctx)

        process_contexts(self.http_transport, others, p_ctx, error=error)

        return ''.join(p_ctx.out_string)

    def handle_rpc(self, request):
        initial_ctx = HttpMethodContext(self.http_transport, request,
                                self.http_transport.app.out_protocol.mime_type)
        initial_ctx.in_string = [request.content.getvalue()]

        contexts = self.http_transport.generate_contexts(initial_ctx)
        p_ctx, others = contexts[0], contexts[1:]
        if p_ctx.in_error:
            return self.handle_error(p_ctx, others, p_ctx.in_error, request)

        else:
            self.http_transport.get_in_object(p_ctx)

            if p_ctx.in_error:
                return self.handle_error(p_ctx, others, p_ctx.in_error, request)
            else:
                self.http_transport.get_out_object(p_ctx)
                if p_ctx.out_error:
                    return self.handle_error(p_ctx, others, p_ctx.out_error, request)

        self.http_transport.get_out_string(p_ctx)

        process_contexts(self.http_transport, others, p_ctx)

        def _cb_request_finished(request):
            request.finish()

        producer = _Producer(p_ctx.out_string, request)
        producer.deferred.addErrback(err).addCallback(_cb_request_finished)
        request.registerProducer(producer, False)

        return NOT_DONE_YET

    def __handle_wsdl_request(self, request):
        ctx = HttpMethodContext(self.http_transport, request,
                                                      "text/xml; charset=utf-8")
        url = _reconstruct_url(request)

        try:
            ctx.transport.wsdl = self._wsdl

            if ctx.transport.wsdl is None:
                from spyne.interface.wsdl.wsdl11 import Wsdl11
                wsdl = Wsdl11(self.http_transport.app.interface)
                wsdl.build_interface_document(url)
                self._wsdl = ctx.transport.wsdl = wsdl.get_interface_document()

            assert ctx.transport.wsdl != None

            self.http_transport.event_manager.fire_event('wsdl', ctx)

            for k,v in ctx.transport.resp_headers.items():
                request.setHeader(k,v)

            return ctx.transport.wsdl

        except Exception, e:
            ctx.transport.wsdl_error = e
            self.http_transport.event_manager.fire_event('wsdl_exception', ctx)
            raise
