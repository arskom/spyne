
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

"""The ``spyne.protocol.soap.mime`` module contains additional logic for using
optimized encodings for binary when encapsulating Soap 1.1 messages in Http.

The functionality in this code is not well tested and is reportedly not working
at all.

Patches are welcome.
"""

import logging
logger = logging.getLogger(__name__)

from lxml import etree
from base64 import b64encode

# import email data format related stuff
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.encoders import encode_7or8bit

from email import message_from_string

from spyne.model.binary import Attachment
from spyne.model.binary import ByteArray

import spyne.const.xml_ns
_ns_xop = spyne.const.xml_ns.xop
_ns_soap_env = spyne.const.xml_ns.soap11_env

from spyne.util.six.moves.urllib.parse import unquote


def _join_attachment(href_id, envelope, payload, prefix=True):
    """Places the data from an attachment back into a SOAP message, replacing
    its xop:Include element or href.

    Returns a tuple of length 2 with the new message and the number of
    replacements made

    :param  id:       content-id or content-location of attachment
    :param  prefix:   Set this to true if id is content-id or false if it is
                      content-location.  It prefixes a "cid:" to the href value.
    :param  envelope: soap envelope string to be operated on
    :param  payload:  attachment data
    """

    def replacing(parent, node, payload_, numreplaces_):
        if node.tag == '{%s}Include' % _ns_xop:
            attr = node.attrib.get('href')
            if not attr is None:
                if unquote(attr) == href_id:
                    parent.remove(node)
                    parent.text = payload_
                    numreplaces_ += 1
        else:
            for c in node:
                numreplaces_ = replacing(node, c, payload_, numreplaces_)

        return numreplaces_

    # grab the XML element of the message in the SOAP body
    soaptree = etree.fromstring(envelope)
    soapbody = soaptree.find("{%s}Body" % _ns_soap_env)

    message = None
    for child in list(soapbody):
        if child.tag != "{%s}Fault" % _ns_soap_env:
            message = child
            break

    numreplaces = 0
    idprefix = ''

    if prefix:
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
                    del param.attrib['href']
                    param.text = payload
                    numreplaces += 1

    return etree.tostring(soaptree), numreplaces


def collapse_swa(content_type, envelope):
    """
    Translates an SwA multipart/related message into an application/soap+xml
    message.

    Returns the 'appication/soap+xml' version of the given HTTP body.

    References:
    SwA     http://www.w3.org/TR/SOAP-attachments
    XOP     http://www.w3.org/TR/xop10/
    MTOM    http://www.w3.org/TR/soap12-mtom/
            http://www.w3.org/Submission/soap11mtom10/

    :param  content_type: value of the Content-Type header field, parsed by
                          cgi.parse_header() function
    :param  envelope:     body of the HTTP message, a soap envelope
    """

    # convert multipart messages back to pure SOAP
    mime_type = content_type[0]

    if 'multipart/related' not in mime_type:
        return envelope

    charset = content_type[1].get('charset', None)
    if charset is None:
        charset = 'ascii'

    # parse the body into an email.Message object
    msg_string = [
        "MIME-Version: 1.0",
        "Content-Type: %s; charset=%s" % (mime_type, charset),
        "",
    ]
    msg_string.extend(envelope)

    msg = message_from_string('\r\n'.join(msg_string))  # our message

    soapmsg = None
    root = msg.get_param('start')

    # walk through sections, reconstructing pure SOAP
    for part in msg.walk():
        # skip the multipart container section
        if part.get_content_maintype() == 'multipart':
            continue

        # detect main soap section
        if (part.get('Content-ID') and part.get('Content-ID') == root) or \
                (root is None and part == msg.get_payload()[0]):
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
            soapmsg, numreplaces = _join_attachment(cid, soapmsg, payload)

        # Check for Content-Location and make replacement
        if cloc and not cid and not numreplaces:
            soapmsg, numreplaces = _join_attachment(cloc, soapmsg, payload,
                                                                          False)

    return [soapmsg]


def apply_mtom(headers, envelope, params, paramvals):
    """Apply MTOM to a SOAP envelope, separating attachments into a
    MIME multipart message.

    Returns a tuple of length 2 with dictionary of headers and string of body
    that can be sent with HTTPConnection

    References:
    XOP     http://www.w3.org/TR/xop10/
    MTOM    http://www.w3.org/TR/soap12-mtom/
            http://www.w3.org/Submission/soap11mtom10/

    :param headers   Headers dictionary of the SOAP message that would
                     originally be sent.
    :param envelope  Iterable containing SOAP envelope string that would have
                     originally been sent.
    :param params    params attribute from the Message object used for the SOAP
    :param paramvals values of the params, passed to Message.to_parent
    """

    # grab the XML element of the message in the SOAP body
    envelope = ''.join(envelope)

    soaptree = etree.fromstring(envelope)
    soapbody = soaptree.find("{%s}Body" % _ns_soap_env)

    message = None
    for child in list(soapbody):
        if child.tag == ("{%s}Fault" % _ns_soap_env):
            return headers, envelope
        else:
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
    mtompkg = MIMEMultipart('related', boundary='?//<><>spyne_MIME_boundary<>')
    rootpkg = MIMEApplication(envelope, 'xop+xml', encode_7or8bit)

    # Set up multipart headers.
    del mtompkg['mime-version']
    mtompkg.set_param('start-info', roottype)
    mtompkg.set_param('start', '<spyneEnvelope>')
    if 'SOAPAction' in headers:
        mtompkg.add_header('SOAPAction', headers.get('SOAPAction'))

    # Set up root SOAP part headers.
    del rootpkg['mime-version']

    rootpkg.add_header('Content-ID', '<spyneEnvelope>')

    for n, v in rootparams.items():
        rootpkg.set_param(n, v)

    rootpkg.set_param('type', roottype)

    mtompkg.attach(rootpkg)

    # Extract attachments from SOAP envelope.
    for i in range(len(params)):
        name, typ = params[i]

        if typ in (ByteArray, Attachment):
            id = "spyneAttachment_%s" % (len(mtompkg.get_payload()), )

            param = message[i]
            param.text = ""

            incl = etree.SubElement(param, "{%s}Include" % _ns_xop)
            incl.attrib["href"] = "cid:%s" % id

            if paramvals[i].fileName and not paramvals[i].data:
                paramvals[i].load_from_file()

            if type == Attachment:
                data = paramvals[i].data
            else:
                data = ''.join(paramvals[i])

            attachment = MIMEApplication(data, _encoder=encode_7or8bit)

            del attachment['mime-version']

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
        return headers, envelope

    return mtomheaders, [mtombody]
