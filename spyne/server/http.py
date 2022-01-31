# encoding: utf8
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

from email import utils
from email.utils import encode_rfc2231
from email.message import tspecials

from spyne import TransportContext, MethodDescriptor, MethodContext, Redirect
from spyne.server import ServerBase
from spyne.protocol.http import HttpPattern
from spyne.const.http import gen_body_redirect, HTTP_301, HTTP_302, HTTP_303, \
    HTTP_307


class HttpRedirect(Redirect):
    def __init__(self, ctx, location, orig_exc=None, code=HTTP_302):
        super(HttpRedirect, self) \
                      .__init__(ctx, location, orig_exc=orig_exc)

        self.ctx = ctx
        self.location = location
        self.orig_exc = orig_exc
        self.code = code

    def do_redirect(self):
        if not isinstance(self.ctx.transport, HttpTransportContext):
            if self.orig_exc is not None:
                raise self.orig_exc
            raise TypeError(self.ctx.transport)

        self.ctx.transport.respond(self.code, location=self.location)

#
# Plagiarized HttpTransport.add_header() and _formatparam() function from
# Python 2.7 stdlib.
#
# Copyright (C) 2001-2007 Python Software Foundation
# Author: Barry Warsaw
# Contact: email-sig@python.org
#
def _formatparam(param, value=None, quote=True):
    """Convenience function to format and return a key=value pair.

    This will quote the value if needed or if quote is true.  If value is a
    three tuple (charset, language, value), it will be encoded according
    to RFC2231 rules.  If it contains non-ascii characters it will likewise
    be encoded according to RFC2231 rules, using the utf-8 charset and
    a null language.
    """
    if value is None or len(value) == 0:
        return param

    # A tuple is used for RFC 2231 encoded parameter values where items
    # are (charset, language, value).  charset is a string, not a Charset
    # instance.  RFC 2231 encoded values are never quoted, per RFC.
    if isinstance(value, tuple):
        # Encode as per RFC 2231
        param += '*'
        value = encode_rfc2231(value[2], value[0], value[1])
        return '%s=%s' % (param, value)

    try:
        value.encode('ascii')

    except UnicodeEncodeError:
        param += '*'
        value = encode_rfc2231(value, 'utf-8', '')
        return '%s=%s' % (param, value)

    # BAW: Please check this.  I think that if quote is set it should
    # force quoting even if not necessary.
    if quote or tspecials.search(value):
        return '%s="%s"' % (param, utils.quote(value))

    return '%s=%s' % (param, value)


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

    def get_url(self):
        raise NotImplementedError()

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

    def get_peer(self):
        raise NotImplementedError()

    @staticmethod
    def gen_header(_value, **kwargs):
        parts = []

        for k, v in kwargs.items():
            if v is None:
                parts.append(k.replace('_', '-'))

            else:
                parts.append(_formatparam(k.replace('_', '-'), v))

        if _value is not None:
            parts.insert(0, _value)

        return '; '.join(parts)

    def add_header(self, _name, _value, **kwargs):
        """Extended header setting.

        name is the header field to add.  keyword arguments can be used to set
        additional parameters for the header field, with underscores converted
        to dashes.  Normally the parameter will be added as key="value" unless
        value is None, in which case only the key will be added.  If a
        parameter value contains non-ASCII characters it can be specified as a
        three-tuple of (charset, language, value), in which case it will be
        encoded according to RFC2231 rules.  Otherwise it will be encoded using
        the utf-8 charset and a language of ''.

        Examples:

        msg.add_header('content-disposition', 'attachment', filename='bud.gif')
        msg.add_header('content-disposition', 'attachment',
                       filename=('utf-8', '', Fußballer.ppt'))
        msg.add_header('content-disposition', 'attachment',
                       filename='Fußballer.ppt'))
        """

        self.resp_headers[_name] = self.gen_header(_value, **kwargs)

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

    # because ctor signatures differ between TransportContext and
    # HttpTransportContext, we needed a new variable
    TransportContext = None
    HttpTransportContext = HttpTransportContext

    def __init__(self, transport, req_env, content_type):
        super(HttpMethodContext, self).__init__(transport, MethodContext.SERVER)

        self.transport = self.HttpTransportContext(self, transport,
                                                          req_env, content_type)
        """Holds the HTTP-specific information"""

    def set_out_protocol(self, what):
        self._out_protocol = what
        if self._out_protocol.app is None:
            self._out_protocol.set_app(self.app)
        if isinstance(self.transport, HttpTransportContext):
            self.transport.set_mime_type(what.mime_type)

    out_protocol = property(MethodContext.get_out_protocol, set_out_protocol)
    """Assigning an out protocol overrides the mime type of the transport."""


class HttpBase(ServerBase):
    transport = 'http://schemas.xmlsoap.org/soap/http'

    SLASH = '/'
    SLASHPER = '/%s'

    def __init__(self, app, chunked=False,
                max_content_length=2 * 1024 * 1024,
                block_length=8 * 1024):
        super(HttpBase, self).__init__(app)

        self.chunked = chunked
        self.max_content_length = max_content_length
        self.block_length = block_length

        self._http_patterns = set()

        for k, v in self.app.interface.service_method_map.items():
            # p_ stands for primary, ie the non-aux method
            p_method_descriptor = v[0]
            for patt in p_method_descriptor.patterns:
                if isinstance(patt, HttpPattern):
                    self._http_patterns.add(patt)

        # this makes sure similar addresses with patterns are evaluated after
        # addresses with wildcards, which puts the more specific addresses to
        # the front.
        self._http_patterns = list(reversed(sorted(self._http_patterns,
                                           key=lambda x: (x.address, x.host) )))

    @classmethod
    def get_patt_verb(cls, patt):
        return patt.verb_re

    @classmethod
    def get_patt_host(cls, patt):
        return patt.host_re

    @classmethod
    def get_patt_address(cls, patt):
        return patt.address_re

    def match_pattern(self, ctx, method='', path='', host=''):
        """Sets ctx.method_request_string if there's a match. It's O(n) which
        means you should keep your number of patterns as low as possible.

        :param ctx: A MethodContext instance
        :param method: The verb in the HTTP Request (GET, POST, etc.)
        :param host: The contents of the ``Host:`` header
        :param path: Path but not the arguments. (i.e. stuff before '?', if it's
            there)
        """

        if not path.startswith(self.SLASH):
            path = self.SLASHPER % (path,)

        params = defaultdict(list)
        for patt in self._http_patterns:
            assert isinstance(patt, HttpPattern)

            if patt.verb is not None:
                match = self.get_patt_verb(patt).match(method)
                if match is None:
                    continue
                if not (match.span() == (0, len(method))):
                    continue

                for k,v in match.groupdict().items():
                    params[k].append(v)

            if patt.host is not None:
                match = self.get_patt_host(patt).match(host)
                if match is None:
                    continue
                if not (match.span() == (0, len(host))):
                    continue

                for k, v in match.groupdict().items():
                    params[k].append(v)

            if patt.address is None:
                if path.split(self.SLASH)[-1] != patt.endpoint.name:
                    continue

            else:
                match = self.get_patt_address(patt).match(path)
                if match is None:
                    continue

                if not (match.span() == (0, len(path))):
                    continue

                for k,v in match.groupdict().items():
                    params[k].append(v)

            d = patt.endpoint
            assert isinstance(d, MethodDescriptor)
            ctx.method_request_string = d.name

            break

        return params

    @property
    def has_patterns(self):
        return len(self._http_patterns) > 0
