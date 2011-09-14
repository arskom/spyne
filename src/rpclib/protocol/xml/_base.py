
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

from lxml import etree

from rpclib.const import xml_ns as ns

from rpclib.util.cdict import cdict

from rpclib.error import NotFoundError
from rpclib.model import ModelBase

from rpclib.model.binary import Attachment
from rpclib.model.complex import Array
from rpclib.model.complex import Iterable
from rpclib.model.complex import ComplexModelBase
from rpclib.model.enum import EnumBase
from rpclib.model.fault import Fault
from rpclib.model.primitive import AnyXml
from rpclib.model.primitive import AnyDict
from rpclib.model.primitive import String
from rpclib.model.primitive import Duration

from rpclib.protocol import ProtocolBase

from rpclib.protocol.xml.model import base_to_parent_element
from rpclib.protocol.xml.model.binary import binary_to_parent_element
from rpclib.protocol.xml.model.enum import enum_to_parent_element
from rpclib.protocol.xml.model.fault import fault_to_parent_element
from rpclib.protocol.xml.model.complex import complex_to_parent_element
from rpclib.protocol.xml.model.primitive import xml_to_parent_element
from rpclib.protocol.xml.model.primitive import dict_to_parent_element
from rpclib.protocol.xml.model.primitive import string_to_parent_element
from rpclib.protocol.xml.model.primitive import duration_to_parent_element

from rpclib.protocol.xml.model import base_from_element
from rpclib.protocol.xml.model.binary import binary_from_element
from rpclib.protocol.xml.model.complex import array_from_element
from rpclib.protocol.xml.model.complex import iterable_from_element
from rpclib.protocol.xml.model.complex import complex_from_element
from rpclib.protocol.xml.model.enum import enum_from_element
from rpclib.protocol.xml.model.fault import fault_from_element
from rpclib.protocol.xml.model.primitive import dict_from_element
from rpclib.protocol.xml.model.primitive import xml_from_element
from rpclib.protocol.xml.model.primitive import string_from_element

class XmlObject(ProtocolBase):
    def __init__(self, app=None):
        ProtocolBase.__init__(self, app)

        self.serialization_handlers = cdict({
            ModelBase: base_to_parent_element,
            Attachment: binary_to_parent_element,
            ComplexModelBase: complex_to_parent_element,
            Fault: fault_to_parent_element,
            String: string_to_parent_element,
            AnyXml: xml_to_parent_element,
            AnyDict: dict_to_parent_element,
            EnumBase: enum_to_parent_element,
            Duration: duration_to_parent_element,
        })

        self.deserialization_handlers = cdict({
            ModelBase: base_from_element,
            Attachment: binary_from_element,
            ComplexModelBase: complex_from_element,
            Fault: fault_from_element,
            String: string_from_element,
            AnyXml: xml_from_element,
            AnyDict: dict_from_element,
            Array: array_from_element,
            Iterable: iterable_from_element,
            EnumBase: enum_from_element,
        })

    def from_element(self, cls, element):
        handler = self.deserialization_handlers[cls]
        return handler(self, cls, element)

    def to_parent_element(self, cls, value, tns, parent_elt, * args, ** kwargs):
        handler = self.serialization_handlers[cls]
        handler(self, cls, value, tns, parent_elt, * args, ** kwargs)

    def create_in_document(self, ctx, charset=None):
        ctx.in_document = etree.fromstring(ctx.in_string, charset)

        body_doc = ctx.in_document

        try:
            self.validate(body_doc)
            if (not (body_doc is None) and
                (ctx.method_request_string is None)):
                ctx.method_request_string = body_doc.tag
                logger.debug("\033[92mMethod request_string: %r\033[0m" %
                                                    ctx.method_request_string)

        finally:
            # for performance reasons, we don't want the following to run
            # in production even though we won't see the results.
            # that's why one needs to explicitly set the logging level of
            # the 'rpclib.protocol.xml._base' to DEBUG to see the xml data.
            if logger.level == logging.DEBUG:
                try:
                    logger.debug(etree.tostring(body_doc, pretty_print=True))
                except etree.XMLSyntaxError, e:
                    logger.debug(body_doc)
                    raise Fault('Client.Xml', 'Error at line: %d, col: %d' %
                                                                    e.position)

        if ctx.method_request_string is None:
            raise Exception("Could not extract method request string from "
                            "the request!")
        try:
            if ctx.service_class is None: # i.e. if it's a server
                self.set_method_descriptor(ctx)

        except Exception, e:
            logger.exception(e)
            raise NotFoundError('Client', 'Method not found: %r' %
                                                    ctx.method_request_string)

        ctx.in_header_doc = None # XmlObject does not know between header and
            # payload. That's SOAP's job to do.
        ctx.in_body_doc = body_doc

    def create_out_string(self, ctx, charset=None):
        """Sets an iterable of string fragments to ctx.out_string"""
        if charset is None:
            charset = 'utf8'

        ctx.out_string = [etree.tostring(ctx.out_document, xml_declaration=True,
                                                            encoding=charset)]

    def deserialize(self, ctx, way='out'):
        """Takes a MethodContext instance and a string containing ONE root xml
        tag.

        Returns the corresponding native python object

        Not meant to be overridden.
        """

        assert way in ('in', 'out')

        if way == 'in':
            body_class = ctx.descriptor.in_message

        elif self.in_wrapper is self.OUT_WRAPPER:
            body_class = ctx.descriptor.out_message

        # decode method arguments
        if ctx.in_body_doc is not None and len(ctx.in_body_doc) > 0:
            ctx.in_object = self.from_element(body_class, ctx.in_body_doc)
        else:
            ctx.in_object = [None] * len(body_class._type_info)

        self.event_manager.fire_event('deserialize', ctx)

    def serialize(self, ctx, way='out'):
        """Uses ctx.out_object, ctx.out_header or ctx.out_error to set
        ctx.out_body_doc, ctx.out_header_doc and ctx.out_document as an
        lxml.etree._Element instance.

        Not meant to be overridden.
        """

        assert way in ('in', 'out')

        # instantiate the result message
        if way == 'in':
            result_message_class = ctx.descriptor.in_message
        else:
            result_message_class = ctx.descriptor.out_message

        result_message = result_message_class()

        # assign raw result to its wrapper, result_message
        out_type_info = result_message_class._type_info

        if len(out_type_info) == 1:
            attr_name = result_message_class._type_info.keys()[0]
            setattr(result_message, attr_name, ctx.out_object)

        else:
            for i in range(len(out_type_info)):
                attr_name = result_message_class._type_info.keys()[i]
                setattr(result_message, attr_name, ctx.out_object[i])

        # transform the results into an element
        tmp_elt = etree.Element('{%s}punk' % ns.soap_env)
        self.to_parent_element(result_message_class,
                    result_message, self.app.interface.get_tns(), tmp_elt)
        ctx.out_document = tmp_elt[0]

        if logger.level == logging.DEBUG:
            logger.debug('\033[91m' + "Response" + '\033[0m')
            logger.debug(etree.tostring(ctx.out_document,
                         xml_declaration=True, pretty_print=True))

        self.event_manager.fire_event('serialize', ctx)
