
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

This is not strictly necessary. If you don't do this, Spyne will get the URL
from the first request, build the wsdl on-the-fly and cache it as a string in
memory for later requests. However, if you want to make sure you only have this
url on the WSDL, this is how to do it. Note that if your client takes the
information in wsdl seriously, all requests will go to the designated url above
which can make testing a bit difficult. Use in moderation.

This module is EXPERIMENTAL. Your mileage may vary. Patches are welcome.
"""


from __future__ import absolute_import

import logging
logger = logging.getLogger(__name__)

import re

from os import fstat
from mmap import mmap
from inspect import isgenerator, isclass
from collections import namedtuple

from twisted.web.server import NOT_DONE_YET, Request
from twisted.web.resource import Resource, NoResource, ForbiddenResource
from twisted.web import static
from twisted.web.static import getTypeAndEncoding
from twisted.web.http import CACHED
from twisted.python.log import err
from twisted.internet.defer import Deferred

from spyne import BODY_STYLE_BARE, BODY_STYLE_EMPTY, Redirect
from spyne.application import logger_server
from spyne.application import get_fault_string_from_exception

from spyne.error import InternalError
from spyne.auxproc import process_contexts
from spyne.const.ansi_color import LIGHT_GREEN
from spyne.const.ansi_color import END_COLOR
from spyne.const.http import HTTP_404, HTTP_200
from spyne.model import PushBase, File, ComplexModelBase
from spyne.model.fault import Fault
from spyne.protocol.http import HttpRpc
from spyne.server.http import HttpBase
from spyne.server.http import HttpMethodContext
from spyne.server.http import HttpTransportContext
from spyne.server.twisted._base import Producer
from spyne.util.six import text_type, string_types
from spyne.util.six.moves.urllib.parse import unquote


def _render_file(file, request):
    """
    Begin sending the contents of this L{File} (or a subset of the
    contents, based on the 'range' header) to the given request.
    """
    file.restat(False)

    if file.type is None:
        file.type, file.encoding = getTypeAndEncoding(file.basename(),
                                                      file.contentTypes,
                                                      file.contentEncodings,
                                                      file.defaultType)

    if not file.exists():
        return file.childNotFound.render(request)

    if file.isdir():
        return file.redirect(request)

    request.setHeader('accept-ranges', 'bytes')

    try:
        fileForReading = file.openForReading()
    except IOError as e:
        import errno

        if e[0] == errno.EACCES:
            return ForbiddenResource().render(request)
        else:
            raise

    #if request.setLastModified(file.getmtime()) is CACHED:
    #    return ''

    producer = file.makeProducer(request, fileForReading)

    if request.method == 'HEAD':
        return ''

    producer.start()
    # and make sure the connection doesn't get closed
    return NOT_DONE_YET


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

    def get_cookie(self, key):
        return self.req.getCookie(key)

    def get_path(self):
        return self.req.URLPath().path

    def get_path_and_qs(self):
        return self.req.uri

    def get_request_method(self):
        return self.req.method

    def get_request_content_type(self):
        return self.req.getHeader("Content-Type")


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

        # this is a huge hack because twisted seems to take the slashes in urls
        # too seriously.
        postpath = getattr(request, 'realpostpath', None)
        if postpath is None:
            postpath = request.path

        params = self.match_pattern(ctx, request.method, postpath,
                                                      request.getHeader('Host'))

        if ctx.method_request_string is None: # no pattern match
            ctx.method_request_string = '{%s}%s' % (self.app.interface.get_tns(),
                                                request.path.rsplit('/', 1)[-1])

        logger.debug("%sMethod name: %r%s" % (LIGHT_GREEN,
                                          ctx.method_request_string, END_COLOR))

        for k, v in params.items():
            val = ctx.in_body_doc.get(k, [])
            val.extend(v)
            ctx.in_body_doc[k] = val

        r = {}
        for k,v in ctx.in_body_doc.items():
            l = []
            for v2 in v:
                if isinstance(v2, string_types):
                    l.append(unquote(v2))
                else:
                    l.append(v2)
            r[k] = l
        ctx.in_body_doc = r

        # This is consistent with what server.wsgi does.
        if request.method in ('POST', 'PUT', 'PATCH'):
            for k, v in ctx.in_body_doc.items():
                if v == ['']:
                    ctx.in_body_doc[k] = [None]


FIELD_NAME_RE = re.compile(r'name="([^"]+)"')
FILE_NAME_RE = re.compile(r'filename="([^"]+)"')
_FileInfo = namedtuple("_FileInfo", "field_name file_name file_type "
                                                                "header_offset")
def _get_file_name(instr):
    """We need this huge hack because twisted doesn't offer a way to get file
    name from Content-Disposition header. This works only when there's just one
    file because we want to avoid scanning the whole stream. So this won't get
    the names of the subsequent files even though that's a perfectly valid
    request.
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
                                           block_length=8 * 1024, prepath=None):
        Resource.__init__(self)
        self.app = app

        self.http_transport = TwistedHttpTransport(app, chunked,
                                            max_content_length, block_length)
        self._wsdl = None
        self.prepath = prepath

    def getChildWithDefault(self, path, request):
        # this hack is necessary because twisted takes the slash character in
        # http requests too seriously. i.e. it insists that a leaf node can only
        # handle the last path fragment.
        if self.prepath is None:
            request.realprepath = '/' + '/'.join(request.prepath)
        else:
            if not self.prepath.startswith('/'):
                request.realprepath = '/' + self.prepath
            else:
                request.realprepath = self.prepath

        if path in self.children:
            retval = self.children[path]
        else:
            retval = self.getChild(path, request)

        if isinstance(retval, NoResource):
            retval = self
        else:
            request.realpostpath = request.path[len(request.realprepath):]

        return retval

    def render(self, request):
        if request.method == 'GET' and (
                request.uri.endswith('.wsdl') or request.uri.endswith('?wsdl')):
            return self.__handle_wsdl_request(request)
        return self.handle_rpc(request)

    def handle_rpc_error(self, p_ctx, others, error, request):
        logger.error(error)

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

        ret = p_ctx.out_object[0]
        retval = NOT_DONE_YET
        if isinstance(ret, Deferred):
            ret.addCallback(_cb_deferred, request, p_ctx, others, self)
            ret.addErrback(_eb_deferred, request, p_ctx, others, self)

        elif isinstance(ret, PushBase):
            _init_push(ret, request, p_ctx, others, self)

        else:
            retval = _cb_deferred(p_ctx.out_object, request, p_ctx, others, self, cb=False)

        return retval

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

    # fire events
    p_ctx.app.event_manager.fire_event('method_return_push', p_ctx)
    if p_ctx.service_class is not None:
        p_ctx.service_class.event_manager.fire_event('method_return_push', p_ctx)

    gen = resource.http_transport.get_out_string_push(p_ctx)

    assert isgenerator(gen), "It looks like this protocol is not " \
                             "async-compliant yet."

    def _cb_push_finish():
        p_ctx.out_stream.finish()
        process_contexts(resource.http_transport, others, p_ctx)

    retval = ret.init(p_ctx, request, gen, _cb_push_finish, None)

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
    resp_code = p_ctx.transport.resp_code
    # If user code set its own response code, don't touch it.
    if resp_code is None:
        resp_code = HTTP_200
    request.setResponseCode(int(resp_code[:3]))

    _set_response_headers(request, p_ctx.transport.resp_headers)

    om = p_ctx.descriptor.out_message
    single_class = None
    if cb:
        if p_ctx.descriptor.body_style in (BODY_STYLE_BARE, BODY_STYLE_EMPTY):
            p_ctx.out_object = [ret]

        elif (not issubclass(om, ComplexModelBase)) or len(om._type_info) <= 1:
            p_ctx.out_object = [ret]
            if len(om._type_info) == 1:
                single_class, = om._type_info.values()
        else:
            p_ctx.out_object = ret
    else:
        p_ctx.out_object = ret

    retval = NOT_DONE_YET

    p_ctx.out_stream = request
    if isinstance(ret, PushBase):
        retval = _init_push(ret, request, p_ctx, others, resource)

    elif ((isclass(om) and issubclass(om, File)) or
          (isclass(single_class) and issubclass(single_class, File))) and \
         isinstance(p_ctx.out_protocol, HttpRpc) and \
                                      getattr(ret, 'abspath', None) is not None:

        file = static.File(ret.abspath,
                        defaultType=str(ret.type) or 'application/octet-stream')
        retval = _render_file(file, request)
        if retval != NOT_DONE_YET and cb:
            request.write(retval)
            request.finish()
            p_ctx.close()
        else:
            def _close_only_context(ret):
                p_ctx.close()

            request.notifyFinish().addCallback(_close_only_context)
            request.notifyFinish().addErrback(_eb_request_finished, request, p_ctx)

    else:
        resource.http_transport.get_out_string(p_ctx)

        producer = Producer(p_ctx.out_string, request)
        producer.deferred.addCallback(_cb_request_finished, request, p_ctx)
        producer.deferred.addErrback(_eb_request_finished, request, p_ctx)

        request.registerProducer(producer, False)

    process_contexts(resource.http_transport, others, p_ctx)

    return retval


def _eb_deferred(ret, request, p_ctx, others, resource):
    app = p_ctx.app

    # DRY this with what's in Application.process_request
    if issubclass(ret.type, Redirect):
        try:
            ret.value.do_redirect()

            # Now that the processing is switched to the outgoing message,
            # point ctx.protocol to ctx.out_protocol
            p_ctx.protocol = p_ctx.outprot_ctx

            _cb_deferred(None, request, p_ctx, others, resource, cb=False)

            # fire events
            app.event_manager.fire_event('method_redirect', p_ctx)
            if p_ctx.service_class is not None:
                p_ctx.service_class.event_manager.fire_event(
                    'method_redirect', p_ctx)

        except Exception as e:
            logger_server.exception(e)
            p_ctx.out_error = Fault('Server', get_fault_string_from_exception(e))

            # fire events
            app.event_manager.fire_event('method_redirect_exception', p_ctx)
            if p_ctx.service_class is not None:
                p_ctx.service_class.event_manager.fire_event(
                    'method_redirect_exception', p_ctx)

    elif issubclass(ret.type, Fault):
        p_ctx.out_error = ret.value

        ret = resource.handle_rpc_error(p_ctx, others, p_ctx.out_error, request)

        # fire events
        app.event_manager.fire_event('method_exception_object', p_ctx)
        if p_ctx.service_class is not None:
            p_ctx.service_class.event_manager.fire_event(
                                               'method_exception_object', p_ctx)

        request.write(ret)

    else:
        p_ctx.out_error = ret.value
        ret.printTraceback()
        p_ctx.out_error = InternalError(ret.value)

        # fire events
        app.event_manager.fire_event('method_exception_object', p_ctx)
        if p_ctx.service_class is not None:
            p_ctx.service_class.event_manager.fire_event(
                                               'method_exception_object', p_ctx)

    request.finish()
