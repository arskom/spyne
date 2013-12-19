
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


from spyne import TransportContext
from spyne import MethodContext
from spyne.server import ServerBase


class HttpTransportContext(TransportContext):
    """The abstract base class that is used in the transport attribute of the
    :class:`HttpMethodContext` class and its subclasses."""

    def __init__(self, parent, transport, request, content_type):
        super(HttpTransportContext, self).__init__(parent, transport, 'http')

        self.req = request
        """HTTP Request. This is transport-specific"""

        self.resp_headers = {
        }
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
        super(HttpMethodContext, self).__init__(transport)

        self.transport = self.default_transport_context(self, transport, req_env,
                                                                   content_type)
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
