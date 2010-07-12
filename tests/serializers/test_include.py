import unittest

from soaplib.serializers.primitive import String, Integer
from soaplib.serializers.clazz import ClassSerializer
from soaplib.soap import join_attachment

from StringIO import StringIO
from soaplib.xml import ElementTree


##########################################################
# Service Classes
##########################################################

class DownloadPartFileResult(ClassSerializer):
    class types:
        ErrorCode = Integer
        ErrorMessage = String
        Data = String

##########################################################
# Tests
##########################################################

class test(unittest.TestCase):

    def test_join_attachment(self):
        id="http://tempuri.org/1/634133419330914808"
        payload="ANJNSLJNDYBC SFDJNIREMX:CMKSAJN"
        envelope = '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"&gt;&lt;s:Body&gt;&lt;DownloadPartFileResponse xmlns="http://tempuri.org/"&gt;&lt;DownloadPartFileResult xmlns:a="http://schemas.datacontract.org/2004/07/KlanApi.Common" xmlns:i="http://www.w3.org/2001/XMLSchema-instance"&gt;&lt;a:ErrorCode&gt;0&lt;/a:ErrorCode&gt;&lt;a:ErrorMessage i:nil="true"/><a:Data><xop:Include href="cid:http%3A%2F%2Ftempuri.org%2F1%2F634133419330914808" xmlns:xop="http://www.w3.org/2004/08/xop/include"/&gt;&lt;/a:Data&gt;&lt;/DownloadPartFileResult&gt;&lt;/DownloadPartFileResponse&gt;&lt;/s:Body&gt;&lt;/s:Envelope&gt;'
        (joinedmsg, numreplaces) = join_attachment(id, envelope, payload)

        soapmsg = StringIO(joinedmsg)
        soaptree = ElementTree.parse(soapmsg)

        soapns = "http://schemas.xmlsoap.org/soap/envelope/"
        r = DownloadPartFileResult.from_xml( soaptree.getroot().find("{%s}Body" % soapns).getchildren()[0].getchildren()[0] )

        self.assertEquals(payload, r.Data)

def test_suite():
    loader = unittest.TestLoader()
    return loader.loadTestsFromTestCase(test)

if __name__== '__main__':
    unittest.TextTestRunner().run(test_suite())