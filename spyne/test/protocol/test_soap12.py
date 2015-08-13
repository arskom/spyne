#!/usr/bin/env python

import unittest

from lxml import etree
from lxml.doctestcompare import LXMLOutputChecker, PARSE_XML

from spyne import Fault
from spyne.util.six import BytesIO
from spyne.application import Application
from spyne.decorator import srpc
from spyne.interface import Wsdl11
from spyne.server.wsgi import WsgiApplication
from spyne.protocol.soap.soap12 import Soap12
from spyne.service import ServiceBase
from spyne.test.protocol.test_soap11 import TestService, TestSingle, \
    TestMultiple, MultipleReturnService


def start_response(code, headers):
    print(code, headers)


class TestSingleSoap12(TestSingle):
    def setUp(self):
        self.app = Application([TestService], 'tns', in_protocol=Soap12(), out_protocol=Soap12())
        self.app.transport = 'null.spyne'
        self.srv = TestService()

        wsdl = Wsdl11(self.app.interface)
        wsdl.build_interface_document('URL')
        self.wsdl_str = wsdl.get_interface_document()
        self.wsdl_doc = etree.fromstring(self.wsdl_str)


class TestMultipleSoap12(TestMultiple):
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
        class SoapException(ServiceBase):
            @srpc()
            def soap_exception():
                raise Fault(
                    "Client.Plausible", "A plausible fault", 'http://faultactor.example.com')
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
            'CONTENT_TYPE': 'text/xml',
            'wsgi.input': BytesIO(req)
        }, start_response, "http://null")))

        response_str = etree.tostring(response, pretty_print=True)
        print(response_str)

        expected = b"""
            <soap12env:Envelope xmlns:soap12env="http://www.w3.org/2003/05/soap-envelope">
              <soap12env:Body>
                <soap12env:Fault>
                  <soap12env:Reason>
                      <soap12env:Text xml:lang="en">A plausible fault</soap12env:Text>
                  </soap12env:Reason>
                  <soap12env:Role>http://faultactor.example.com</soap12env:Role>
                  <soap12env:Code>
                    <soap12env:Value>soap12env:Sender</soap12env:Value>
                    <soap12env:Subcode>
                      <soap12env:Value>Plausible</soap12env:Value>
                    </soap12env:Subcode>
                  </soap12env:Code>
                </soap12env:Fault>
              </soap12env:Body>
            </soap12env:Envelope>"""
        if not LXMLOutputChecker().check_output(expected, response_str, PARSE_XML):
            raise Exception("Got: %s but expected: %s" % (response_str, expected))


if __name__ == '__main__':
    unittest.main()
