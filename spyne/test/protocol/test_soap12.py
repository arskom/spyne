#!/usr/bin/env python

from __future__ import unicode_literals

import unittest

from lxml import etree
from lxml.doctestcompare import LXMLOutputChecker, PARSE_XML

from spyne import Fault, Unicode, ByteArray
from spyne.application import Application
from spyne.const import xml as ns
from spyne.const.xml import NS_SOAP11_ENV
from spyne.decorator import srpc, rpc
from spyne.interface import Wsdl11
from spyne.model.complex import ComplexModel
from spyne.model.primitive import Integer, String
from spyne.protocol.soap.mime import _join_attachment
from spyne.protocol.soap.soap12 import Soap12
from spyne.protocol.xml import XmlDocument
from spyne.server.wsgi import WsgiApplication
from spyne.service import Service
from spyne.test.protocol.test_soap11 import TestService, TestSingle, \
    TestReturn, MultipleReturnService
from spyne.util.six import BytesIO


def start_response(code, headers):
    print(code, headers)


MTOM_REQUEST = b"""
--uuid:2e53e161-b47f-444a-b594-eb6b72e76997
Content-Type: application/xop+xml; charset=UTF-8;
  type="application/soap+xml"; action="sendDocument";
Content-Transfer-Encoding: binary
Content-ID: <root.message@cxf.apache.org>

<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
  <soap:Body>
    <ns3:documentRequest xmlns:xmime="http://www.w3.org/2005/05/xmlmime" xmlns:ns3="http://gib.gov.tr/vedop3/eFatura">
      <fileName>EA055406-5881-4F02-A3DC-9A5A7510D018.dat</fileName>
      <binaryData xmime:contentType="application/octet-stream">
        <xop:Include xmlns:xop="http://www.w3.org/2004/08/xop/include" href="cid:04dfbca1-54b8-4631-a556-4addea6716ed-223384@cxf.apache.org"/>
      </binaryData>
      <hash>26981FCD51C95FA47780400B7A45132F</hash>
    </ns3:documentRequest>
  </soap:Body>
</soap:Envelope>

--uuid:2e53e161-b47f-444a-b594-eb6b72e76997
Content-Type: application/octet-stream
Content-Transfer-Encoding: binary
Content-ID: <04dfbca1-54b8-4631-a556-4addea6716ed-223384@cxf.apache.org>

sample data
--uuid:2e53e161-b47f-444a-b594-eb6b72e76997--
"""


# Service Classes
class DownloadPartFileResult(ComplexModel):
    ErrorCode = Integer
    ErrorMessage = String
    Data = String


class TestSingleSoap12(TestSingle):
    def setUp(self):
        self.app = Application([TestService], 'tns', in_protocol=Soap12(), out_protocol=Soap12())
        self.app.transport = 'null.spyne'
        self.srv = TestService()

        wsdl = Wsdl11(self.app.interface)
        wsdl.build_interface_document('URL')
        self.wsdl_str = wsdl.get_interface_document()
        self.wsdl_doc = etree.fromstring(self.wsdl_str)


class TestMultipleSoap12(TestReturn):
    def setUp(self):
        self.app = Application([MultipleReturnService], 'tns', in_protocol=Soap12(), out_protocol=Soap12())
        self.app.transport = 'none'
        self.wsdl = Wsdl11(self.app.interface)
        self.wsdl.build_interface_document('URL')


class TestSoap12(unittest.TestCase):

    def test_soap12(self):
        element = etree.fromstring(b"""
        <soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
          <soap:Body>
            <soap:Fault>
                <soap:Code>
                    <soap:Value>env:Sender</soap:Value>
                    <soap:Subcode>
                        <soap:Value>st:SomeDomainProblem</soap:Value>
                    </soap:Subcode>
                </soap:Code>
                <soap:Reason>
                    <soap:Text xml:lang="en-US">
                        Some_Policy
                    </soap:Text>
                </soap:Reason>
            </soap:Fault>
          </soap:Body>
        </soap:Envelope>""")

        so = Soap12()
        ret = so.from_element(None, Fault, element[0][0])
        assert ret.faultcode == "env:Sender.st:SomeDomainProblem"

    def test_fault_generation(self):
        class SoapException(Service):
            @srpc()
            def soap_exception():
                raise Fault(
                    "Client.Plausible.issue", "A plausible fault", 'http://faultactor.example.com',
                    detail={'some':'extra info'})
        app = Application([SoapException], 'tns', in_protocol=Soap12(), out_protocol=Soap12())

        req = b"""
        <soap12env:Envelope
                xmlns:soap12env="http://www.w3.org/2003/05/soap-envelope"
                xmlns:tns="tns">
            <soap12env:Body>
                <tns:soap_exception/>
            </soap12env:Body>
        </soap12env:Envelope>
        """

        server = WsgiApplication(app)
        response = etree.fromstring(b''.join(server({
            'QUERY_STRING': '',
            'PATH_INFO': '/call',
            'REQUEST_METHOD': 'POST',
            'CONTENT_TYPE': 'text/xml; charset=utf8',
            'wsgi.input': BytesIO(req)
        }, start_response, "http://null")))

        response_str = etree.tostring(response, pretty_print=True)
        print(response_str)

        expected = b"""
            <soap12env:Envelope xmlns:soap12env="http://www.w3.org/2003/05/soap-envelope">
              <soap12env:Body>
                <soap12env:Fault>
                  <soap12env:Code>
                    <soap12env:Value>soap12env:Sender</soap12env:Value>
                    <soap12env:Subcode>
                      <soap12env:Value>Plausible</soap12env:Value>
                      <soap12env:Subcode>
                        <soap12env:Value>issue</soap12env:Value>
                      </soap12env:Subcode>
                    </soap12env:Subcode>
                  </soap12env:Code>
                  <soap12env:Reason>
                      <soap12env:Text xml:lang="en">A plausible fault</soap12env:Text>
                  </soap12env:Reason>
                  <soap12env:Role>http://faultactor.example.com</soap12env:Role>
                  <soap12env:Detail>
                    <some>extra info</some>
                  </soap12env:Detail>
                </soap12env:Fault>
              </soap12env:Body>
            </soap12env:Envelope>"""
        if not LXMLOutputChecker().check_output(expected, response_str, PARSE_XML):
            raise Exception("Got: %s but expected: %s" % (response_str, expected))

    def test_gen_fault_codes(self):
        fault_string = "Server.Plausible.error"
        value, faultstrings = Soap12().gen_fault_codes(faultstring=fault_string)
        self.assertEqual(value, "%s:Receiver" %(Soap12.soap_env))
        self.assertEqual(faultstrings[0], "Plausible")
        self.assertEqual(faultstrings[1], "error")

        fault_string = "UnknownFaultCode.Plausible.error"
        with self.assertRaises(TypeError):
            value, faultstrings = Soap12().gen_fault_codes(faultstring=fault_string)

    def test_mtom(self):
        FILE_NAME = 'EA055406-5881-4F02-A3DC-9A5A7510D018.dat'
        TNS = 'http://gib.gov.tr/vedop3/eFatura'
        class SomeService(Service):
            @rpc(Unicode(sub_name="fileName"), ByteArray(sub_name='binaryData'),
                 ByteArray(sub_name="hash"), _returns=Unicode)
            def documentRequest(ctx, file_name, file_data, data_hash):
                assert file_name == FILE_NAME
                assert file_data == (b'sample data',)

                return file_name

        app = Application([SomeService], tns=TNS,
                                    in_protocol=Soap12(), out_protocol=Soap12())

        server = WsgiApplication(app)
        response = etree.fromstring(b''.join(server({
            'QUERY_STRING': '',
            'PATH_INFO': '/call',
            'REQUEST_METHOD': 'POST',
            'CONTENT_TYPE': 'Content-Type: multipart/related; '
                            'type="application/xop+xml"; '
                            'boundary="uuid:2e53e161-b47f-444a-b594-eb6b72e76997"; '
                            'start="<root.message@cxf.apache.org>"; '
                            'start-info="application/soap+xml"; action="sendDocument"',
            'wsgi.input': BytesIO(MTOM_REQUEST.replace(b"\n", b"\r\n"))
        }, start_response, "http://null")))

        response_str = etree.tostring(response, pretty_print=True)
        print(response_str)

        nsdict = dict(tns=TNS)

        assert etree.fromstring(response_str) \
            .xpath(".//tns:documentRequestResult/text()", namespaces=nsdict) \
                                                                  == [FILE_NAME]

    def test_mtom_join_envelope_chunks(self):
        FILE_NAME = 'EA055406-5881-4F02-A3DC-9A5A7510D018.dat'
        TNS = 'http://gib.gov.tr/vedop3/eFatura'

        # large enough payload to be chunked
        PAYLOAD = b"sample data " * 1024
        class SomeService(Service):
            @rpc(Unicode(sub_name="fileName"), ByteArray(sub_name='binaryData'),
                 ByteArray(sub_name="hash"), _returns=Unicode)
            def documentRequest(ctx, file_name, file_data, data_hash):
                assert file_name == FILE_NAME
                assert file_data == (PAYLOAD,)

                return file_name

        app = Application([SomeService], tns=TNS,
                                    in_protocol=Soap12(), out_protocol=Soap12())

        server = WsgiApplication(app, block_length=1024)
        response = etree.fromstring(b''.join(server({
            'QUERY_STRING': '',
            'PATH_INFO': '/call',
            'REQUEST_METHOD': 'POST',
            'CONTENT_TYPE': 'Content-Type: multipart/related; '
                            'type="application/xop+xml"; '
                            'boundary="uuid:2e53e161-b47f-444a-b594-eb6b72e76997"; '
                            'start="<root.message@cxf.apache.org>"; '
                            'start-info="application/soap+xml"; action="sendDocument"',
            'wsgi.input': BytesIO(MTOM_REQUEST
                                  .replace(b"\n", b"\r\n")
                                  .replace(b"sample data", PAYLOAD)),
        }, start_response, "http://null")))

        response_str = etree.tostring(response, pretty_print=True)
        print(response_str)

        nsdict = dict(tns=TNS)

        assert etree.fromstring(response_str) \
            .xpath(".//tns:documentRequestResult/text()", namespaces=nsdict) \
                                                                  == [FILE_NAME]

    def test_bytes_join_attachment(self):
        href_id = "http://tempuri.org/1/634133419330914808"
        payload = "ANJNSLJNDYBC SFDJNIREMX:CMKSAJN"
        envelope = '''
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
  <s:Body>
    <DownloadPartFileResponse xmlns="http://tempuri.org/">
      <DownloadPartFileResult
            xmlns:a="http://schemas.datacontract.org/2004/07/KlanApi.Common"
            xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
        <a:ErrorCode>0</a:ErrorCode>
        <a:ErrorMessage i:nil="true"/>
        <a:Data>
          <xop:Include href="cid:%s"
                             xmlns:xop="http://www.w3.org/2004/08/xop/include"/>
        </a:Data>
      </DownloadPartFileResult>
    </DownloadPartFileResponse>
  </s:Body>
</s:Envelope>
        ''' % href_id

        (joinedmsg, numreplaces) = _join_attachment(NS_SOAP11_ENV,
                                                     href_id, envelope, payload)

        soaptree = etree.fromstring(joinedmsg)

        body = soaptree.find(ns.SOAP11_ENV("Body"))
        response = body.getchildren()[0]
        result = response.getchildren()[0]
        r = XmlDocument().from_element(None, DownloadPartFileResult, result)

        self.assertEqual(payload, r.Data)


if __name__ == '__main__':
    unittest.main()
