
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

from rpclib.util.cdict import cdict

from rpclib.model import ModelBase

from rpclib.model.complex import Array
from rpclib.model.complex import Iterable
from rpclib.model.complex import ComplexModelBase
from rpclib.model.enum import EnumBase
from rpclib.model.fault import Fault
from rpclib.model.primitive import AnyXml
from rpclib.model.primitive import AnyDict
from rpclib.model.primitive import String
from rpclib.model.primitive import AnyUri
from rpclib.model.primitive import Decimal
from rpclib.model.primitive import Integer
from rpclib.model.primitive import UnsignedInteger
from rpclib.model.primitive import UnsignedInteger64
from rpclib.model.primitive import UnsignedInteger32
from rpclib.model.primitive import UnsignedInteger16
from rpclib.model.primitive import UnsignedInteger8
from rpclib.model.primitive import Date
from rpclib.model.primitive import DateTime
from rpclib.model.primitive import Duration
from rpclib.model.primitive import Double
from rpclib.model.primitive import Float
from rpclib.model.primitive import Boolean
from rpclib.model.primitive import Mandatory

from rpclib.protocol import ProtocolBase

from rpclib.protocol.xml.model import base_to_parent_element
from rpclib.protocol.xml.model.enum import enum_to_parent_element
from rpclib.protocol.xml.model.fault import fault_to_parent_element
from rpclib.protocol.xml.model.complex import complex_to_parent_element
from rpclib.protocol.xml.model.primitive import xml_to_parent_element
from rpclib.protocol.xml.model.primitive import dict_to_parent_element
from rpclib.protocol.xml.model.primitive import string_to_parent_element
from rpclib.protocol.xml.model.primitive import duration_to_parent_element

from rpclib.protocol.xml.model import base_from_element
from rpclib.protocol.xml.model.complex import array_from_element
from rpclib.protocol.xml.model.complex import iterable_from_element
from rpclib.protocol.xml.model.complex import complex_from_element
from rpclib.protocol.xml.model.enum import enum_from_element
from rpclib.protocol.xml.model.fault import fault_from_element
from rpclib.protocol.xml.model.primitive import dict_from_element
from rpclib.protocol.xml.model.primitive import xml_from_element
from rpclib.protocol.xml.model.primitive import string_from_element

_serialization_handlers = cdict({
    ModelBase: base_to_parent_element,
    ComplexModelBase: complex_to_parent_element,
    Fault: fault_to_parent_element,
    String: string_to_parent_element,
    AnyXml: xml_to_parent_element,
    AnyDict: dict_to_parent_element,
    EnumBase: enum_to_parent_element,
    Duration: duration_to_parent_element,
#    AnyUri: any_uri_serialize
#    Decimal: any_uri_serialize
#    Int:
#    Integer:
#    UnsignedInteger:
#    UnsignedInteger64:
#    UnsignedInteger32:
#    UnsignedInteger16:
#    UnsignedInteger8:
#    Date:
#    DateTime:
#    Double:
#    Float:
#    Boolean:
})

_deserialization_handlers = cdict({
    ModelBase: base_from_element,
    ComplexModelBase: complex_from_element,
    Fault: fault_from_element,
    String: string_from_element,
    AnyXml: xml_from_element,
    AnyDict: dict_from_element,
    Array: array_from_element,
    Iterable: iterable_from_element,
    EnumBase: enum_from_element,
})

class XmlObject(ProtocolBase):
    def create_in_document(self, ctx, in_string_encoding=None):
        """Uses ctx.in_string to set ctx.in_document"""
        raise NotImplementedError()

    def decompose_incoming_envelope(self, ctx):
        """Sets the ctx.in_body_doc, ctx.in_header_doc and ctx.service
        properties of the ctx object, if applicable.
        """
        raise NotImplementedError()

    def from_element(self, cls, element):
        handler = _deserialization_handlers[cls]
        logger.debug("-"*20)
        return handler(self, cls, element)

    def to_parent_element(self, cls, value, tns, parent_elt, *args, **kwargs):
        handler = _serialization_handlers[cls]
        logger.debug("-"*20)
        handler(self, cls, value, tns, parent_elt, *args, **kwargs)

    def deserialize(self, ctx):
        """Takes a MethodContext instance and a string containing ONE document
        instance in the ctx.in_string attribute.

        Returns the corresponding native python object in the ctx.in_object
        attribute.
        """
        raise NotImplementedError()

    def serialize(self, ctx):
        """Takes a MethodContext instance and the object to be serialied in the
        ctx.out_object attribute.

        Returns the corresponding document structure in the ctx.out_document
        attribute.
        """
        raise NotImplementedError()

    def create_out_string(self, ctx, out_string_encoding=None):
        """Uses ctx.out_string to set ctx.out_document"""
        raise NotImplementedError()

    def validate(self, payload):
        """Method to be overriden to perform any sort of custom input
        validation.
        """
