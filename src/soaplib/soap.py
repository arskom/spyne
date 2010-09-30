
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

from base64 import b64encode
from urllib import unquote

# import email data format related stuff
try:
    # python >= 2.5
    from email.mime.multipart import MIMEMultipart
    from email.mime.application import MIMEApplication
    from email.encoders import encode_7or8bit
except ImportError:
    # python 2.4
    from email.MIMENonMultipart import MIMENonMultipart
    from email.MIMEMultipart import MIMEMultipart
    from email.Encoders import encode_7or8bit

from email import message_from_string

# import soaplib stuff
from soaplib.serializers.binary import Attachment
from soaplib.serializers.clazz import ClassSerializer

import soaplib

class Message(ClassSerializer):
    pass


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

def from_soap(xml_string, http_charset):
    '''
    Parses the xml string into the header and payload
    '''
    try:
        root, xmlids = etree.XMLID(xml_string.decode(http_charset))
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
    body=None
    if len(body_envelope) > 0 and len(body_envelope[0]) > 0:
        body = body_envelope[0].getchildren()[0]

    header=None
    if len(header_envelope) > 0 and len(header_envelope[0]) > 0:
        header = header_envelope[0].getchildren()[0]

    return body, header

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

def join_attachment(href_id, envelope, payload, prefix=True):
    '''
    Helper function for swa_to_soap.

    Places the data from an attachment back into a SOAP message, replacing
    its xop:Include element or href.

    @param  id        content-id or content-location of attachment
    @param  prefix    Set this to true if id is content-id or false if it is
                      content-location.  It prefixes a "cid:" to the href value.
    @param  envelope  soap envelope string to be operated on
    @param  payload   attachment data

    @return           tuple of length 2 with the new message and the
                      number of replacements made
    '''

    def replacing(parent, node, payload, numreplaces):
        if node.tag == '{%s}Include' % soaplib.ns_xop:
            attrib = node.attrib.get('href')
            if not attrib is None:
                if unquote(attrib) == href_id:
                    parent.remove(node)
                    parent.text = payload
                    numreplaces += 1
        else:
            for child in node:
                numreplaces = replacing(node, child, payload, numreplaces)

        return numreplaces

    # grab the XML element of the message in the SOAP body
    soaptree = etree.fromstring(envelope)
    soapbody = soaptree.find("{%s}Body" % soaplib.ns_soap_env)

    message = None
    for child in list(soapbody):
        if child.tag != "{%s}Fault" % soaplib.ns_soap_env:
            message = child
            break

    numreplaces = 0
    idprefix = ''

    if prefix == True:
        idprefix = "cid:"
    href_id = "%s%s" % (idprefix, href_id, )

    # Make replacement.
    for param in message:
        # Look for Include subelement.
        for sub in param:
            numreplaces = replacing(param, sub, payload, numreplaces)

        if numreplaces < 1:
            attrib = param.attrib.get('href')
            if not attrib is None:
                if unquote(attrib) == href_id:
                    del(param.attrib['href'])
                    param.text = payload
                    numreplaces += 1

    return (etree.tostring(soaptree), numreplaces)

def collapse_swa(content_type, envelope):
    '''
    Translates an SwA multipart/related message into an
    application/soap+xml message.

    References:
    SwA     http://www.w3.org/TR/SOAP-attachments
    XOP     http://www.w3.org/TR/xop10/
    MTOM    http://www.w3.org/TR/soap12-mtom/
            http://www.w3.org/Submission/soap11mtom10/

    @param  content_type value of the Content-Type header field, parsed by
                         cgi.parse_header() function
    @param  envelope     body of the HTTP message, a soap envelope
    @return              appication/soap+xml version of the given HTTP body
    '''

    # convert multipart messages back to pure SOAP
    mime_type = content_type[0]

    if 'multipart/related' not in mime_type:
        return envelope

    charset = content_type[1].get('charset', None)
    if charset is None:
        charset='ascii'

    # parse the body into an email.Message object
    msg_string = [
        "MIME-Version: 1.0",
        "Content-Type: %s; charset=%s" % (mime_type, charset),
        "",
        envelope
    ]

    msg = message_from_string('\r\n'.join(msg_string)) # our message

    soapmsg = None
    root = msg.get_param('start')

    # walk through sections, reconstructing pure SOAP
    for part in msg.walk():
        # skip the multipart container section
        if part.get_content_maintype() == 'multipart':
            continue

        # detect main soap section
        if (part.get('Content-ID') and part.get('Content-ID') == root) or \
           (root == None and part == msg.get_payload()[0]):
            soapmsg = part.get_payload()
            continue

        # binary packages
        cte = part.get("Content-Transfer-Encoding")

        payload = None
        if cte != 'base64':
            payload = b64encode(part.get_payload())
        else:
            payload = part.get_payload()

        cid = part.get("Content-ID").strip("<>")
        cloc = part.get("Content-Location")
        numreplaces = None

        # Check for Content-ID and make replacement
        if cid:
            soapmsg, numreplaces = join_attachment(cid, soapmsg, payload)

        # Check for Content-Location and make replacement
        if cloc and not cid and not numreplaces:
            soapmsg, numreplaces = join_attachment(cloc, soapmsg, payload, False)

    return soapmsg

def apply_mtom(headers, envelope, params, paramvals):
    '''
    Apply MTOM to a SOAP envelope, separating attachments into a
    MIME multipart message.

    References:
    XOP     http://www.w3.org/TR/xop10/
    MTOM    http://www.w3.org/TR/soap12-mtom/
            http://www.w3.org/Submission/soap11mtom10/

    @param headers   Headers dictionary of the SOAP message that would
                     originally be sent.
    @param envelope  SOAP envelope string that would have originally been sent.
    @param params    params attribute from the Message object used for the SOAP
    @param paramvals values of the params, passed to Message.to_xml
    @return          tuple of length 2 with dictionary of headers and
                     string of body that can be sent with HTTPConnection
    '''

    # grab the XML element of the message in the SOAP body
    soaptree = etree.fromstring(envelope)
    soapbody = soaptree.find("{%s}Body" % soaplib.ns_soap_env)

    message = None
    for child in list(soapbody):
        if child.tag != "%sFault" % (soaplib.ns_soap_env, ):
            message = child
            break

    # Get additional parameters from original Content-Type
    ctarray = []
    for n, v in headers.items():
        if n.lower() == 'content-type':
            ctarray = v.split(';')
            break
    roottype = ctarray[0].strip()
    rootparams = {}
    for ctparam in ctarray[1:]:
        n, v = ctparam.strip().split('=')
        rootparams[n] = v.strip("\"'")

    # Set up initial MIME parts.
    mtompkg = MIMEMultipart('related',
        boundary='?//<><>soaplib_MIME_boundary<>')
    rootpkg = None
    try:
        rootpkg = MIMEApplication(envelope, 'xop+xml', encode_7or8bit)
    except NameError:
        rootpkg = MIMENonMultipart("application", "xop+xml")
        rootpkg.set_payload(envelope)
        encode_7or8bit(rootpkg)

    # Set up multipart headers.
    del(mtompkg['mime-version'])
    mtompkg.set_param('start-info', roottype)
    mtompkg.set_param('start', '<soaplibEnvelope>')
    if 'SOAPAction' in headers:
        mtompkg.add_header('SOAPAction', headers.get('SOAPAction'))

    # Set up root SOAP part headers.
    del(rootpkg['mime-version'])

    rootpkg.add_header('Content-ID', '<soaplibEnvelope>')

    for n, v in rootparams.items():
        rootpkg.set_param(n, v)

    rootpkg.set_param('type', roottype)

    mtompkg.attach(rootpkg)

    # Extract attachments from SOAP envelope.
    for i in range(len(params)):
        name, typ = params[i]

        if typ == Attachment:
            id = "soaplibAttachment_%s" % (len(mtompkg.get_payload()), )

            param = message[i]
            param.text = ""

            incl = etree.SubElement(param, "{%s}Include" % soaplib.ns_xop)
            incl.attrib["href"] = "cid:%s" % id

            if paramvals[i].fileName and not paramvals[i].data:
                paramvals[i].load_from_file()

            data = paramvals[i].data
            attachment = None

            try:
                attachment = MIMEApplication(data, _encoder=encode_7or8bit)

            except NameError:
                attachment = MIMENonMultipart("application", "octet-stream")
                attachment.set_payload(data)
                encode_7or8bit(attachment)

            del(attachment['mime-version'])

            attachment.add_header('Content-ID', '<%s>' % (id, ))
            mtompkg.attach(attachment)

    # Update SOAP envelope.
    rootpkg.set_payload(etree.tostring(soaptree))

    # extract body string from MIMEMultipart message
    bound = '--%s' % (mtompkg.get_boundary(), )
    marray = mtompkg.as_string().split(bound)
    mtombody = bound
    mtombody += bound.join(marray[1:])

    # set Content-Length
    mtompkg.add_header("Content-Length", str(len(mtombody)))

    # extract dictionary of headers from MIMEMultipart message
    mtomheaders = {}
    for name, value in mtompkg.items():
        mtomheaders[name] = value

    if len(mtompkg.get_payload()) <= 1:
        return (headers, envelope)

    return (mtomheaders, mtombody)
