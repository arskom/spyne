
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

from collections import defaultdict

from spyne import TransportContext, MethodDescriptor, MethodContext, Redirect
from spyne.server import ServerBase
from spyne.const.http import gen_body_redirect, \
    HTTP_301, HTTP_302, HTTP_303, HTTP_307
from spyne.protocol.http import HttpPattern


class HttpRedirect(Redirect):
    def do_redirect(self):
        if not isinstance(self.ctx.transport, HttpTransportContext):
            if self.orig_exc is not None:
                raise self.orig_exc
            raise TypeError(self.ctx.transport)

        self.ctx.transport.respond(HTTP_302, location=self.location)


class HttpTransportContext(TransportContext):
    """The abstract base class that is used in the transport attribute of the
    :class:`HttpMethodContext` class and its subclasses."""

    def __init__(self, parent, transport, request, content_type):
        super(HttpTransportContext, self).__init__(parent, transport, 'http')

        self.req = request
        """HTTP Request. This is transport-specific"""

        self.resp_headers = {}
        """HTTP Response headers."""

        self.mime_type = content_type

        self.resp_code = None
        """HTTP Response code."""

        self.wsdl = None
        """The WSDL document that is being returned. Only relevant when handling
        WSDL requests."""

        self.wsdl_error = None
        """The error when handling WSDL requests."""

    def get_mime_type(self):
        return self.resp_headers.get('Content-Type', None)

    def set_mime_type(self, what):
        self.resp_headers['Content-Type'] = what

    def respond(self, resp_code, **kwargs):
        self.resp_code = resp_code
        if resp_code in (HTTP_301, HTTP_302, HTTP_303, HTTP_307):
            l = kwargs.pop('location')
            self.resp_headers['Location'] = l
            self.parent.out_string = [gen_body_redirect(resp_code, l)]
            self.mime_type = 'text/html'

        else:
            # So that deserialization is skipped.
            self.parent.out_string = []

    def get_path(self):
        raise NotImplementedError()

    def get_request_method(self):
        raise NotImplementedError()

    def get_request_content_type(self):
        raise NotImplementedError()

    def get_path_and_qs(self):
        raise NotImplementedError()

    def get_cookie(self, key):
        raise NotImplementedError()

    mime_type = property(
        lambda self: self.get_mime_type(),
        lambda self, what: self.set_mime_type(what),
    )
    """Provides an easy way to set outgoing mime type. Synonym for
    `content_type`"""

    content_type = mime_type
    """Provides an easy way to set outgoing mime type. Synonym for
    `mime_type`"""


class HttpMethodContext(MethodContext):
    """The Http-Specific method context. Http-Specific information is stored in
    the transport attribute using the :class:`HttpTransportContext` class.
    """

    default_transport_context = HttpTransportContext

    def __init__(self, transport, req_env, content_type):
        super(HttpMethodContext, self).__init__(transport, MethodContext.SERVER)

        self.transport = self.default_transport_context(self, transport,
                                                          req_env, content_type)
        """Holds the WSGI-specific information"""

    def set_out_protocol(self, what):
        self._out_protocol = what
        if isinstance(self.transport, HttpTransportContext):
            self.transport.set_mime_type(what.mime_type)

    out_protocol = property(MethodContext.get_out_protocol, set_out_protocol)
    """Assigning an out protocol overrides the mime type of the transport."""


class HttpBase(ServerBase):
    transport = 'http://schemas.xmlsoap.org/soap/http'

    def __init__(self, app, chunked=False,
                max_content_length=2 * 1024 * 1024,
                block_length=8 * 1024):
        super(HttpBase, self).__init__(app)

        self.chunked = chunked
        self.max_content_length = max_content_length
        self.block_length = block_length

        self._http_patterns = set()

        for k, v in self.app.interface.service_method_map.items():
            # p_ stands for primary
            p_method_descriptor = v[0]
            for patt in p_method_descriptor.patterns:
                if isinstance(patt, HttpPattern):
                    self._http_patterns.add(patt)

        # this makes sure similar addresses with patterns are evaluated after
        # addresses with wildcards, which puts the more specific addresses to
        # the front.
        self._http_patterns = list(reversed(sorted(self._http_patterns,
                                          key=lambda x: (x.address, x.host) )))

    def match_pattern(self, ctx, method='', path='', host=''):
        """Sets ctx.method_request_string if there's a match. It's O(n) which
        means you should keep your number of patterns as low as possible.

        :param ctx: A MethodContext instance
        :param method: The verb in the HTTP Request (GET, POST, etc.)
        :param host: The contents of the ``Host:`` header
        :param path: Path but not the arguments. (i.e. stuff before '?', if it's
            there)
        """

        if not path.startswith('/'):
            path = '/' + path

        params = defaultdict(list)
        for patt in self._http_patterns:
            assert isinstance(patt, HttpPattern)

            if patt.verb is not None:
                match = patt.verb_re.match(method)
                if match is None:
                    continue
                if not (match.span() == (0, len(method))):
                    continue

                for k,v in match.groupdict().items():
                    params[k].append(v)

            if patt.host is not None:
                match = patt.host_re.match(host)
                if match is None:
                    continue
                if not (match.span() == (0, len(host))):
                    continue

                for k,v in match.groupdict().items():
                    params[k].append(v)

            assert patt.address is not None

            match = patt.address_re.match(path)
            if match is None:
                continue
            if not (match.span() == (0, len(path))):
                continue
            for k,v in match.groupdict().items():
                params[k].append(v)

            d = patt.endpoint
            assert isinstance(d, MethodDescriptor)
            if d.parent_class is not None and d.in_message_name_override:
                ctx.method_request_string = '%s.%s' % (
                                           d.in_message.get_type_name(), d.name)
            else:
                ctx.method_request_string = patt.endpoint.name
            break

        return params

    @property
    def has_patterns(self):
        return len(self._http_patterns) > 0
