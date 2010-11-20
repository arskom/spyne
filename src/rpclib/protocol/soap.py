
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
from rpclib.mime import collapse_swa

import traceback
from lxml import etree
import rpclib
from rpclib.protocol.base import Base
from rpclib.model.exception import Fault
from rpclib.model.primitive import string_encoding

class ValidationError(Fault):
    pass

def _from_soap(in_envelope_xml, xmlids=None):
    '''
    Parses the xml string into the header and payload
    '''

    if xmlids:
        resolve_hrefs(in_envelope_xml, xmlids)

    if in_envelope_xml.tag != '{%s}Envelope' % rpclib.ns_soap_env:
        raise Fault('Client.SoapError', 'No {%s}Envelope element was found!' %
                                                            rpclib.ns_soap_env)

    header_envelope = in_envelope_xml.xpath('e:Header',
                                          namespaces={'e': rpclib.ns_soap_env})
    body_envelope = in_envelope_xml.xpath('e:Body',
                                          namespaces={'e': rpclib.ns_soap_env})

    if len(header_envelope) == 0 and len(body_envelope) == 0:
        raise Fault('Client.SoapError', 'Soap envelope is empty!' %
                                                            rpclib.ns_soap_env)

    header=None
    if len(header_envelope) > 0 and len(header_envelope[0]) > 0:
        header = header_envelope[0].getchildren()[0]

    body=None
    if len(body_envelope) > 0 and len(body_envelope[0]) > 0:
        body = body_envelope[0].getchildren()[0]

    return header, body

def _parse_xml_string(xml_string, charset=None):
    try:
        if charset is None: # hack
            raise ValueError(charset)

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

class Soap11(Base):
    class NO_WRAPPER:
        pass
    class IN_WRAPPER:
        pass
    class OUT_WRAPPER:
        pass

    allowed_http_verbs = ['POST']

    def __init__(self, parent):
        Base.__init__(self, parent)

        self.in_wrapper = Soap11.IN_WRAPPER
        self.out_wrapper = Soap11.OUT_WRAPPER

    def create_document_structure(self, ctx, in_string, in_string_encoding=None):
        return _parse_xml_string(in_string, in_string_encoding)

    def create_document_string(self, ctx, out_doc):
        return etree.tostring(out_doc, xml_declaration=True,
                                                       encoding=string_encoding)

    def reconstruct_wsgi_request(self, http_env):
        http_payload, charset = Base.reconstruct_wsgi_request(self, http_env)

        content_type = cgi.parse_header(http_env.get("CONTENT_TYPE"))

        return collapse_swa(content_type, http_payload), charset

    def decompose_incoming_envelope(self, ctx, envelope_xml, xmlids=None):
        header, body = _from_soap(envelope_xml, xmlids)

        # FIXME: find a way to include soap env schema with rpclib package and
        # properly validate the whole request.

        if len(body) > 0 and body.tag == '{%s}Fault' % rpclib.ns_soap_env:
            ctx.in_body_doc = body

        elif not (body is None):
            try:
                self.parent.interface.validate(body)
                if (not (body is None)) and (ctx.method_name is None):
                    ctx.method_name = body.tag
                    logger.debug("\033[92mMethod name: %r\033[0m" %
                                                                ctx.method_name)

            finally:
                # for performance reasons, we don't want the following to run
                # in production even though we won't see the results.
                if logger.level == logging.DEBUG:
                    try:
                        logger.debug(etree.tostring(envelope_xml,
                                                             pretty_print=True))
                    except etree.XMLSyntaxError, e:
                        logger.debug(body)
                        raise Fault('Client.Xml', 'Error at line: %d, '
                                    'col: %d' % e.position)
            try:
                if ctx.service_class is None: # i.e. if it's a server
                    ctx.service_class = self.parent.get_service_class(ctx.method_name)

            except Exception,e:
                logger.debug(traceback.format_exc())
                raise ValidationError('Client', 'Method not found: %r' %
                                                                ctx.method_name)

            ctx.service = self.parent.get_service(ctx.service_class)

            ctx.in_header_doc = header
            ctx.in_body_doc = body

    def deserialize(self, ctx, doc_struct):
        """Takes a MethodContext instance and a string containing ONE soap
        message.
        Returns the corresponding native python object

        Not meant to be overridden.
        """

        envelope_xml, xmlids = doc_struct

        # this sets the ctx.in_body_doc and ctx.in_header_doc properties
        self.decompose_incoming_envelope(ctx, envelope_xml, xmlids)

        if ctx.in_body_doc.tag == "{%s}Fault" % rpclib.ns_soap_env:
            in_body = Fault.from_xml(ctx.in_body_doc)

        else:
            # retrieve the method descriptor
            if ctx.method_name is None:
                raise Exception("Could not extract method name from the request!")
            else:
                if ctx.descriptor is None:
                    descriptor = ctx.descriptor = ctx.service.get_method(
                                                                ctx.method_name)
                else:
                    descriptor = ctx.descriptor

            if self.in_wrapper is self.IN_WRAPPER:
                header_class = descriptor.in_header
                body_class = descriptor.in_message

            elif self.in_wrapper is self.OUT_WRAPPER:
                header_class = descriptor.out_header
                body_class = descriptor.out_message

            # decode header object
            if ctx.in_header_doc is not None and len(ctx.in_header_doc) > 0:
                ctx.service.in_header = header_class.from_xml(ctx.in_header_doc)

            # decode method arguments
            if ctx.in_body_doc is not None and len(ctx.in_body_doc) > 0:
                in_body = body_class.from_xml(ctx.in_body_doc)
            else:
                in_body = [None] * len(body_class._type_info)

        return in_body

    def serialize(self, ctx, out_object):
        """Takes a MethodContext instance and the object to be serialized.
        Returns the corresponding xml structure as an lxml.etree._Element
        instance.

        Not meant to be overridden.
        """

        # construct the soap response, and serialize it
        nsmap = self.parent.interface.nsmap
        envelope = etree.Element('{%s}Envelope'% rpclib.ns_soap_env,nsmap=nsmap)

        if isinstance(out_object, Fault):
            # FIXME: There's no way to alter soap response headers for the user.
            ctx.out_body_doc = out_body_doc = etree.SubElement(envelope,
                            '{%s}Body' % rpclib.ns_soap_env, nsmap=nsmap)
            out_object.__class__.to_parent_element(out_object,self.parent.interface.get_tns(), out_body_doc)

            # implementation hook
            if not (ctx.service is None):
                ctx.service.on_method_exception_doc(out_body_doc)
            self.parent.on_exception_doc(out_body_doc)

            if logger.level == logging.DEBUG:
                logger.debug(etree.tostring(envelope, pretty_print=True))

        elif isinstance(out_object, Exception):
            raise Exception("Can't serialize native python exceptions")

        else:
            # header
            if ctx.service.out_header != None:
                if self.out_wrapper in (self.NO_WRAPPER, self.OUT_WRAPPER):
                    header_message_class = ctx.descriptor.in_header
                else:
                    header_message_class = ctx.descriptor.out_header

                if ctx.descriptor.out_header is None:
                    logger.warning(
                        "Skipping soap response header as %r method is not "
                        "published to have one." %
                                out_object.get_type_name()[:-len('Response')])

                else:
                    ctx.out_header_doc = soap_header_elt = etree.SubElement(
                                   envelope, '{%s}Header' % rpclib.ns_soap_env)

                    header_message_class.to_parent_element(
                        ctx.service.out_header,
                        self.parent.interface.get_tns(),
                        soap_header_elt,
                        header_message_class.get_type_name()
                    )

            # body
            ctx.out_body_doc = out_body_doc = etree.SubElement(envelope,
                                               '{%s}Body' % rpclib.ns_soap_env)

            # instantiate the result message
            if self.out_wrapper is self.NO_WRAPPER:
                result_message_class = ctx.descriptor.in_message
                result_message = out_object

            else:
                if self.out_wrapper is self.IN_WRAPPER:
                    result_message_class = ctx.descriptor.in_message
                elif self.out_wrapper is self.OUT_WRAPPER:
                    result_message_class = ctx.descriptor.out_message

                result_message = result_message_class()

                # assign raw result to its wrapper, result_message
                out_type_info = result_message_class._type_info

                if len(out_type_info) > 0:
                     if len(out_type_info) == 1:
                         attr_name = result_message_class._type_info.keys()[0]
                         setattr(result_message, attr_name, out_object)

                     else:
                         for i in range(len(out_type_info)):
                             attr_name=result_message_class._type_info.keys()[i]
                             setattr(result_message, attr_name, out_object[i])

            # transform the results into an element
            result_message_class.to_parent_element(
                  result_message, self.parent.interface.get_tns(), out_body_doc)

            if logger.level == logging.DEBUG:
                logger.debug('\033[91m'+ "Response" + '\033[0m')
                logger.debug(etree.tostring(envelope, xml_declaration=True,
                                                             pretty_print=True))

            #implementation hook
            if not (ctx.service is None):
                ctx.service.on_method_return_doc(envelope)

        return envelope
