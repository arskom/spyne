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
from soaplib.serializers.primitive import Fault
from soaplib.serializers.binary import Attachment
from soaplib.xml import create_xml_element, create_xml_subelement
from soaplib.xml import NamespaceLookup, ElementTree


class Message(object):

    def __init__(self, name, params, ns=None, typ=None):
        self.name = name
        self.params = params
        if typ == None:
            typ = name
        self.typ = typ
        self.ns = ns

    def to_xml(self, *data):
        if len(self.params):
            if len(data) != len(self.params):
                raise Exception("Parameter number mismatch expected [%s] "
                    "got [%s]"%(len(self.params), len(data)))

        nsmap = NamespaceLookup(self.ns)
        element = create_xml_element(self.name, nsmap, self.ns)

        for i in range(0, len(self.params)):
            name, serializer = self.params[i]
            d = data[i]
            e = serializer.to_xml(d, name, nsmap)
            if type(e) in (list, tuple):
                elist = e
                for e in elist:
                    element.append(e)
            elif e == None:
                pass
            else:
                element.append(e)

        ElementTree.cleanup_namespaces(element)
        return element

    def from_xml(self, element):
        results = []
        try:
            children = element.getchildren()
        except:
            return []

        def findall(name):
            # inner method for finding child node
            nodes = []
            for c in children:
                if c.tag.split('}')[-1] == name:
                    nodes.append(c)
            return nodes

        for name, serializer in self.params:
            childnodes = findall(name)
            if len(childnodes) == 0:
                results.append(None)
            else:
                results.append(serializer.from_xml(*childnodes))
        return results

    def add_to_schema(self, schemaDict, nsmap):
        complexType = create_xml_element(nsmap.get('xs') + 'complexType',
            nsmap)
        complexType.set('name', self.typ)

        sequence = create_xml_subelement(complexType,
            nsmap.get('xs') + 'sequence')
        if self.params:
            for name, serializer in self.params:
                e = create_xml_subelement(sequence,
                    nsmap.get('xs') + 'element')
                e.set('name', name)
                e.set('type',
                    "%s:%s" % (serializer.get_namespace_id(),
                        serializer.get_datatype()))

        element = create_xml_element(nsmap.get('xs') + 'element', nsmap)
        element.set('name', self.typ)
        element.set('type', '%s:%s' % ('tns', self.typ))

        schemaDict[self.typ] = complexType
        schemaDict[self.typ + 'Element'] = element


class MethodDescriptor:
    '''
    This class represents the method signature of a soap method,
    and is returned by the soapdocument, or soapmethod decorators.
    '''

    def __init__(self, name, soapAction, inMessage, outMessage, doc,
                 isCallback=False, isAsync=False, mtom=False):
        self.inMessage = inMessage
        self.outMessage = outMessage
        self.soapAction = soapAction
        self.name = name
        self.isCallback = isCallback
        self.isAsync = isAsync
        self.doc = doc
        self.mtom = mtom


def from_soap(xml_string):
    '''
    Parses the xml string into the header and payload
    '''
    root, xmlids = ElementTree.XMLID(xml_string)
    if xmlids:
        resolve_hrefs(root, xmlids)
    body = None
    header = None

    # find the body and header elements
    for e in root.getchildren():
        name = e.tag.split('}')[-1].lower()
        if name == 'body':
            body = e
        elif name == 'header':
            header = e
    payload = None
    if len(body.getchildren()):
        payload = body.getchildren()[0]

    return payload, header


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
        else:
            resolve_hrefs(e, xmlids)
    return element


def make_soap_envelope(message, tns='', header_elements=None):
    '''
    This method takes the results from a soap method call, and wraps them
    in the appropriate soap envelope with any specified headers

    @param the message of the soap envelope, either an element or
           a list of elements
    @param any header elements to be included in the soap response
    @returns the envelope element
    '''
    nsmap = NamespaceLookup(tns)
    envelope = create_xml_element(nsmap.get('SOAP-ENV') + 'Envelope', nsmap,
        tns)
    if header_elements:
        headerElement = create_xml_subelement(envelope,
            nsmap.get('SOAP-ENV') + 'Header')
        for h in header_elements:
            headerElement.append(h)
    body = create_xml_subelement(envelope, nsmap.get('SOAP-ENV') + 'Body')
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
    soaptree = ElementTree.parse(soapmsg)
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
    soaptree = ElementTree.parse(soapmsg)
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

    # Set up initial MIME parts
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
            incl = create_xml_subelement(param,
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


def make_soap_fault(faultString, faultCode = 'Server', detail = None,
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
    nsmap = NamespaceLookup()
    envelope = create_xml_element(nsmap.get('SOAP-ENV') + 'Envelope', nsmap)
    if header_elements:
        header = create_xml_subelement(
            envelope, nsmap.get('SOAP-ENV') + 'Header')
        for element in header_elements:
            header.append(element)
    body = create_xml_subelement(envelope, nsmap.get('SOAP-ENV') + 'Body')
    f = Fault(faultCode, faultString, detail)
    body.append(Fault.to_xml(f, nsmap.get('SOAP-ENV') + "Fault", nsmap))
    return envelope
