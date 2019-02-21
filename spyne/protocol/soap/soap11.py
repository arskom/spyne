
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

"""The ``spyne.protocol.soap.soap11`` module contains the implementation of a
subset of the Soap 1.1 standard.

Except the binary optimizations (MtoM, attachments, etc) that are beta quality,
this protocol is production quality.

One must specifically enable the debug output for the Xml protocol to see the
actual document exchange. That's because the xml formatting code is run only
when explicitly enabled due to performance reasons. ::

    logging.getLogger('spyne.protocol.xml').setLevel(logging.DEBUG)

Initially released in soaplib-0.8.0.

Logs valid documents to %r and invalid documents to %r.
""" % (__name__, __name__ + ".invalid")

import logging
logger = logging.getLogger(__name__)
logger_invalid = logging.getLogger(__name__ + ".invalid")

import cgi

from itertools import chain

import spyne.const.xml as ns

from lxml import etree
from lxml.etree import XMLSyntaxError
from lxml.etree import XMLParser

from spyne import BODY_STYLE_WRAPPED
from spyne.util import six
from spyne.const.xml import DEFAULT_NS
from spyne.const.http import HTTP_405, HTTP_500
from spyne.error import RequestNotAllowed
from spyne.model.fault import Fault
from spyne.model.primitive import Date, Time, DateTime
from spyne.protocol.xml import XmlDocument
from spyne.protocol.soap.mime import collapse_swa
from spyne.server.http import HttpTransportContext


def _from_soap(in_envelope_xml, xmlids=None, **kwargs):
    """Parses the xml string into the header and payload.
    """
    ns_soap = kwargs.pop('ns', ns.NS_SOAP11_ENV)

    if xmlids:
        resolve_hrefs(in_envelope_xml, xmlids)

    if in_envelope_xml.tag != '{%s}Envelope' % ns_soap:
        raise Fault('Client.SoapError', 'No {%s}Envelope element was found!' %
                                                                        ns_soap)

    header_envelope = in_envelope_xml.xpath('e:Header',
                                          namespaces={'e': ns_soap})
    body_envelope = in_envelope_xml.xpath('e:Body',
                                          namespaces={'e': ns_soap})

    if len(header_envelope) == 0 and len(body_envelope) == 0:
        raise Fault('Client.SoapError', 'Soap envelope is empty!')

    header = None
    if len(header_envelope) > 0:
        header = header_envelope[0].getchildren()

    body = None
    if len(body_envelope) > 0 and len(body_envelope[0]) > 0:
        body = body_envelope[0][0]

    return header, body


def _parse_xml_string(xml_string, parser, charset=None):
    xml_string = iter(xml_string)
    chunk = next(xml_string)
    if isinstance(chunk, six.binary_type):
        string = b''.join(chain( (chunk,), xml_string ))
    else:
        string = ''.join(chain( (chunk,), xml_string ))

    if charset:
        string = string.decode(charset)

    try:
        try:
            root, xmlids = etree.XMLID(string, parser)

        except ValueError as e:
            logger.debug('ValueError: Deserializing from unicode strings with '
                         'encoding declaration is not supported by lxml.')
            root, xmlids = etree.XMLID(string.encode(charset), parser)

    except XMLSyntaxError as e:
        logger_invalid.error("%r in string %r", e, string)
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


class Soap11(XmlDocument):
    """The base implementation of a subset of the Soap 1.1 standard. The
    document is available here: http://www.w3.org/TR/soap11/

    :param app: The owner application instance.
    :param validator: One of (None, 'soft', 'lxml', 'schema',
                ProtocolBase.SOFT_VALIDATION, XmlDocument.SCHEMA_VALIDATION).
                Both ``'lxml'`` and ``'schema'`` values are equivalent to
                ``XmlDocument.SCHEMA_VALIDATION``.
    :param xml_declaration: Whether to add xml_declaration to the responses
        Default is 'True'.
    :param cleanup_namespaces: Whether to add clean up namespace declarations
        in the response document. Default is 'True'.
    :param encoding: The suggested string encoding for the returned xml
        documents. The transport can override this.
    :param pretty_print: When ``True``, returns the document in a pretty-printed
        format.
    """

    mime_type = 'text/xml; charset=utf-8'

    type = set(XmlDocument.type)
    type.update(('soap', 'soap11'))

    ns_soap_env = ns.NS_SOAP11_ENV
    ns_soap_enc = ns.NS_SOAP11_ENC

    def __init__(self, *args, **kwargs):
        super(Soap11, self).__init__(*args, **kwargs)

        # SOAP requires DateTime strings to be in iso format. The following
        # lines make sure custom datetime formatting via
        # DateTime(dt_format="...") (or similar) is bypassed.
        self._to_unicode_handlers[Time] = lambda cls, value: value.isoformat()
        self._to_unicode_handlers[DateTime] = lambda cls, value: value.isoformat()

        self._from_unicode_handlers[Date] = self.date_from_unicode_iso
        self._from_unicode_handlers[DateTime] = self.datetime_from_unicode_iso

    def create_in_document(self, ctx, charset=None):
        if isinstance(ctx.transport, HttpTransportContext):
            # according to the soap-via-http standard, soap requests must only
            # work with proper POST requests.
            content_type = ctx.transport.get_request_content_type()
            http_verb = ctx.transport.get_request_method()
            if content_type is None or http_verb != "POST":
                ctx.transport.resp_code = HTTP_405
                raise RequestNotAllowed(
                        "You must issue a POST request with the Content-Type "
                        "header properly set.")

            content_type = cgi.parse_header(content_type)
            ctx.in_string = collapse_swa(ctx, content_type, self.ns_soap_env)

        ctx.in_document = _parse_xml_string(ctx.in_string,
                                            XMLParser(**self.parser_kwargs),
                                                                        charset)

    def decompose_incoming_envelope(self, ctx, message=XmlDocument.REQUEST):
        envelope_xml, xmlids = ctx.in_document
        header_document, body_document = _from_soap(envelope_xml, xmlids,
                                                            ns=self.ns_soap_env)

        ctx.in_document = envelope_xml

        if body_document.tag == '{%s}Fault' % self.ns_soap_env:
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

        if ctx.in_body_doc.tag == "{%s}Fault" % self.ns_soap_env:
            ctx.in_object = None
            ctx.in_error = self.from_element(ctx, Fault, ctx.in_body_doc)

        else:
            if message is self.REQUEST:
                header_class = ctx.descriptor.in_header
                body_class = ctx.descriptor.in_message

            elif message is self.RESPONSE:
                header_class = ctx.descriptor.out_header
                body_class = ctx.descriptor.out_message

            # decode header objects
            #  header elements are returned in header_class order which need not match the incoming XML
            if (ctx.in_header_doc is not None and header_class is not None):
                headers = [None] * len(header_class)
                in_header_dict = dict( [(element.tag, element)
                                              for element in ctx.in_header_doc])
                for i, head_class in enumerate(header_class):
                    if i < len(header_class):
                        nsval = "{%s}%s" % (head_class.__namespace__,
                                                       head_class.__type_name__)
                        header_doc = in_header_dict.get(nsval, None)
                        if header_doc is not None:
                            headers[i] = self.from_element(ctx, head_class,
                                                                     header_doc)

                if len(headers) == 1:
                    ctx.in_header = headers[0]
                else:
                    ctx.in_header = headers

            # decode method arguments
            if ctx.in_body_doc is None:
                ctx.in_object = [None] * len(body_class._type_info)
            else:
                ctx.in_object = self.from_element(ctx, body_class,
                                                                ctx.in_body_doc)

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
        ctx.out_document = etree.Element('{%s}Envelope' % self.ns_soap_env,
                                                                    nsmap=nsmap)
        if ctx.out_error is not None:
            # FIXME: There's no way to alter soap response headers for the user.
            ctx.out_body_doc = out_body_doc = etree.SubElement(ctx.out_document,
                            '{%s}Body' % self.ns_soap_env, nsmap=nsmap)
            self.to_parent(ctx, ctx.out_error.__class__, ctx.out_error,
                                    out_body_doc, self.app.interface.get_tns())

        else:
            if message is self.REQUEST:
                header_message_class = ctx.descriptor.in_header
                body_message_class = ctx.descriptor.in_message

            elif message is self.RESPONSE:
                header_message_class = ctx.descriptor.out_header
                body_message_class = ctx.descriptor.out_message

            # body
            ctx.out_body_doc = out_body_doc = etree.Element(
                                                    '{%s}Body' % self.ns_soap_env)

            # assign raw result to its wrapper, result_message
            if ctx.descriptor.body_style is BODY_STYLE_WRAPPED:
                out_type_info = body_message_class._type_info
                out_object = body_message_class()
                bm_attrs = self.get_cls_attrs(body_message_class)

                keys = iter(out_type_info)
                values = iter(ctx.out_object)
                while True:
                    try:
                        k = next(keys)
                    except StopIteration:
                        break
                    try:
                        v = next(values)
                    except StopIteration:
                        v = None

                    out_object._safe_set(k, v, body_message_class, bm_attrs)

                self.to_parent(ctx, body_message_class, out_object,
                               out_body_doc, body_message_class.get_namespace())

            else:
                out_object = ctx.out_object[0]

                sub_ns = body_message_class.Attributes.sub_ns
                if sub_ns is None:
                    sub_ns = body_message_class.get_namespace()
                if sub_ns is DEFAULT_NS:
                    sub_ns = self.app.interface.get_tns()

                sub_name = body_message_class.Attributes.sub_name
                if sub_name is None:
                    sub_name = body_message_class.get_type_name()

                self.to_parent(ctx, body_message_class, out_object, out_body_doc,
                                                            sub_ns, sub_name)

            # header
            if ctx.out_header is not None and header_message_class is not None:
                ctx.out_header_doc = soap_header_elt = etree.SubElement(
                                ctx.out_document, '{%s}Header' % self.ns_soap_env)

                if isinstance(ctx.out_header, (list, tuple)):
                    out_headers = ctx.out_header
                else:
                    out_headers = (ctx.out_header,)

                for header_class, out_header in zip(header_message_class,
                                                                   out_headers):
                    self.to_parent(ctx,
                        header_class, out_header,
                        soap_header_elt,
                        header_class.get_namespace(),
                        header_class.get_type_name(),
                    )

            ctx.out_document.append(ctx.out_body_doc)

        if self.cleanup_namespaces:
            etree.cleanup_namespaces(ctx.out_document)

        self.event_manager.fire_event('after_serialize', ctx)

    def fault_to_http_response_code(self, fault):
        return HTTP_500
