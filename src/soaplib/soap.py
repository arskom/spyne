
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

from lxml import etree

from base64 import b64encode
from StringIO import StringIO

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
from soaplib.serializers.exception import Fault
from soaplib.serializers.binary import Attachment
from soaplib.serializers.clazz import ClassSerializer

import soaplib

_ns_xs = soaplib.nsmap['xs']
_ns_soap_env = soaplib.nsmap['soap_env']
_ns_soap_enc = soaplib.nsmap['soap_enc']

class Message(ClassSerializer):
    @classmethod
    def c(cls, namespace, type_name, members):
        cls_dup = Message.customize()
        cls_dup.__namespace__ = namespace
        cls_dup.__type_name__ = type_name
        cls_dup._type_info = members

        return cls_dup

class MethodDescriptor(object):
    '''
    This class represents the method signature of a soap method,
    and is returned by the soapdocument, or rpc decorators.
    '''

    def __init__(self, name, public_name, in_message, out_message, doc,
                 is_callback=False, is_async=False, mtom=False):
        self.name = name
        self.public_name = public_name
        self.in_message = in_message
        self.out_message = out_message
        self.doc = doc
        self.is_callback = is_callback
        self.is_async = is_async
        self.mtom = mtom

def from_soap(xml_string):
    '''
    Parses the xml string into the header and payload
    '''
    root = etree.fromstring(xml_string)

    body = None
    header = None

    # find the body and header elements
    for e in root.getchildren():
        if e.tag == '{%s}Body' % soaplib.nsmap['soap_env']:
            body = e

        elif e.tag == '{%s}Header' % soaplib.nsmap['soap_env']:
            header = e

    payload = None
    if len(body.getchildren()):
        payload = body.getchildren()[0]

    return payload, header

def make_soap_envelope(message, tns='', header_elements=None):
    '''
    This method takes the results from a soap method call, and wraps them
    in the appropriate soap envelope with any specified headers

    @param the message of the soap envelope, either an element or
           a list of elements
    @param any header elements to be included in the soap response
    @returns the envelope element
    '''
    envelope = etree.Element('{%s}Envelope' % _ns_soap_env)
    if header_elements:
        soap_header = etree.SubElement(envelope, '{%s}Header' % _ns_soap_env)
        for h in header_elements:
            soap_header.append(h)
    body = etree.SubElement(envelope, '{%s}Body' % _ns_soap_env)

    if type(message) == list:
        for m in message:
            body.append(m)

    elif message != None:
        body.append(message)

    return envelope

def join_attachment(id, envelope, payload, prefix=True):
    '''
    Helper function for swa_to_soap.

    Places the data from an attachment back into a SOAP message, replacing
    its xop:Include element or href.

    @param  id          content-id or content-location of attachment
    @param  prefix      Set this to true if id is content-id or false if
                        it is content-location.  It prefixes a "cid:" to
                        the href value.
    @param  envelope    soap envelope string to be operated on
    @param  payload     attachment data
    @return             tuple of length 2 with the new message and the
                        number of replacements made
    '''

    # grab the XML element of the message in the SOAP body
    soapmsg = StringIO(envelope)
    soaptree = etree.parse(soapmsg)
    soapns = soaptree.getroot().tag.split('}')[0].strip('{')
    soapbody = soaptree.getroot().find("{%s}Body" % soapns)
    message = None
    for child in list(soapbody):
        if child.tag != "%sFault" % (soapns, ):
            message = child
            break

    numreplaces = 0
    idprefix = ''
    if prefix == True:
        idprefix = "cid:"
    id = "%s%s" % (idprefix, id, )

    # Make replacement.
    for param in message:
        # Look for Include subelement.
        for sub in param:
            if sub.tag.split('}')[-1] == 'Include' and \
               sub.attrib.get('href') == id:
                param.remove(sub)
                param.text = payload
                numreplaces += 1
        if numreplaces < 1 and param.attrib.get('href') == id:
            del(param.attrib['href'])
            param.text = payload
            numreplaces += 1

    soapmsg.close()
    soapmsg = StringIO()
    soaptree.write(soapmsg)
    joinedmsg = soapmsg.getvalue()
    soapmsg.close()

    return (joinedmsg, numreplaces)


def collapse_swa(content_type, envelope):
    '''
    Translates an SwA multipart/related message into an
    application/soap+xml message.

    References:
    SwA     http://www.w3.org/TR/SOAP-attachments
    XOP     http://www.w3.org/TR/xop10/
    MTOM    http://www.w3.org/TR/soap12-mtom/
            http://www.w3.org/Submission/soap11mtom10/

    @param  content_type value of the Content-Type header field
    @param  envelope     body of the HTTP message, a soap envelope
    @return              appication/soap+xml version of the given HTTP body
    '''

    # convert multipart messages back to pure SOAP
    mime_type = content_type.lower().split(';')
    if 'multipart/related' not in mime_type:
        return envelope

    # parse the body into an email.Message object
    msgString = "MIME-Version: 1.0\r\n" \
                "Content-Type: %s\r\n" % (
                content_type, )
    msgString += "\r\n" + envelope
    msg = message_from_string(msgString) # our message

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
            soapmsg, numreplaces = join_attachment(cloc, soapmsg, payload,
                False)

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
    soapmsg = StringIO(envelope)
    soaptree = etree.parse(soapmsg)
    soapns = soaptree.getroot().tag.split('}')[0].strip('{')
    soapbody = soaptree.getroot().find("{%s}Body" % soapns)
    message = None
    for child in list(soapbody):
        if child.tag != "%sFault" % (soapns, ):
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
    for name,typ in params.items():
        name, typ = params[i]
        if typ == Attachment:
            id = "soaplibAttachment_%s" % (len(mtompkg.get_payload()), )
            param = message[i]
            param.text = ""
            incl = etree.SubElement(param,
                "{http://www.w3.org/2004/08/xop/include}Include")
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
    soapmsg.close()
    soapmsg = StringIO()
    soaptree.write(soapmsg)
    rootpkg.set_payload(soapmsg.getvalue())
    soapmsg.close()

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


def make_soap_fault(fault_string, fault_code = 'Server', detail = None,
        header_elements = None):
    '''
    This method populates a soap fault message with the provided
    fault string and details.
    @param faultString the short description of the error
    @param detail the details of the exception, such as a stack trace
    @param faultCode defaults to 'Server', but can be overridden
    @param header_elements A list of XML elements to add to the fault header.
    @returns the element corresponding to the fault message
    '''
    envelope = etree.Element('{%s}Envelope' % _ns_soap_env)
    if header_elements:
        header = etree.SubElement(
            envelope, '{%s}Header' % _ns_soap_env)
        for element in header_elements:
            header.append(element)
    body = etree.SubElement(envelope, '{%s}Body'  % _ns_soap_env)

    f = Fault(fault_code, fault_string, detail)
    body.append(Fault.to_xml(f, "{%s}Fault" % _ns_soap_env))

    return envelope
