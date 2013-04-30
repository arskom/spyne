
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

from spyne.util.cdict import cdict

from spyne.const.http import HTTP_400
from spyne.const.http import HTTP_404
from spyne.const.http import HTTP_405
from spyne.const.http import HTTP_413
from spyne.const.http import HTTP_500

from spyne.error import Fault
from spyne.error import ResourceNotFoundError
from spyne.error import RequestTooLongError
from spyne.error import RequestNotAllowed

from spyne.model import ModelBase
from spyne.model import SimpleModel
from spyne.model import Null
from spyne.model.binary import ByteArray
from spyne.model.binary import File
from spyne.model.binary import Attachment
from spyne.model.complex import ComplexModelBase
from spyne.model.primitive import AnyXml
from spyne.model.primitive import AnyHtml
from spyne.model.primitive import Unicode
from spyne.model.primitive import String
from spyne.model.primitive import Decimal
from spyne.model.primitive import Double
from spyne.model.primitive import Integer
from spyne.model.primitive import Time
from spyne.model.primitive import DateTime
from spyne.model.primitive import Uuid
from spyne.model.primitive import Date
from spyne.model.primitive import Duration
from spyne.model.primitive import Boolean

from spyne.protocol._model import *


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
    :param ignore_uncap: Silently ignore cases when the protocol is not capable
        of serializing return values instead of raising a TypeError.
    """

    mime_type = 'application/octet-stream'

    SOFT_VALIDATION = type("Soft", (object,), {})
    REQUEST = type("Request", (object,), {})
    RESPONSE = type("Response", (object,), {})

    type = set()
    """Set that contains keywords about a protocol."""

    default_binary_encoding = None

    def __init__(self, app=None, validator=None, mime_type=None,
                                                            ignore_uncap=False):
        self.__app = None
        self.validator = None

        self.set_app(app)
        self.event_manager = EventManager(self)
        self.set_validator(validator)
        self.ignore_uncap = ignore_uncap
        if mime_type is not None:
            self.mime_type = mime_type

        self._to_string_handlers = cdict({
            ModelBase: lambda cls, value: cls.to_string(value),
            Time: time_to_string,
            Uuid: uuid_to_string,
            Null: null_to_string,
            Double: double_to_string,
            AnyXml: any_xml_to_string,
            Unicode: unicode_to_string,
            Boolean: boolean_to_string,
            Decimal: decimal_to_string,
            Integer: integer_to_string,
            AnyHtml: any_html_to_string,
            DateTime: datetime_to_string,
            Duration: duration_to_string,
            ByteArray: byte_array_to_string,
            Attachment: attachment_to_string,
            ComplexModelBase: complex_model_base_to_string,
        })

        self._to_string_iterable_handlers = cdict({
            File: file_to_string_iterable,
            ByteArray: byte_array_to_string_iterable,
            ModelBase: lambda prot, cls, value: cls.to_string_iterable(value),
            SimpleModel: lambda prot, cls, value: (prot._to_string_handlers[cls](cls, value),),
        })

        self._from_string_handlers = cdict({
            Null: null_from_string,
            Time: time_from_string,
            Date: date_from_string,
            Uuid: uuid_from_string,
            File: file_from_string,
            Double: double_from_string,
            String: string_from_string,
            AnyXml: any_xml_from_string,
            Boolean: boolean_from_string,
            Integer: integer_from_string,
            Unicode: unicode_from_string,
            Decimal: decimal_from_string,
            AnyHtml: any_html_from_string,
            DateTime: datetime_from_string,
            Duration: duration_from_string,
            ByteArray: byte_array_from_string,
            Attachment: attachment_from_string,
            ComplexModelBase: complex_model_base_from_string
        })

        self._to_dict_handlers = cdict({
            ModelBase: lambda cls, value: cls.to_dict(value),
            ComplexModelBase: complex_model_base_to_dict,
            Fault: fault_to_dict,
        })

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

        return HTTP_500

    def set_validator(self, validator):
        """You must override this function if you want your protocol to support
        validation."""

        assert validator is None

        self.validator = None

    def from_string(self, class_, string, *args, **kwargs):
        handler = self._from_string_handlers[class_]
        return handler(class_, string, *args, **kwargs)

    def to_string(self, class_, value, *args, **kwargs):
        handler = self._to_string_handlers[class_]
        return handler(class_, value, *args, **kwargs)

    def to_string_iterable(self, class_, value):
        handler = self._to_string_iterable_handlers[class_]
        return handler(self, class_, value)

    def to_dict(self, class_, value):
        handler = self._to_dict_handlers[class_]
        return handler(class_, value)
