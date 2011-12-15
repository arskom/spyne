
import logging
logger = logging.getLogger(__name__)
from lxml import etree

from base64 import b64encode

try:
    from urllib import unquote
except ImportError: # Python 3
    from urllib.parse import unquote

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
from rpclib.model.binary import Attachment
from rpclib.model.binary import ByteArray
import rpclib.const.xml_ns

_ns_xop = rpclib.const.xml_ns.xop
_ns_soap_env = rpclib.const.xml_ns.soap_env

def join_attachment(href_id, envelope, payload, prefix=True):
    '''Places the data from an attachment back into a SOAP message, replacing
    its xop:Include element or href.

    Returns a tuple of length 2 with the new message and the number of
    replacements made

    :param  id:        content-id or content-location of attachment
    :param  prefix:    Set this to true if id is content-id or false if it is
                       content-location.  It prefixes a "cid:" to the href value.
    :param  envelope:  soap envelope string to be operated on
    :param  payload:   attachment data
    '''

    def replacing(parent, node, payload, numreplaces):
        if node.tag == '{%s}Include' % _ns_xop:
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
    soapbody = soaptree.find("{%s}Body" % _ns_soap_env)

    message = None
    for child in list(soapbody):
        if child.tag != "{%s}Fault" % _ns_soap_env:
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
    ]
    msg_string.extend(envelope)

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

    return [soapmsg]

def apply_mtom(headers, envelope, params, paramvals):
    '''Apply MTOM to a SOAP envelope, separating attachments into a
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
    :param paramvals values of the params, passed to Message.to_parent_element
    '''

    # grab the XML element of the message in the SOAP body
    envelope = ''.join(envelope)

    soaptree = etree.fromstring(envelope)
    soapbody = soaptree.find("{%s}Body" % _ns_soap_env)

    message = None
    for child in list(soapbody):
        if child.tag == ("{%s}Fault" % _ns_soap_env):
            return (headers, envelope)
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
    mtompkg = MIMEMultipart('related', boundary='?//<><>rpclib_MIME_boundary<>')
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
    mtompkg.set_param('start', '<rpclibEnvelope>')
    if 'SOAPAction' in headers:
        mtompkg.add_header('SOAPAction', headers.get('SOAPAction'))

    # Set up root SOAP part headers.
    del(rootpkg['mime-version'])

    rootpkg.add_header('Content-ID', '<rpclibEnvelope>')

    for n, v in rootparams.items():
        rootpkg.set_param(n, v)

    rootpkg.set_param('type', roottype)

    mtompkg.attach(rootpkg)

    # Extract attachments from SOAP envelope.
    for i in range(len(params)):
        name, typ = params[i]

        if typ in (ByteArray, Attachment):
            id = "rpclibAttachment_%s" % (len(mtompkg.get_payload()), )

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

    return (mtomheaders, [mtombody])

from rpclib.model.binary import Attachment
