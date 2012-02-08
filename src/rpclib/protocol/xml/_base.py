
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
logger = logging.getLogger('rpclib.protocol.xml')

from lxml import etree

from rpclib import _bytes_join

from rpclib.const import xml_ns as ns
from rpclib.const.ansi_color import LIGHT_GREEN
from rpclib.const.ansi_color import LIGHT_RED
from rpclib.const.ansi_color import END_COLOR

from rpclib.util.cdict import cdict
from rpclib.model import ModelBase
from rpclib.model.binary import ByteArray
from rpclib.model.binary import Attachment
from rpclib.model.complex import Array
from rpclib.model.complex import Iterable
from rpclib.model.complex import ComplexModelBase
from rpclib.model.enum import EnumBase
from rpclib.model.fault import Fault
from rpclib.model.primitive import AnyXml
from rpclib.model.primitive import AnyDict

from rpclib.protocol import ProtocolBase

from rpclib.protocol.xml.model import base_to_parent_element
from rpclib.protocol.xml.model.binary import binary_to_parent_element
from rpclib.protocol.xml.model.enum import enum_to_parent_element
from rpclib.protocol.xml.model.fault import fault_to_parent_element
from rpclib.protocol.xml.model.complex import complex_to_parent_element
from rpclib.protocol.xml.model.primitive import xml_to_parent_element
from rpclib.protocol.xml.model.primitive import dict_to_parent_element

from rpclib.protocol.xml.model import base_from_element
from rpclib.protocol.xml.model.binary import binary_from_element
from rpclib.protocol.xml.model.complex import array_from_element
from rpclib.protocol.xml.model.complex import iterable_from_element
from rpclib.protocol.xml.model.complex import complex_from_element
from rpclib.protocol.xml.model.enum import enum_from_element
from rpclib.protocol.xml.model.fault import fault_from_element
from rpclib.protocol.xml.model.primitive import dict_from_element
from rpclib.protocol.xml.model.primitive import xml_from_element

class SchemaValidationError(Fault):
    """Raised when the input stream could not be validated by the Xml Schema."""
    def __init__(self, faultstring):
        Fault.__init__(self, 'Client.SchemaValidationError', faultstring)

class XmlObject(ProtocolBase):
    """The protocol that serializes python objects to xml using schema
    conventions.

    :param app: The owner application instance.
    :param validator: One of (None, 'soft', 'lxml', 'schema',
                ProtocolBase.SOFT_VALIDATION, XmlObject.SCHEMA_VALIDATION).
    """

    SCHEMA_VALIDATION = type("schema", (object,), {})

    def __init__(self, app=None, validator=None, xml_declaration=True):
        ProtocolBase.__init__(self, app, validator)
        self.xml_declaration = xml_declaration

        self.serialization_handlers = cdict({
            ModelBase: base_to_parent_element,
            ByteArray: binary_to_parent_element,
            Attachment: binary_to_parent_element,
            ComplexModelBase: complex_to_parent_element,
            Fault: fault_to_parent_element,
            AnyXml: xml_to_parent_element,
            AnyDict: dict_to_parent_element,
            EnumBase: enum_to_parent_element,
        })

        self.deserialization_handlers = cdict({
            ModelBase: base_from_element,
            ByteArray: binary_from_element,
            Attachment: binary_from_element,
            ComplexModelBase: complex_from_element,
            Fault: fault_from_element,
            AnyXml: xml_from_element,
            AnyDict: dict_from_element,
            EnumBase: enum_from_element,

            Array: array_from_element,
            Iterable: iterable_from_element,
        })

        self.log_messages = (logger.level == logging.DEBUG)

    def set_validator(self, validator):
        if validator in ('lxml', 'schema') or \
                                    validator is self.SCHEMA_VALIDATION:
            self.validate_document = self.__validate_lxml
            self.validator = self.SCHEMA_VALIDATION

        elif validator == 'soft' or validator is self.SOFT_VALIDATION:
            self.validator = self.SOFT_VALIDATION

        elif validator is None:
            pass

        else:
            raise ValueError(validator)

        self.validation_schema = None

    def from_element(self, cls, element):
        handler = self.deserialization_handlers[cls]
        return handler(self, cls, element)

    def to_parent_element(self, cls, value, tns, parent_elt, * args, ** kwargs):
        handler = self.serialization_handlers[cls]
        handler(self, cls, value, tns, parent_elt, * args, ** kwargs)

    def validate_body(self, ctx, message):
        """Sets ctx.method_request_string and calls :func:`generate_contexts`
        for validation."""

        assert message in (self.REQUEST, self.RESPONSE), message

        line_header = LIGHT_RED + "Error:" + END_COLOR
        try:
            self.validate_document(ctx.in_body_doc)
            if message is self.REQUEST:
                line_header = LIGHT_GREEN + "Method request string:" + END_COLOR
            else:
                line_header = LIGHT_RED + "Response:" + END_COLOR
        finally:
            if self.log_messages:
                logger.debug("%s %s" % (line_header, ctx.method_request_string))
                logger.debug(etree.tostring(ctx.in_document, pretty_print=True))

    def create_in_document(self, ctx, charset=None):
        """Uses the iterable of string fragments in ``ctx.in_string`` to set
        ``ctx.in_document``."""

        try:
            ctx.in_document = etree.fromstring(_bytes_join(ctx.in_string))
        except ValueError:
            ctx.in_document = etree.fromstring(_bytes_join([s.decode(charset)
                                                        for s in ctx.in_string]))

    def decompose_incoming_envelope(self, ctx, message):
        assert message in (self.REQUEST, self.RESPONSE)

        ctx.in_header_doc = None # If you need header support, you should use Soap
        ctx.in_body_doc = ctx.in_document
        ctx.method_request_string = ctx.in_body_doc.tag
        self.validate_body(ctx, message)

    def create_out_string(self, ctx, charset=None):
        """Sets an iterable of string fragments to ctx.out_string"""

        if charset is None:
            charset = 'UTF-8'

        ctx.out_string = [etree.tostring(ctx.out_document,
                        xml_declaration=self.xml_declaration, encoding=charset)]

    def deserialize(self, ctx, message):
        """Takes a MethodContext instance and a string containing ONE root xml
        tag.

        Returns the corresponding native python object

        Not meant to be overridden.
        """

        assert message in (self.REQUEST, self.RESPONSE)

        self.event_manager.fire_event('before_deserialize', ctx)

        if message is self.REQUEST:
            body_class = ctx.descriptor.in_message
        elif message is self.RESPONSE:
            body_class = ctx.descriptor.out_message

        # decode method arguments
        if ctx.in_body_doc is not None and len(ctx.in_body_doc) > 0:
            ctx.in_object = self.from_element(body_class, ctx.in_body_doc)
        else:
            ctx.in_object = [None] * len(body_class._type_info)

        if self.log_messages:
            if message is self.REQUEST:
                line_header = '%sRequest%s' % (LIGHT_GREEN, END_COLOR)
            elif message is self.RESPONSE:
                line_header = '%sResponse%s' % (LIGHT_RED, END_COLOR)

            logger.debug("%s %s" % (line_header, etree.tostring(ctx.out_document,
                    xml_declaration=self.xml_declaration, pretty_print=True)))

        self.event_manager.fire_event('after_deserialize', ctx)

    def serialize(self, ctx, message):
        """Uses ctx.out_object, ctx.out_header or ctx.out_error to set
        ctx.out_body_doc, ctx.out_header_doc and ctx.out_document as an
        lxml.etree._Element instance.

        Not meant to be overridden.
        """

        assert message in (self.REQUEST, self.RESPONSE)

        self.event_manager.fire_event('before_serialize', ctx)

        # instantiate the result message
        if message is self.REQUEST:
            result_message_class = ctx.descriptor.in_message
        elif message is self.RESPONSE:
            result_message_class = ctx.descriptor.out_message

        result_message = result_message_class()

        # assign raw result to its wrapper, result_message
        out_type_info = result_message_class._type_info

        for i in range(len(out_type_info)):
            attr_name = result_message_class._type_info.keys()[i]
            setattr(result_message, attr_name, ctx.out_object[i])

        # transform the results into an element
        tmp_elt = etree.Element('{%s}punk' % ns.soap_env)
        self.to_parent_element(result_message_class,
                    result_message, self.app.interface.get_tns(), tmp_elt)
        ctx.out_document = tmp_elt[0]

        self.event_manager.fire_event('after_serialize', ctx)

    def set_app(self, value):
        ProtocolBase.set_app(self, value)

        self.validation_schema = None

        if value:
            from rpclib.interface.wsdl import Wsdl11

            wsdl = Wsdl11(value)
            wsdl.build_validation_schema()

            self.validation_schema = wsdl.validation_schema

    def __validate_lxml(self, payload):
        ret = self.validation_schema.validate(payload)

        logger.debug("Validated ? %s" % str(ret))
        if ret == False:
            raise SchemaValidationError(
                               str(self.validation_schema.error_log.last_error))
