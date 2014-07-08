from lxml import etree
import unittest
import pytest
from spyne import Fault
from spyne.application import Application
from spyne.interface import Wsdl11
from spyne.protocol.soap.soap12 import Soap12
from spyne.test.protocol.test_soap11 import TestService, TestSingle, \
    TestMultiple, MultipleReturnService


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
        element = etree.fromstring("""
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

#       TODO: make from element -> Fault(1.1)
#        pytest.set_trace()
#        ret = Soap12().from_element(None, Fault, element[0][0])
#        assert ret.faultcode == "soap:Client"


