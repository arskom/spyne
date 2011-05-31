
#
# rpclib - Copyright (C) Rpclib contributors.
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

import cgi
from rpclib.model.exception import Fault

class ValidationError(Fault):
    pass

class Base(object):
    allowed_http_verbs = ['GET','POST']
    mime_type = 'application/octet-stream'

    def __init__(self, parent):
        self.parent = parent

    def create_in_document(self, ctx, in_string_encoding=None):
        """Uses ctx.in_string to set ctx.in_document"""

    def decompose_incoming_envelope(self, ctx):
        """Sets the ctx.in_body_doc, ctx.in_header_doc and ctx.service
        properties of the ctx object, if applicable.
        """

    def deserialize(self, ctx):
        """Takes a MethodContext instance and a string containing ONE document
        instance in the ctx.in_string attribute.

        Returns the corresponding native python object in the ctx.in_object
        attribute.
        """

    def serialize(self, ctx):
        """Takes a MethodContext instance and the object to be serialied in the
        ctx.out_object attribute.

        Returns the corresponding document structure in the ctx.out_document
        attribute.
        """

    def create_out_string(self, ctx):
        """Uses ctx.out_string to set ctx.out_document"""

    def reconstruct_wsgi_request(self, http_env):
        """Reconstruct http payload using information in the http header"""

        input = http_env.get('wsgi.input')
        try:
            length = int(http_env.get("CONTENT_LENGTH"))
        except ValueError:
            length = 0

        # fyi, here's what the parse_header function returns:
        # >>> import cgi; cgi.parse_header("text/xml; charset=utf-8")
        # ('text/xml', {'charset': 'utf-8'})
        content_type = cgi.parse_header(http_env.get("CONTENT_TYPE"))
        charset = content_type[1].get('charset',None)
        if charset is None:
            charset = 'ascii'

        return input.read(length), charset

    def validate(self, payload):
        """Method to be overriden to perform any sort of custom input
        validation.
        """
