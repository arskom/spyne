
import unittest
from urllib import urlquote

from lxml import etree

import soaplib

from soaplib.serializers.clazz import ClassSerializer
from soaplib.serializers.primitive import Integer
from soaplib.serializers.primitive import String
from soaplib.soap import join_attachment

# Service Classes
class DownloadPartFileResult(ClassSerializer):
    ErrorCode = Integer
    ErrorMessage = String
    Data = String

# Tests
class TestInclude(unittest.TestCase):
    def test_join_attachment(self):
        href_id="http://tempuri.org/1/634133419330914808"
        payload="ANJNSLJNDYBC SFDJNIREMX:CMKSAJN"
        envelope = '''
            <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
                <s:Body>
                    <DownloadPartFileResponse xmlns="http://tempuri.org/">
                        <DownloadPartFileResult xmlns:a="http://schemas.datacontract.org/2004/07/KlanApi.Common" xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
                            <a:ErrorCode>0</a:ErrorCode>
                            <a:ErrorMessage i:nil="true"/>
                            <a:Data>
                                <xop:Include href="cid:%s" xmlns:xop="http://www.w3.org/2004/08/xop/include"/>
                            </a:Data>
                        </DownloadPartFileResult>
                    </DownloadPartFileResponse>
                </s:Body>
            </s:Envelope>
        ''' % urlquote(href_id)

        (joinedmsg, numreplaces) = join_attachment(href_id, envelope, payload)

        soaptree = etree.fromstring(joinedmsg)

        body = soaptree.find("{%s}Body" % soaplib.ns_soap_env)
        response = body.getchildren()[0]
        result = response.getchildren()[0]
        r = DownloadPartFileResult.from_xml(result)

        self.assertEquals(payload, r.Data)

def suite():
    loader = unittest.TestLoader()
    return loader.loadTestsFromTestCase(TestInclude)

if __name__== '__main__':
    unittest.TextTestRunner().run(suite())
