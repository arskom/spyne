#!/usr/bin/env python

# this doesn't work yet because <union> is not implemented

from __future__ import print_function


EXAMPLE_DOCUMENT = """
<wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" soapenv:mustUnderstand="1">
    <wsu:Timestamp xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd" wsu:Id="Timestamp-15452452">
        <wsu:Created>2016-02-01T10:14:54.517Z</wsu:Created>
        <wsu:Expires>2016-02-01T10:19:54.517Z</wsu:Expires>
    </wsu:Timestamp>
    <ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#" Id="Signature-2088192064">
        <ds:SignedInfo>
            <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#" />
            <ds:SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1" />
            <ds:Reference URI="#Id-1052429873">
                <ds:Transforms>
                    <ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#" />
                </ds:Transforms>
                <ds:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1" />
                <ds:DigestValue>...</ds:DigestValue>
            </ds:Reference>
            <ds:Reference URI="#Timestamp-15452452">
                <ds:Transforms>
                    <ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#" />
                </ds:Transforms>
                <ds:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1" />
                <ds:DigestValue>...</ds:DigestValue>
            </ds:Reference>
        </ds:SignedInfo>
        <ds:SignatureValue>
...
        </ds:SignatureValue>
        <ds:KeyInfo Id="KeyId-8475839474">
            <wsse:SecurityTokenReference xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd" wsu:Id="STRId-680050181">
                <wsse:KeyIdentifier EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509SubjectKeyIdentifier">...</wsse:KeyIdentifier>
            </wsse:SecurityTokenReference>
        </ds:KeyInfo>
    </ds:Signature>
</wsse:Security>
"""

class NS:
    WSSE = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd"
    WSU = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd"
    DS = "http://www.w3.org/2000/09/xmldsig#"
    XSD = "http://www.w3.org/2001/XMLSchema"
    XML = "http://www.w3.org/XML/1998/namespace"

files = {
    NS.WSSE: "wsse.xsd",
    NS.WSU: "wsu.xsd",
    NS.DS: "ds.xsd",
    NS.XSD: "xsd.xsd",
    NS.XML: "xml.xsd",
}


from os.path import isfile
from datetime import datetime, timedelta

from spyne import Service
from spyne.util.xml import parse_schema_file


for fn in files:
    if not isfile(fn):
        raise Exception("Please run 'make' in this script's directory to fetch"
                        "schema files before running this example")


import logging
logging.basicConfig(level=logging.DEBUG)


wsse = parse_schema_file(files[NS.WSSE], files=files)
wsu = parse_schema_file(files[NS.WSU], files=files)


class InteropServiceWithHeader(Service):
    __out_header__ = Security

    @rpc(_returns=Security)
    def send_out_header(ctx):
        ctx.out_header = Security(
            timestamp=TimeStamp(
                created=datetime.now(),
                expired=datetime.now() + timedelta(days=365),
            )
        )
        ctx.out_header.dt = datetime(year=2000, month=1, day=1)
        ctx.out_header.f = 3.141592653

        return ctx.out_header
