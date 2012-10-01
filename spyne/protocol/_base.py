
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

import logging
logger = logging.getLogger(__name__)

from copy import copy

from spyne import EventManager

from spyne.const.http import HTTP_400
from spyne.const.http import HTTP_404
from spyne.const.http import HTTP_405
from spyne.const.http import HTTP_413
from spyne.const.http import HTTP_500

from spyne.error import Fault
from spyne.error import ResourceNotFoundError
from spyne.error import RequestTooLongError
from spyne.error import RequestNotAllowed

from spyne.model.complex import Array


def unwrap_messages(cls, skip_depth):
    out_type = cls
    for _ in range(skip_depth):
        if hasattr(out_type, "_type_info") and len(out_type._type_info) == 1:
            out_type = out_type._type_info[0]
        else:
            break

    return out_type


def unwrap_instance(cls, inst, skip_depth):
    out_type = cls
    out_instance = inst

    for _ in range(skip_depth):
        if hasattr(out_type, "_type_info") and len(out_type._type_info) == 1:
            (k, t), = out_type._type_info.items()
            if not issubclass(out_type, Array):
                out_instance = getattr(out_instance, k)
            out_type = t

        else:
            break

    return out_type, out_instance


class ProtocolBase(object):
    """This is the abstract base class for all protocol implementations. Child
    classes can implement only the required subset of the public methods.

    An output protocol must implement :func:`serialize` and
    :func:`create_out_string`.

    An input protocol must implement :func:`create_in_document`,
    :func:`decompose_incoming_envelope` and :func:`deserialize`.

    The ProtocolBase class supports the following events:

    * ``before_deserialize``:
      Called before the deserialization operation is attempted.

    * ``after_deserialize``:
      Called after the deserialization operation is finished.

    * ``before_serialize``:
      Called before after the serialization operation is attempted.

    * ``after_serialize``:
      Called after the serialization operation is finished.

    The arguments the constructor takes are as follows:

    :param app: The application this protocol belongs to.
    :param validator: The type of validation this protocol should do on
        incoming data.
    :param mime_type: The mime_type this protocol should set for transports
        that support this. This is a quick way to override the mime_type by
        default instead of subclassing the releavant protocol implementation.
    :param skip_depth: Number of wrapper classes to ignore. This is
        typically one of (0, 1, 2) but higher numbers may also work for your
        case.
    """

    allowed_http_verbs = None
    mime_type = 'application/octet-stream'

    SOFT_VALIDATION = type("Soft", (object,), {})
    REQUEST = type("Request", (object,), {})
    RESPONSE = type("Response", (object,), {})

    def __init__(self, app=None, validator=None, mime_type=None, skip_depth=0):
        self.__app = None
        self.validator = None

        self.set_app(app)
        self.event_manager = EventManager(self)
        self.set_validator(validator)
        self.skip_depth = skip_depth
        if mime_type is not None:
            self.mime_type = mime_type

    @property
    def app(self):
        return self.__app

    def set_app(self, value):
        assert self.__app is None, "One protocol instance should belong to one " \
                                   "application instance."
        self.__app = value

    def create_in_document(self, ctx, in_string_encoding=None):
        """Uses ``ctx.in_string`` to set ``ctx.in_document``."""

    def decompose_incoming_envelope(self, ctx, message):
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
        """Uses ctx.out_document to set ctx.out_string"""

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
        """Generates MethodContext instances for every callable assigned to the
        given method handle.

        The first element in the returned list is always the primary method
        context whereas the rest are all auxiliary method contexts.
        """

        call_handles = self.get_call_handles(ctx)
        if len(call_handles) == 0:
            raise ResourceNotFoundError('Method %r not found.' %
                                                      ctx.method_request_string)

        retval = []
        for sc, d in call_handles:
            c = copy(ctx)

            assert d != None

            c.descriptor = d
            c.service_class = sc

            retval.append(c)

        return retval

    def get_call_handles(self, ctx):
        """Method to be overriden to perform any sort of custom method mapping
        using any data in the method context. Returns a list of contexts.
        Can return multiple contexts if a method_request_string matches more
        than one function. (This is called the fanout mode.)
        """

        name = ctx.method_request_string
        if not name.startswith("{"):
            name = '{%s}%s' % (self.app.interface.get_tns(), name)

        call_handles = self.app.interface.service_method_map.get(name, [])

        return call_handles

    def fault_to_http_response_code(self, fault):
        """Special function to convert native Python exceptions to Http response
        codes.
        """

        if isinstance(fault, RequestTooLongError):
            return HTTP_413
        if isinstance(fault, ResourceNotFoundError):
            return HTTP_404
        if isinstance(fault, RequestNotAllowed):
            return HTTP_405
        if isinstance(fault, Fault) and (fault.faultcode.startswith('Client.')
                                                or fault.faultcode == 'Client'):
            return HTTP_400
        else:
            return HTTP_500

    def set_validator(self, validator):
        """You must override this function if you want your protocol to support
        validation."""

        assert validator is None

        self.validator = None
