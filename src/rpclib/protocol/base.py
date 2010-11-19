
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

class Base(object):
    options = {}
    def __init__(self, parent):
        self.parent = parent

    def create_document_structure(self, in_string, in_string_encoding=None):
        pass

    def decompose_incoming_envelope(self, ctx, envelope_xml):
        """Sets the ctx.in_body_doc, ctx.in_header_doc and ctx.service
        properties of the ctx object.
        """

    def deserialize(self, ctx, wrapper, envelope_xml):
        """Takes a MethodContext instance and a string containing ONE document
        instance.

        Returns the corresponding native python object
        """

    def serialize(self, ctx, wrapper, out_object):
        """Takes a MethodContext instance and the object to be serialied.

        Returns the corresponding document structure.
        """
    def create_document_string():
        pass

    def set_options(self, **kwargs):
        for k in kwargs:
            assert k in Base.options
            self.options[k] = kwargs[k]
