
#
# soaplib - Copyright (C) Soaplib contributors.
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

import soaplib
from soaplib.serializers.exception import Fault

class MethodDescriptor(object):
    '''
    This class represents the method signature of a soap method,
    and is returned by the soapdocument, or rpc decorators.
    '''

    def __init__(self, name, public_name, in_message, out_message, doc,
                 is_callback=False, is_async=False, mtom=False, in_header=None,
                 out_header=None):

        self.name = name
        self.public_name = public_name
        self.in_message = in_message
        self.out_message = out_message
        self.doc = doc
        self.is_callback = is_callback
        self.is_async = is_async
        self.mtom = mtom
        self.in_header = in_header
        self.out_header = out_header

def from_soap(xml_string, charset):
    '''
    Parses the xml string into the header and payload
    '''

    try:
        root, xmlids = etree.XMLID(xml_string.decode(charset))
    except ValueError,e:
        logger.debug('%s -- falling back to str decoding.' % (e))
        root, xmlids = etree.XMLID(xml_string)

    if xmlids:
        resolve_hrefs(root, xmlids)

    if root.tag != '{%s}Envelope' % soaplib.ns_soap_env:
        raise Fault('Client.SoapError', 'No {%s}Envelope element was found!' % soaplib.ns_soap_env)

    header_envelope = root.xpath('e:Header', namespaces={'e': soaplib.ns_soap_env})
    body_envelope = root.xpath('e:Body', namespaces={'e': soaplib.ns_soap_env})

    if len(header_envelope) == 0 and len(body_envelope) == 0:
        raise Fault('Client.SoapError', 'Soap envelope is empty!' % soaplib.ns_soap_env)

    header=None
    if len(header_envelope) > 0 and len(header_envelope[0]) > 0:
        header = header_envelope[0].getchildren()[0]

    body=None
    if len(body_envelope) > 0 and len(body_envelope[0]) > 0:
        body = body_envelope[0].getchildren()[0]

    return header, body

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
