
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

    def __init__(self, transport, request, content_type):
        TransportContext.__init__(self, transport, 'http')

        self.req = request
        """HTTP Request. This is transport-specific"""

        assert isinstance(content_type, str)
        self.resp_headers = {
            'Content-Type': content_type,
            'Content-Length': None,
        }
        """HTTP Response headers."""

        self.resp_code = None
        """HTTP Response code."""

        self.wsdl = None
        """The WSDL document that is being returned. Only relevant when handling
        WSDL requests."""

        self.wsdl_error = None
        """The error when handling WSDL requests."""

    def get_mime_type(self):
        return self.resp_headers['Content-Type']

    def set_mime_type(self, what):
        self.resp_headers['Content-Type'] = what

    mime_type = property(get_mime_type, set_mime_type)
    """Provides an easy way to set outgoing mime type. Synonym for
    `content_type`"""

    content_type = property(get_mime_type, set_mime_type)
    """Provides an easy way to set outgoing mime type. Synonym for
    `mime_type`"""


class HttpMethodContext(MethodContext):
    """The Http-Specific method context. Http-Specific information is stored in
    the transport attribute using the :class:`HttpTransportContext` class.
    """

    def __init__(self, transport, req_env, content_type):
        MethodContext.__init__(self, transport)

        self.transport = HttpTransportContext(transport, req_env, content_type)
        """Holds the WSGI-specific information"""


class HttpBase(ServerBase):
    transport = 'http://schemas.xmlsoap.org/soap/http'

    def __init__(self, app, chunked=False,
                max_content_length=2 * 1024 * 1024,
                block_length=8 * 1024):
        ServerBase.__init__(self, app)

        self._allowed_http_verbs = app.in_protocol.allowed_http_verbs

        self.chunked = chunked
        self.max_content_length = max_content_length
        self.block_length = block_length
