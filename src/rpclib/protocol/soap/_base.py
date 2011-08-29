
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

import cgi
import traceback

import rpclib.const.xml_ns as ns

from lxml import etree

from rpclib.protocol.xml import XmlObject
from rpclib.protocol.soap.mime import collapse_swa

from rpclib.protocol import ProtocolBase
from rpclib.model.fault import Fault
from rpclib.model.primitive import string_encoding

class ValidationError(Fault):
    pass

def _from_soap(in_envelope_xml, xmlids=None):
    '''
    Parses the xml string into the header and payload
    '''

    if xmlids:
        resolve_hrefs(in_envelope_xml, xmlids)

    if in_envelope_xml.tag != '{%s}Envelope' % ns.soap_env:
        raise Fault('Client.SoapError', 'No {%s}Envelope element was found!' %
                                                            ns.soap_env)

    header_envelope = in_envelope_xml.xpath('e:Header',
                                          namespaces={'e': ns.soap_env})
    body_envelope = in_envelope_xml.xpath('e:Body',
                                          namespaces={'e': ns.soap_env})

    if len(header_envelope) == 0 and len(body_envelope) == 0:
        raise Fault('Client.SoapError', 'Soap envelope is empty!' %
                                                            ns.soap_env)

    header=None
    if len(header_envelope) > 0 and len(header_envelope[0]) > 0:
        header = header_envelope[0].getchildren()

    body=None
    if len(body_envelope) > 0 and len(body_envelope[0]) > 0:
        body = body_envelope[0].getchildren()[0]

    return header, body

def _parse_xml_string(xml_string, charset=None):
    try:
        if charset is None:
            charset = string_encoding

        root, xmlids = etree.XMLID(xml_string.decode(charset))

    except ValueError,e:
        logger.debug('%s -- falling back to str decoding.' % (e))
        root, xmlids = etree.XMLID(xml_string)

    return root, xmlids

# see http://www.w3.org/TR/2000/NOTE-SOAP-20000508/
# section 5.2.1 for an example of how the id and href attributes are used.
def resolve_hrefs(element, xmlids):
    for e in element:
        if e.get('id'):
            continue # don't need to resolve this element

        elif e.get('href'):
            resolved_element = xmlids[e.get('href').replace('#', '')]
            if resolved_element is None:
                continue
            resolve_hrefs(resolved_element, xmlids)

            # copies the attributes
            [e.set(k, v) for k, v in resolved_element.items()]

            # copies the children
            [e.append(child) for child in resolved_element.getchildren()]

            # copies the text
            e.text = resolved_element.text

        else:
            resolve_hrefs(e, xmlids)

    return element

class Soap11(XmlObject):
    class NO_WRAPPER:
        pass
    class IN_WRAPPER:
        pass
    class OUT_WRAPPER:
        pass

    allowed_http_verbs = ['POST']
    mime_type = 'application/soap+xml'

    def __init__(self, parent):
        ProtocolBase.__init__(self, parent)

        self.in_wrapper = Soap11.IN_WRAPPER
        self.out_wrapper = Soap11.OUT_WRAPPER

    def create_in_document(self, ctx, charset=None):
        if ctx.transport.type == 'wsgi':
            content_type = cgi.parse_header(ctx.transport.req_env.get("CONTENT_TYPE"))

            collapse_swa(content_type, ctx.in_string)

        ctx.in_document = _parse_xml_string(ctx.in_string, charset)

    def create_out_string(self, ctx, charset=None):
        """Sets an iterable of string fragments to ctx.out_string"""
        if charset is None:
            charset = string_encoding

        ctx.out_string = [etree.tostring(ctx.out_document, xml_declaration=True,
                                                              encoding=charset)]

    def decompose_incoming_envelope(self, ctx):
        envelope_xml, xmlids = ctx.in_document
        header_doc, body_doc = _from_soap(envelope_xml, xmlids)

        if len(body_doc) > 0 and body_doc.tag == '{%s}Fault' % ns.soap_env:
            ctx.in_body_doc = body_doc

        elif not (body_doc is None):
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
                # the 'rpclib.protocol.soap._base' to DEBUG to see the xml data.
                if logger.level == logging.DEBUG:
                    try:
                        logger.debug(etree.tostring(envelope_xml,
                                                             pretty_print=True))
                    except etree.XMLSyntaxError, e:
                        logger.debug(body_doc)
                        raise Fault('Client.Xml', 'Error at line: %d, '
                                    'col: %d' % e.position)

            if ctx.method_request_string is None:
                raise Exception("Could not extract method request string from "
                                "the request!")
            try:
                if ctx.service_class is None: # i.e. if it's a server
                    self.set_method_descriptor(ctx)

            except Exception,e:
                logger.debug(traceback.format_exc())
                raise ValidationError('Client', 'Method not found: %r' %
                                                    ctx.method_request_string)

            ctx.in_header_doc = header_doc
            ctx.in_body_doc = body_doc

    def deserialize(self, ctx):
        """Takes a MethodContext instance and a string containing ONE soap
        message.
        Returns the corresponding native python object

        Not meant to be overridden.
        """

        if ctx.in_body_doc.tag == "{%s}Fault" % ns.soap_env:
            ctx.in_object = None
            ctx.in_error = self.from_element(Fault, ctx.in_body_doc)

        else:
            if self.in_wrapper is self.IN_WRAPPER:
                header_class = ctx.descriptor.in_header
                body_class = ctx.descriptor.in_message

            elif self.in_wrapper is self.OUT_WRAPPER:
                header_class = ctx.descriptor.out_header
                body_class = ctx.descriptor.out_message

            # decode header objects
            if (ctx.in_header_doc is not None and header_class is not None):
                if isinstance(header_class, (list, tuple)):
                    headers = [None] * len(header_class)
                    for i, (header_doc, head_class) in enumerate(
                                          zip(ctx.in_header_doc, header_class)):
                        if len(header_doc) > 0:
                            headers[i] = self.from_element(head_class, header_doc)
                    ctx.in_header = tuple(headers)

                else:
                    header_doc = ctx.in_header_doc[0]
                    if len(header_doc) > 0:
                        ctx.in_header = self.from_element(header_class, header_doc)

            # decode method arguments
            if ctx.in_body_doc is not None and len(ctx.in_body_doc) > 0:
                ctx.in_object = self.from_element(body_class, ctx.in_body_doc)
            else:
                ctx.in_object = [None] * len(body_class._type_info)

        self.event_manager.fire_event('deserialize', ctx)

    def serialize(self, ctx):
        """Uses ctx.out_object, ctx.out_header or ctx.out_error to set
        ctx.out_body_doc, ctx.out_header_doc and ctx.out_document as an
        lxml.etree._Element instance.

        Not meant to be overridden.
        """

        # construct the soap response, and serialize it
        nsmap = self.app.interface.nsmap
        ctx.out_document = etree.Element('{%s}Envelope' % ns.soap_env,
                                                                    nsmap=nsmap)

        if not (ctx.out_error is None):
            # FIXME: There's no way to alter soap response headers for the user.
            ctx.out_body_doc = out_body_doc = etree.SubElement(ctx.out_document,
                            '{%s}Body' % ns.soap_env, nsmap=nsmap)
            self.to_parent_element(ctx.out_error.__class__, ctx.out_error,
                                    self.app.interface.get_tns(), out_body_doc)

            if logger.level == logging.DEBUG:
                logger.debug(etree.tostring(ctx.out_document, pretty_print=True))

        else:
            # header
            if ctx.out_header is not None:
                if self.out_wrapper is self.OUT_WRAPPER:
                    header_message_class = ctx.descriptor.out_header
                else:
                    header_message_class = ctx.descriptor.in_header

                if ctx.descriptor.out_header is None:
                    logger.warning(
                        "Skipping soap response header as %r method is not "
                        "declared to have one." % ctx.method_name)

                else:
                    ctx.out_header_doc = soap_header_elt = etree.SubElement(
                                    ctx.out_document, '{%s}Header' % ns.soap_env)

                    if isinstance(header_message_class, (list, tuple)):
                        if isinstance(ctx.out_header, (list, tuple)):
                            out_headers = ctx.out_header
                        else:
                            out_headers = (ctx.out_header,)

                        for header_class, out_header in zip(header_message_class,
                                                                out_headers):
                            self.to_parent_element(header_class,
                                out_header,
                                self.app.interface.get_tns(),
                                soap_header_elt,
                                header_class.get_type_name(),
                            )
                    else:
                        self.to_parent_element(header_message_class,
                            ctx.out_header,
                            self.app.interface.get_tns(),
                            soap_header_elt,
                            header_message_class.get_type_name()
                        )

            # body
            ctx.out_body_doc = out_body_doc = etree.SubElement(ctx.out_document,
                                               '{%s}Body' % ns.soap_env)

            # instantiate the result message
            if self.out_wrapper is self.NO_WRAPPER:
                result_message_class = ctx.descriptor.in_message
                result_message = ctx.out_object

            else:
                if self.out_wrapper is self.IN_WRAPPER:
                    result_message_class = ctx.descriptor.in_message
                elif self.out_wrapper is self.OUT_WRAPPER:
                    result_message_class = ctx.descriptor.out_message

                result_message = result_message_class()

                # assign raw result to its wrapper, result_message
                out_type_info = result_message_class._type_info

                if len(out_type_info) == 1:
                    attr_name = result_message_class._type_info.keys()[0]
                    setattr(result_message, attr_name, ctx.out_object)

                else:
                    for i in range(len(out_type_info)):
                        attr_name=result_message_class._type_info.keys()[i]
                        setattr(result_message, attr_name, ctx.out_object[i])

            # transform the results into an element
            self.to_parent_element(result_message_class,
                  result_message, self.app.interface.get_tns(), out_body_doc)

            if logger.level == logging.DEBUG:
                logger.debug('\033[91m'+ "Response" + '\033[0m')
                logger.debug(etree.tostring(ctx.out_document,
                                       xml_declaration=True, pretty_print=True))

        self.event_manager.fire_event('serialize',ctx)

class Soap11Strict(Soap11):
    def __init__(self, parent):
        Soap11.__init__(self, parent)

        parent.interface.build_validation_schema()

    def validate(self, payload):
        schema = self.app.interface.validation_schema
        ret = schema.validate(payload)

        logger.debug("Validated ? %s" % str(ret))
        if ret == False:
            raise ValidationError('Client.SchemaValidation',
                                               str(schema.error_log.last_error))
