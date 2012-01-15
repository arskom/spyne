
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

"""This module contains the ProtocolBase abstract base class for all
protocol implementations.
"""

import logging
logger = logging.getLogger(__name__)

import rpclib.const.xml_ns
from copy import copy

_ns_xsi = rpclib.const.xml_ns.xsi
_ns_xsd = rpclib.const.xml_ns.xsd

from rpclib._base import EventManager

from rpclib.const.http import HTTP_400
from rpclib.const.http import HTTP_404
from rpclib.const.http import HTTP_413
from rpclib.const.http import HTTP_500

from rpclib.error import ResourceNotFoundError
from rpclib.error import RequestTooLongError
from rpclib.error import Fault

class ProtocolBase(object):
    """This is the abstract base class for all protocol implementations. Child
    classes can implement only the required subset of the public methods.

    The ProtocolBase class supports the following events:
    
    * ``before_deserialize``:
      Called before the deserialization operation is attempted.

    * ``after_deserialize``:
      Called after the deserialization operation is finished.

    * ``before_serialize``:
      Called before after the serialization operation is attempted.

    * ``after_serialize``:
      Called after the serialization operation is finished.
    """

    allowed_http_verbs = ['GET', 'POST']
    mime_type = 'application/octet-stream'

    SOFT_VALIDATION = type("soft", (object,), {})
    REQUEST = type("request", (object,), {})
    RESPONSE = type("response", (object,), {})

    def __init__(self, app=None, validator=None):
        self.__app = None
        self.validator = None

        self.set_app(app)
        self.event_manager = EventManager(self)
        self.set_validator(validator)

    @property
    def app(self):
        """The :class:`rpclib.application.Application` instance this protocol
        belongs to.
        """

        return self.__app

    def set_app(self, value):
        assert self.__app is None, "One protocol instance should belong to one " \
                                   "application instance."
        self.__app = value

    def create_in_document(self, ctx, in_string_encoding=None):
        """Uses ``ctx.in_string`` to set ``ctx.in_document``."""

    def decompose_incoming_envelope(self, ctx):
        """Sets the ``ctx.method_request_string``, ``ctx.in_body_doc``,
        ``ctx.in_header_doc`` and ``ctx.service`` properties of the ctx object,
        if applicable.
        """

    def deserialize(self, ctx):
        """Takes a MethodContext instance and a string containing ONE document
        instance in the ``ctx.in_string`` attribute.

        Returns the corresponding native python object in the ctx.in_object
        attribute.
        """

    def serialize(self, ctx):
        """Takes a MethodContext instance and the object to be serialized in the
        ctx.out_object attribute.

        Returns the corresponding document structure in the ctx.out_document
        attribute.
        """

    def create_out_string(self, ctx, out_string_encoding=None):
        """Uses ctx.out_string to set ctx.out_document"""

    def validate_document(self, payload):
        """Method to be overriden to perform any sort of custom input
        validation on the parsed input document.
        """

    def set_method_descriptor(self, ctx):
        """DEPRECATED! Use :func:`generate_method_contexts` instead.

        Method to be overriden to perform any sort of custom matching between
        the method_request_string and the methods.
        """

        name = ctx.method_request_string
        if not name.startswith("{"):
            name = '{%s}%s' % (self.app.interface.get_tns(), name)

        ctx.service_class = self.app.interface.service_mapping.get(name, None)
        if ctx.service_class is None:
            raise ResourceNotFoundError('Method %r not bound to a service class.'
                                                                        % name)

        ctx.descriptor = ctx.app.interface.method_mapping.get(name, None)
        if ctx.descriptor is None:
            raise ResourceNotFoundError('Method %r not found.' % name)

    def generate_method_contexts(self, ctx):
        """Method to be overriden to perform any sort of custom matching between
        the method_request_string and the methods. Returns a list of contexts.
        Can return multiple contexts if a method_request_string matches more
        than one function. (This is called the fanout mode.)
        """

        name = ctx.method_request_string
        if not name.startswith("{"):
            name = '{%s}%s' % (self.app.interface.get_tns(), name)

        call_handles = self.app.interface.service_method_map.get(name, [])
        if len(call_handles) == 0:
            raise ResourceNotFoundError('Method %r not found.' % name)

        retval = []
        for sc, d in call_handles:
            c = copy(ctx)

            assert d != None

            c.descriptor = d
            c.service_class = sc

            retval.append(c)

        return retval

    def fault_to_http_response_code(self, fault):
        if isinstance(fault, RequestTooLongError):
            return HTTP_413
        if isinstance(fault, ResourceNotFoundError):
            return HTTP_404
        if isinstance(fault, Fault) and (fault.faultcode.startswith('Client.')
                                                or fault.faultcode == 'Client'):
            return HTTP_400
        else:
            return HTTP_500

    def set_validator(self, validator):
        """You must override this function if your protocol supports validation.
        """

        assert validator is None

        self.validator = None
