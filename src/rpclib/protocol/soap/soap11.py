
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

"""This module contains the implementation of a subset of the SOAP 1.1 remote
procedure call standard.
"""

import logging
logger = logging.getLogger(__name__)

import cgi

import rpclib.const.xml_ns as ns

from lxml import etree
from lxml.etree import XMLSyntaxError

from rpclib.const.http import HTTP_405
from rpclib.const.http import HTTP_500
from rpclib.const.ansi_color import LIGHT_GREEN
from rpclib.const.ansi_color import LIGHT_RED
from rpclib.const.ansi_color import END_COLOR
from rpclib.error import RequestNotAllowed
from rpclib.model.fault import Fault
from rpclib.protocol.xml import XmlObject
from rpclib.protocol.soap.mime import collapse_swa

def _from_soap(in_envelope_xml, xmlids=None):
    '''Parses the xml string into the header and payload.'''

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
    if charset:
        string = ''.join([s.decode(charset) for s in xml_string])
    else:
        string = ''.join(xml_string)

    try:
        try:
            root, xmlids = etree.XMLID(string)

        except XMLSyntaxError, e:
            logger.error(string)
            raise Fault('Client.XMLSyntaxError', str(e))

    except ValueError, e:
        logger.debug('%r -- falling back to str decoding.' % (e))
        try:
            root, xmlids = etree.XMLID(string.encode(charset))
        except XMLSyntaxError, e:
            logger.error(string)
            raise Fault('Client.XMLSyntaxError', str(e))

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
    '''The base implementation of the Soap 1.1 protocol.'''

    allowed_http_verbs = ['POST']
    mime_type = 'text/xml; charset=utf-8'

    def __init__(self, app=None, validator=None, wrapped=True, xml_declaration=True):
        """Soap 1.1 Protocol with validators.

        :param app: A rpclib.application.Application instance.
        :param validator: The validator to use. Currently the only supported
            value is 'lxml'
        :param wrapped: Whether the return type should be wrapped in another
            object. Default is 'True'.
        """
        XmlObject.__init__(self, app, validator, xml_declaration)

        self.__wrapped = wrapped

    @property
    def wrapped(self):
        return self.__wrapped

    def create_in_document(self, ctx, charset=None):
        if ctx.transport.type == 'wsgi':
            # according to the soap via http standard, soap requests must only
            # work with proper POST requests.
            content_type = ctx.transport.req_env.get("CONTENT_TYPE")
            http_verb = ctx.transport.req_env['REQUEST_METHOD'].upper()
            if content_type is None or http_verb != "POST":
                ctx.transport.resp_code = HTTP_405
                raise RequestNotAllowed(
                        "You must issue a POST request with the Content-Type "
                        "header properly set.")

            content_type = cgi.parse_header(content_type)
            collapse_swa(content_type, ctx.in_string)

        ctx.in_document = _parse_xml_string(ctx.in_string, charset)

    def decompose_incoming_envelope(self, ctx, message=XmlObject.REQUEST):
        envelope_xml, xmlids = ctx.in_document
        header_document, body_document = _from_soap(envelope_xml, xmlids)

        ctx.in_document = envelope_xml

        if body_document.tag == '{%s}Fault' % ns.soap_env:
            ctx.in_body_doc = body_document

        else:
            ctx.in_header_doc = header_document
            ctx.in_body_doc = body_document
            ctx.method_request_string = ctx.in_body_doc.tag
            self.validate_body(ctx, message)

    def deserialize(self, ctx, message):
        """Takes a MethodContext instance and a string containing ONE soap
        message.
        Returns the corresponding native python object

        Not meant to be overridden.
        """

        assert message in (self.REQUEST, self.RESPONSE)

        self.event_manager.fire_event('before_deserialize', ctx)

        if ctx.in_body_doc.tag == "{%s}Fault" % ns.soap_env:
            ctx.in_object = None
            ctx.in_error = self.from_element(Fault, ctx.in_body_doc)

        else:
            if message is self.REQUEST:
                header_class = ctx.descriptor.in_header
                body_class = ctx.descriptor.in_message

            elif message is self.RESPONSE:
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

        self.event_manager.fire_event('after_deserialize', ctx)

    def serialize(self, ctx, message):
        """Uses ctx.out_object, ctx.out_header or ctx.out_error to set
        ctx.out_body_doc, ctx.out_header_doc and ctx.out_document as an
        lxml.etree._Element instance.

        Not meant to be overridden.
        """

        assert message in (self.REQUEST, self.RESPONSE)

        self.event_manager.fire_event('before_serialize', ctx)

        # construct the soap response, and serialize it
        nsmap = self.app.interface.nsmap
        ctx.out_document = etree.Element('{%s}Envelope' % ns.soap_env,
                                                                    nsmap=nsmap)
        if ctx.out_error is not None:
            # FIXME: There's no way to alter soap response headers for the user.
            ctx.out_body_doc = out_body_doc = etree.SubElement(ctx.out_document,
                            '{%s}Body' % ns.soap_env, nsmap=nsmap)
            self.to_parent_element(ctx.out_error.__class__, ctx.out_error,
                                    self.app.interface.get_tns(), out_body_doc)

        else:
            if message is self.REQUEST:
                header_message_class = ctx.descriptor.in_header
                body_message_class = ctx.descriptor.in_message

            elif message is self.RESPONSE:
                header_message_class = ctx.descriptor.out_header
                body_message_class = ctx.descriptor.out_message

            # header
            if ctx.out_header is not None:
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

            # assign raw result to its wrapper, result_message
            out_type_info = body_message_class._type_info
            out_object = body_message_class()

            keys = iter(out_type_info)
            values = iter(ctx.out_object)
            while True:
                try:
                    k = keys.next()
                except StopIteration:
                    break
                try:
                    v = values.next()
                except StopIteration:
                    v = None

                setattr(out_object, k, v)

            # transform the results into an element
            self.to_parent_element(body_message_class, out_object,
                                    self.app.interface.get_tns(), out_body_doc)

        if self.log_messages:
            if message is self.REQUEST:
                line_header = '%sRequest%s' % (LIGHT_GREEN, END_COLOR)
            elif message is self.RESPONSE:
                line_header = '%sResponse%s' % (LIGHT_RED, END_COLOR)
            logger.debug('%s %s' % (line_header, etree.tostring(ctx.out_document,
                                        xml_declaration=True, pretty_print=True)))
        self.event_manager.fire_event('after_serialize', ctx)

    def fault_to_http_response_code(self, fault):
        return HTTP_500
