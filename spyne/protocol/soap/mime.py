
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

The functionality in this code seems to work at first glance but is not well
tested.

Testcases and preferably improvements are most welcome.
"""

from __future__ import print_function, unicode_literals

import logging
logger = logging.getLogger(__name__)

import re

from base64 import b64encode
from itertools import chain

from lxml import etree

from email import generator
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.encoders import encode_7or8bit

from spyne import ValidationError
from spyne.util import six
from spyne.model.binary import ByteArray, File
from spyne.const.xml import NS_XOP

if six.PY2:
    from email import message_from_string as message_from_bytes
else:
    from email import message_from_bytes


XPATH_NSDICT = dict(xop=NS_XOP)


def _join_attachment(ns_soap_env, href_id, envelope, payload, prefix=True):
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

    # grab the XML element of the message in the SOAP body
    soaptree = etree.fromstring(envelope)
    soapbody = soaptree.find("{%s}Body" % ns_soap_env)

    if soapbody is None:
        raise ValidationError(None, "SOAP Body tag not found")

    message = None
    for child in list(soapbody):
        if child.tag != "{%s}Fault" % ns_soap_env:
            message = child
            break

    idprefix = ''

    if prefix:
        idprefix = "cid:"
    href_id = "%s%s" % (idprefix, href_id,)

    num = 0
    xpath = ".//xop:Include[@href=\"{}\"]".format(href_id)

    for num, node in enumerate(message.xpath(xpath, namespaces=XPATH_NSDICT)):
        parent = node.getparent()
        parent.remove(node)
        parent.text = payload

    return etree.tostring(soaptree), num


def collapse_swa(ctx, content_type, ns_soap_env):
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
    :param  ctx:          request context
    """

    envelope = ctx.in_string
    # convert multipart messages back to pure SOAP
    mime_type, content_data = content_type
    if not six.PY2:
        assert isinstance(mime_type, six.text_type)

    if u'multipart/related' not in mime_type:
        return envelope

    charset = content_data.get('charset', None)
    if charset is None:
        charset = 'ascii'

    boundary = content_data.get('boundary', None)
    if boundary is None:
        raise ValidationError(None, u"Missing 'boundary' value from "
                                                         u"Content-Type header")

    envelope = list(envelope)

    # What an ugly hack...
    request = MIMEMultipart('related', boundary=boundary)
    msg_string = re.sub(r"\n\n.*", '', request.as_string())
    msg_string = chain(
        (msg_string.encode(charset), generator.NL.encode('ascii')),
        (e for e in envelope),
    )

    msg_string = b''.join(msg_string)
    msg = message_from_bytes(msg_string)  # our message

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

        if cte != 'base64':
            payload = b64encode(part.get_payload(decode=True))
        else:
            payload = part.get_payload()

        cid = part.get("Content-ID").strip("<>")
        cloc = part.get("Content-Location")
        numreplaces = None

        # Check for Content-ID and make replacement
        if cid:
            soapmsg, numreplaces = _join_attachment(
                                             ns_soap_env, cid, soapmsg, payload)

        # Check for Content-Location and make replacement
        if cloc and not cid and not numreplaces:
            soapmsg, numreplaces = _join_attachment(
                                            ns_soap_env, cloc, soapmsg, payload,
                                                                          False)

    if soapmsg is None:
        raise ValidationError(None, "Invalid MtoM request")

    return (soapmsg,)


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

        if issubclass(typ, (ByteArray, File)):
            id = "SpyneAttachment_%s" % (len(mtompkg.get_payload()), )

            param = message[i]
            param.text = ""

            incl = etree.SubElement(param, "{%s}Include" % _ns_xop)
            incl.attrib["href"] = "cid:%s" % id

            if paramvals[i].fileName and not paramvals[i].data:
                paramvals[i].load_from_file()

            if issubclass(type, File):
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
