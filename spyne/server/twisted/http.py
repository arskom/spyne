
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
"""

from __future__ import absolute_import

import logging
logger = logging.getLogger(__name__)

import re
import cgi
import gzip
import shutil
import threading

from os import fstat
from mmap import mmap
from inspect import isclass
from collections import namedtuple
from tempfile import TemporaryFile

from twisted.web import static
from twisted.web.server import NOT_DONE_YET, Request
from twisted.web.resource import Resource, NoResource, ForbiddenResource
from twisted.web.static import getTypeAndEncoding
from twisted.python.log import err
from twisted.python.failure import Failure
from twisted.internet import reactor
from twisted.internet.task import deferLater
from twisted.internet.defer import Deferred
from twisted.internet.threads import deferToThread

from spyne import Redirect, Address
from spyne.application import logger_server
from spyne.application import get_fault_string_from_exception

from spyne.util import six
from spyne.error import InternalError, ValidationError
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
from spyne.server.twisted import log_and_let_go

from spyne.util.address import address_parser
from spyne.util.six import text_type, string_types
from spyne.util.six.moves.urllib.parse import unquote

if not six.PY2:
    from urllib.request import unquote_to_bytes


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
    # HTTP "Hosts" header only supports ascii

    server_name = request.getHeader(b"x-forwarded-host")
    server_port = request.getHeader(b"x-forwarded-port")
    if server_port is not None:
        try:
            server_port = int(server_port)
        except Exception as e:
            logger.debug("Ignoring exception: %r for value %r", e, server_port)
            server_port = None

    is_secure = request.getHeader(b"x-forwarded-proto")
    if is_secure is not None:
        is_secure = is_secure == 'https'

    if server_name is None:
        server_name = request.getRequestHostname().decode('ascii')
    if server_port is None:
        server_port = request.getHost().port
    if is_secure is None:
        is_secure = bool(request.isSecure())

    if (is_secure, server_port) not in ((True, 443), (False, 80)):
        server_name = '%s:%d' % (server_name, server_port)

    if is_secure:
        url_scheme = 'https'
    else:
        url_scheme = 'http'

    uri = _decode_path(request.uri)
    return ''.join([url_scheme, "://", server_name, uri])


class _Transformer(object):
    def __init__(self, req):
        self.req = req

    def get(self, key, default):
        key = key.lower()
        if six.PY2:
            if key.startswith((b'http_', b'http-')):
                key = key[5:]
        else:
            if isinstance(key, bytes):
                if key.startswith((b'http_', b'http-')):
                    key = key[5:]
            else:
                if key.startswith(('http_', 'http-')):
                    key = key[5:]

        retval = self.req.getHeader(key)
        if retval is None:
            retval = default
        return retval


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

    def get_peer(self):
        peer = Address.from_twisted_address(self.req.transport.getPeer())
        addr = address_parser.get_ip(_Transformer(self.req))

        if addr is None:
            return peer

        if address_parser.is_valid_ipv4(addr):
            return Address(type=Address.TCP4, host=addr, port=0)

        if address_parser.is_valid_ipv6(addr):
            return Address(type=Address.TCP6, host=addr, port=0)


class TwistedHttpMethodContext(HttpMethodContext):
    HttpTransportContext = TwistedHttpTransportContext


def _decode_path(fragment):
    if six.PY2:
        return unquote(fragment)

    return unquote_to_bytes(fragment)


class TwistedHttpTransport(HttpBase):
    SLASH = b'/'
    SLASHPER = b'/%s'

    KEY_ENCODING = 'utf8'

    @classmethod
    def get_patt_verb(cls, patt):
        return patt.verb_b_re

    @classmethod
    def get_patt_host(cls, patt):
        return patt.host_b_re

    @classmethod
    def get_patt_address(cls, patt):
        return patt.address_b_re

    def __init__(self, app, chunked=False, max_content_length=2 * 1024 * 1024,
                                                         block_length=8 * 1024):
        super(TwistedHttpTransport, self).__init__(app, chunked=chunked,
               max_content_length=max_content_length, block_length=block_length)

        self.reactor_thread = None
        def _cb():
            self.reactor_thread = threading.current_thread()

        deferLater(reactor, 0, _cb)

    def pusher_init(self, p_ctx, gen, _cb_push_finish, pusher, interim):
        if pusher.orig_thread != self.reactor_thread:
            return deferToThread(super(TwistedHttpTransport, self).pusher_init,
                                   p_ctx, gen, _cb_push_finish, pusher, interim)

        return super(TwistedHttpTransport, self).pusher_init(
                                   p_ctx, gen, _cb_push_finish, pusher, interim)

    @staticmethod
    def set_out_document_push(ctx):
        class _ISwearImAGenerator(object):
            def send(self, data):
                if not data: return
                ctx.out_stream.write(data)

        ctx.out_document = _ISwearImAGenerator()

    def pusher_try_close(self, ctx, pusher, retval):
        # the whole point of this function is to call ctx.out_stream.finish()
        # when a *root* pusher has no more data to send. interim pushers don't
        # have to close anything.
        if isinstance(retval, Deferred):
            def _eb_push_close(f):
                assert isinstance(f, Failure)

                logger.error(f.getTraceback())

                subretval = super(TwistedHttpTransport, self) \
                                          .pusher_try_close(ctx, pusher, retval)

                if not pusher.interim:
                    ctx.out_stream.finish()

                return subretval

            def _cb_push_close(r):
                def _eb_inner(f):
                    if not pusher.interim:
                        ctx.out_stream.finish()

                    return f

                if not isinstance(r, Deferred):
                    retval = super(TwistedHttpTransport, self) \
                                               .pusher_try_close(ctx, pusher, r)
                    if not pusher.interim:
                        ctx.out_stream.finish()

                    return retval

                return r \
                    .addCallback(_cb_push_close) \
                    .addErrback(_eb_inner) \
                    .addErrback(log_and_let_go, logger)

            return retval \
                .addCallback(_cb_push_close) \
                .addErrback(_eb_push_close)  \
                .addErrback(log_and_let_go, logger)

        super(TwistedHttpTransport, self).pusher_try_close(ctx, pusher, retval)

        if not pusher.interim:
            retval = ctx.out_stream.finish()

        return retval

    def _decode_dict_py2(self, d):
        retval = {}

        for k, v in d.items():
            l = []
            for v2 in v:
                if isinstance(v2, string_types):
                    l.append(unquote(v2))
                else:
                    l.append(v2)
            retval[k] = l

        return retval

    def _decode_dict(self, d):
        retval = {}

        for k, v in d.items():
            l = []
            for v2 in v:
                if isinstance(v2, str):
                    l.append(unquote(v2))
                elif isinstance(v2, bytes):
                    l.append(unquote(v2.decode(self.KEY_ENCODING)))
                else:
                    l.append(v2)

            if isinstance(k, str):
                retval[k] = l
            elif isinstance(k, bytes):
                retval[k.decode(self.KEY_ENCODING)] = l
            else:
                raise ValidationError(k)

        return retval

    def decompose_incoming_envelope(self, prot, ctx, message):
        """This function is only called by the HttpRpc protocol to have the
        twisted web's Request object is parsed into ``ctx.in_body_doc`` and
        ``ctx.in_header_doc``.
        """

        request = ctx.in_document
        assert isinstance(request, Request)

        ctx.in_header_doc = dict(request.requestHeaders.getAllRawHeaders())
        ctx.in_body_doc = request.args

        for fi in ctx.transport.file_info:
            assert isinstance(fi, _FileInfo)
            if fi.file_name is None:
                continue

            l = ctx.in_body_doc.get(fi.field_name, None)
            if l is None:
                l = ctx.in_body_doc[fi.field_name] = []

            l.append(
                File.Value(name=fi.file_name, type=fi.file_type, data=fi.data)
            )

        # this is a huge hack because twisted seems to take the slashes in urls
        # too seriously.
        postpath = getattr(request, 'realpostpath', None)
        if postpath is None:
            postpath = request.path

        if postpath is not None:
            postpath = _decode_path(postpath)

        params = self.match_pattern(ctx, request.method, postpath,
                                                     request.getHeader(b'Host'))

        if ctx.method_request_string is None: # no pattern match
            ctx.method_request_string = u'{%s}%s' % (
                self.app.interface.get_tns(),
                _decode_path(request.path.rsplit(b'/', 1)[-1]).decode("utf8"),
            )

        logger.debug(u"%sMethod name: %r%s" % (LIGHT_GREEN,
                                          ctx.method_request_string, END_COLOR))

        for k, v in params.items():
            val = ctx.in_body_doc.get(k, [])
            val.extend(v)
            ctx.in_body_doc[k] = val

        r = {}
        if six.PY2:
            ctx.in_header_doc = self._decode_dict_py2(ctx.in_header_doc)
            ctx.in_body_doc = self._decode_dict_py2(ctx.in_body_doc)

        else:
            ctx.in_header_doc = self._decode_dict(ctx.in_header_doc)
            ctx.in_body_doc = self._decode_dict(ctx.in_body_doc)

        # This is consistent with what server.wsgi does.
        if request.method in ('POST', 'PUT', 'PATCH'):
            for k, v in ctx.in_body_doc.items():
                if v == ['']:
                    ctx.in_body_doc[k] = [None]

        logger.debug("%r", ctx.in_body_doc)


FIELD_NAME_RE = re.compile(r'name="([^"]+)"')
FILE_NAME_RE = re.compile(r'filename="([^"]+)"')
_FileInfo = namedtuple("_FileInfo", "field_name file_name file_type data")


def _get_file_info(ctx):
    """We need this hack because twisted doesn't offer a way to get file name
    from Content-Disposition header.
    """

    retval = []

    request = ctx.transport.req
    headers = request.getAllHeaders()
    content_type = headers.get('content-type', None)
    if content_type is None:
        return retval

    content = request.content

    content_encoding = headers.get('content-encoding', None)
    if content_encoding == b'gzip':
        request.content.seek(0)
        content = TemporaryFile()
        with gzip.GzipFile(fileobj=request.content) as ifstr:
            shutil.copyfileobj(ifstr, content)
        content.seek(0)

    img = cgi.FieldStorage(
        fp=content,
        headers=ctx.in_header_doc,
        environ={
            'REQUEST_METHOD': request.method,
            'CONTENT_TYPE': content_type,
        }
    )

    try:
        keys = img.keys()
    except TypeError:
        return retval

    for k in keys:
        fields = img[k]

        if isinstance(fields, cgi.FieldStorage):
            fields = (fields,)

        for field in fields:
            file_type = field.type
            file_name = field.disposition_options.get('filename', None)
            if file_name is not None:
                retval.append(_FileInfo(k, file_name, file_type,
                                                [mmap(field.file.fileno(), 0)]))

    return retval


def _has_fd(istr):
    if not hasattr(istr, 'fileno'):
        return False
    try:
        istr.fileno()
    except IOError:
        return False
    else:
        return True


def get_twisted_child_with_default(res, path, request):
    # this hack is necessary because twisted takes the slash character in
    # http requests too seriously. i.e. it insists that a leaf node can only
    # handle the last path fragment.
    if res.prepath is None:
        request.realprepath = b'/' + b'/'.join(request.prepath)
    else:
        if not res.prepath.startswith(b'/'):
            request.realprepath = b'/' + res.prepath
        else:
            request.realprepath = res.prepath

    if path in res.children:
        retval = res.children[path]
    else:
        retval = res.getChild(path, request)

    if isinstance(retval, NoResource):
        retval = res
    else:
        request.realpostpath = request.path[
                               len(path) + (0 if path.startswith(b'/') else 1):]

    return retval


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
        return get_twisted_child_with_default(self, path, request)

    def render(self, request):
        if request.method == b'GET' and (
              request.uri.endswith(b'.wsdl') or request.uri.endswith(b'?wsdl')):
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

        retval = b''.join(p_ctx.out_string)

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

        initial_ctx.transport.file_info = _get_file_info(initial_ctx)

        contexts = self.http_transport.generate_contexts(initial_ctx)
        p_ctx, others = contexts[0], contexts[1:]

        p_ctx.active = True
        p_ctx.out_stream = request
        # TODO: Rate limiting
        p_ctx.active = True

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
            ret.addCallback(_cb_deferred, request, p_ctx, others, resource=self)
            ret.addErrback(_eb_deferred, request, p_ctx, others, resource=self)
            ret.addErrback(log_and_let_go, logger)

        elif isinstance(ret, PushBase):
            self.http_transport.init_root_push(ret, p_ctx, others)

        else:
            try:
                retval = _cb_deferred(p_ctx.out_object, request, p_ctx, others,
                                                                 self, cb=False)
            except Exception as e:
                logger_server.exception(e)
                try:
                    _eb_deferred(Failure(), request, p_ctx, others,
                                                                  resource=self)
                except Exception as e:
                    logger_server.exception(e)

        return retval

    def __handle_wsdl_request(self, request):
        # disabled for performance reasons.
        # logger.debug("WSDL request headers: %r",
        #                       list(request.requestHeaders.getAllRawHeaders()))

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


def _cb_deferred(ret, request, p_ctx, others, resource, cb=True):
    ### set response headers
    resp_code = p_ctx.transport.resp_code

    # If user code set its own response code, don't touch it.
    if resp_code is None:
        resp_code = HTTP_200
    request.setResponseCode(int(resp_code[:3]))

    _set_response_headers(request, p_ctx.transport.resp_headers)

    ### normalize response data
    om = p_ctx.descriptor.out_message
    single_class = None
    if cb:
        if p_ctx.descriptor.is_out_bare():
            p_ctx.out_object = [ret]

        elif (not issubclass(om, ComplexModelBase)) or len(om._type_info) <= 1:
            p_ctx.out_object = [ret]
            if len(om._type_info) == 1:
                single_class, = om._type_info.values()
        else:
            p_ctx.out_object = ret
    else:
        p_ctx.out_object = ret

    ### start response
    retval = NOT_DONE_YET

    if isinstance(ret, PushBase):
        resource.http_transport.init_root_push(ret, p_ctx, others)

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

            request.notifyFinish() \
                .addCallback(_close_only_context) \
                .addErrback(_eb_request_finished, request, p_ctx) \
                .addErrback(log_and_let_go, logger)

    else:
        ret = resource.http_transport.get_out_string(p_ctx)

        if not isinstance(ret, Deferred):
            producer = Producer(p_ctx.out_string, request)
            producer.deferred \
                .addCallback(_cb_request_finished, request, p_ctx) \
                .addErrback(_eb_request_finished, request, p_ctx) \
                .addErrback(log_and_let_go, logger)

            try:
                request.registerProducer(producer, False)
            except Exception as e:
                logger_server.exception(e)
                try:
                    _eb_deferred(Failure(), request, p_ctx, others, resource)
                except Exception as e:
                    logger_server.exception(e)
                    raise

        else:
            def _cb(ret):
                if isinstance(ret, Deferred):
                    return ret \
                        .addCallback(_cb) \
                        .addErrback(_eb_request_finished, request, p_ctx) \
                        .addErrback(log_and_let_go, logger)
                else:
                    return _cb_request_finished(ret, request, p_ctx)

            ret \
                .addCallback(_cb) \
                .addErrback(_eb_request_finished, request, p_ctx) \
                .addErrback(log_and_let_go, logger)

    process_contexts(resource.http_transport, others, p_ctx)

    return retval


def _eb_deferred(ret, request, p_ctx, others, resource):
    # DRY this with what's in Application.process_request
    if ret.check(Redirect):
        try:
            ret.value.do_redirect()

            # Now that the processing is switched to the outgoing message,
            # point ctx.protocol to ctx.out_protocol
            p_ctx.protocol = p_ctx.outprot_ctx

            _cb_deferred(None, request, p_ctx, others, resource, cb=False)

            p_ctx.fire_event('method_redirect')

        except Exception as e:
            logger_server.exception(e)
            p_ctx.out_error = Fault('Server', get_fault_string_from_exception(e))

            p_ctx.fire_event('method_redirect_exception')

    elif ret.check(Fault):
        p_ctx.out_error = ret.value

        ret = resource.handle_rpc_error(p_ctx, others, p_ctx.out_error, request)

        p_ctx.fire_event('method_exception_object')

        request.write(ret)

    else:
        p_ctx.out_error = InternalError(ret.value)
        logger.error(ret.getTraceback())

        ret = resource.handle_rpc_error(p_ctx, others, p_ctx.out_error, request)

        p_ctx.fire_event('method_exception_object')

        request.write(ret)

    request.finish()
