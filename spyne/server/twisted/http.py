
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

import re

from os import fstat
from mmap import mmap
from inspect import isgenerator
from collections import namedtuple

from spyne.error import InternalError
from twisted.python.log import err
from twisted.internet.defer import Deferred
from twisted.web.resource import Resource, NoResource
from twisted.web.server import NOT_DONE_YET, Request

from spyne.auxproc import process_contexts
from spyne.const.ansi_color import LIGHT_GREEN
from spyne.const.ansi_color import END_COLOR
from spyne.const.http import HTTP_404, HTTP_200
from spyne.model import PushBase, File
from spyne.model.fault import Fault
from spyne.server.http import HttpBase
from spyne.server.http import HttpMethodContext
from spyne.server.http import HttpTransportContext
from spyne.server.twisted._base import Producer
from spyne.util.six import text_type


def _set_response_headers(request, headers):
    retval = []

    for k, v in headers.items():
        if isinstance(v, (list, tuple)):
            request.responseHeaders.setRawHeaders(k, v)
        else:
            request.responseHeaders.setRawHeaders(k, [v])

    return retval


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
        if isinstance(what, text_type):
            what = what.encode('ascii', errors='replace')
        super(TwistedHttpTransportContext, self).set_mime_type(what)
        self.req.setHeader('Content-Type', what)


class TwistedHttpMethodContext(HttpMethodContext):

    default_transport_context = TwistedHttpTransportContext


class TwistedHttpTransport(HttpBase):
    def __init__(self, app, chunked=False, max_content_length=2 * 1024 * 1024,
                                                         block_length=8 * 1024):
        super(TwistedHttpTransport, self).__init__(app, chunked=chunked,
               max_content_length=max_content_length, block_length=block_length)

    def decompose_incoming_envelope(self, prot, ctx, message):
        """This function is only called by the HttpRpc protocol to have the
        twisted web's Request object is parsed into ``ctx.in_body_doc`` and
        ``ctx.in_header_doc``.
        """

        request = ctx.in_document
        assert isinstance(request, Request)

        ctx.in_header_doc = dict(request.requestHeaders.getAllRawHeaders())
        fi = ctx.transport.file_info
        if fi is not None and len(request.args) == 1:
            key, = request.args.keys()
            if fi.field_name == key and fi.file_name is not None:
                ctx.in_body_doc = {key: [File.Value(name=fi.file_name,
                                    type=fi.file_type, data=request.args[key])]}

            else:
                ctx.in_body_doc = request.args
        else:
            ctx.in_body_doc = request.args


        params = self.match_pattern(ctx, request.method, request.path,
                                                                   request.host)
        if ctx.method_request_string is None: # no pattern match
            ctx.method_request_string = '{%s}%s' % (self.app.interface.get_tns(),
                                                    request.path.split('/')[-1])

        logger.debug("%sMethod name: %r%s" % (LIGHT_GREEN,
                                          ctx.method_request_string, END_COLOR))

        for k, v in params.items():
             if k in ctx.in_body_doc:
                 ctx.in_body_doc[k].append(v)
             else:
                 ctx.in_body_doc[k] = [v]


FIELD_NAME_RE = re.compile(r'name="([^"]+)"')
FILE_NAME_RE = re.compile(r'filename="([^"]+)"')
_FileInfo = namedtuple("_FileInfo", "field_name file_name file_type "
                                                                "header_offset")
def _get_file_name(instr):
    """We need this huge hack because twisted doesn't offer a way to get file
    name from Content-Disposition header. This works only when there's just one
    file -- it won't get the names of the subsequent files even though that's a
    perfectly valid request.
    """

    field_name = file_name = file_type = content_idx = None

    # hack to see if it looks like a multipart request. 5 is arbitrary.
    if instr[:5] == "-----":
        first_page = instr[:4096] # 4096 = default page size on linux.

        # this normally roughly <200
        header_idx = first_page.find('\r\n') + 2
        content_idx = first_page.find('\r\n\r\n', header_idx)
        if header_idx > 0 and content_idx > header_idx:
            headerstr = first_page[header_idx:content_idx]

            for line in headerstr.split("\r\n"):
                k, v = line.split(":", 2)
                if k == "Content-Disposition":
                    for subv in v.split(";"):
                        subv = subv.strip()
                        m = FIELD_NAME_RE.match(subv)
                        if m:
                            field_name = m.group(1)
                            continue

                        m = FILE_NAME_RE.match(subv)
                        if m:
                            file_name = m.group(1)
                    continue

                if k == "Content-Type":
                    file_type = v.strip()

        # 4 == len('\r\n\r\n')
        return _FileInfo(field_name, file_name, file_type, content_idx + 4)


def _has_fd(istr):
    if hasattr(istr, 'fileno'):
        try:
            istr.fileno()
            return True
        except IOError:
            return False
    return False

class TwistedWebResource(Resource):
    """A server transport that exposes the application as a twisted web
    Resource.
    """

    def __init__(self, app, chunked=False, max_content_length=2 * 1024 * 1024,
                                           block_length=8 * 1024):
        Resource.__init__(self)

        self.http_transport = TwistedHttpTransport(app, chunked,
                                            max_content_length, block_length)
        self._wsdl = None

    def getChildWithDefault(self, path, request):
        if path in self.children:
            retval = self.children[path]
        else:
            retval = self.getChild(path, request)

        if isinstance(retval, NoResource):
            retval = self

        return retval

    def render(self, request):
        return self.handle_rpc(request)

    def render_GET(self, request):
        if request.uri.endswith('.wsdl') or request.uri.endswith('?wsdl'):
            return self.__handle_wsdl_request(request)
        else:
            return self.handle_rpc(request)

    def handle_rpc_error(self, p_ctx, others, error, request):
        resp_code = p_ctx.transport.resp_code
        # If user code set its own response code, don't touch it.
        if resp_code is None:
            resp_code = p_ctx.out_protocol.fault_to_http_response_code(error)

        request.setResponseCode(int(resp_code[:3]))
        _set_response_headers(request, p_ctx.transport.resp_headers)

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
        if _has_fd(request.content):
            f = request.content

            # it's best to avoid empty mappings.
            if fstat(f.fileno()).st_size == 0:
                initial_ctx.in_string = ['']
            else:
                initial_ctx.in_string = [mmap(f.fileno(), 0)]
        else:
            request.content.seek(0)
            initial_ctx.in_string = [request.content.read()]

        initial_ctx.transport.file_info = \
                                        _get_file_name(initial_ctx.in_string[0])

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

        resp_code = p_ctx.transport.resp_code
        # If user code set its own response code, don't touch it.
        if resp_code is None:
            resp_code = HTTP_200
        request.setResponseCode(int(resp_code[:3]))

        _set_response_headers(request, p_ctx.transport.resp_headers)

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
        _set_response_headers(request, ctx.transport.resp_headers)

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


def _cb_request_finished(retval, request, p_ctx):
    request.finish()
    p_ctx.close()

def _eb_request_finished(retval, request, p_ctx):
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
        producer.deferred.addCallback(_cb_request_finished, request, p_ctx)
        producer.deferred.addErrback(_eb_request_finished, request, p_ctx)

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
