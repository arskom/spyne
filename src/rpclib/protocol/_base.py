
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

import logging
logger = logging.getLogger(__name__)

import rpclib.const.xml_ns

_ns_xsi = rpclib.const.xml_ns.xsi
_ns_xsd = rpclib.const.xml_ns.xsd

from rpclib._base import EventManager
from rpclib.model.fault import Fault

class ValidationError(Fault):
    pass

class ProtocolBase(object):
    allowed_http_verbs = ['GET','POST']
    mime_type = 'application/octet-stream'

    def __init__(self, app=None):
        self.__app = None

        self.set_app(app)
        self.event_manager = EventManager(self)

    @property
    def app(self):
        return self.__app

    def set_app(self, value):
        assert self.__app is None, "One protocol instance should belong to one " \
                                   "application instance."
        self.__app = value

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

    def create_out_string(self, ctx, out_string_encoding=None):
        """Uses ctx.out_string to set ctx.out_document"""

    def validate(self, payload):
        """Method to be overriden to perform any sort of custom input
        validation.
        """

    def set_method_descriptor(self, ctx):
        """Method to be overriden to perform any sort of custom matching between
        the method_request_string and the methods.
        """

        name = ctx.method_request_string
        if not name.startswith("{"):
            name = '{%s}%s' % (self.app.interface.get_tns(), name)

        ctx.service_class = self.app.interface.service_mapping.get(name, None)
        if ctx.service_class is None:
            logger.debug(self.app.interface.service_mapping.keys())
            raise Exception('Method %r not bound to a service class.' % name)

        ctx.descriptor = ctx.app.interface.method_mapping.get(name, None)
        if ctx.descriptor is None:
            logger.debug(ctx.app.interface.method_mapping.keys())
            raise Exception('Method %r not found.' % name)
