#!/usr/bin/env python
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

import unittest
try:
    from urllib import quote_plus
except ImportError:
    from urllib.parse import quote_plus

from lxml import etree

from spyne.model.complex import ComplexModel
from spyne.model.primitive import Integer
from spyne.model.primitive import String
from spyne.protocol.xml import XmlDocument
from spyne.protocol.soap.mime import _join_attachment
from spyne.const import xml_ns as ns

# Service Classes
class DownloadPartFileResult(ComplexModel):
    ErrorCode = Integer
    ErrorMessage = String
    Data = String

# Tests
class TestInclude(unittest.TestCase):
    def test_bytes_join_attachment(self):
        href_id="http://tempuri.org/1/634133419330914808"
        payload="ANJNSLJNDYBC SFDJNIREMX:CMKSAJN"
        envelope = '''
            <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
                <s:Body>
                    <DownloadPartFileResponse xmlns="http://tempuri.org/">
                        <DownloadPartFileResult xmlns:a="http://schemas.datacontract.org/2004/07/KlanApi.Common"
                                                xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
                            <a:ErrorCode>0</a:ErrorCode>
                            <a:ErrorMessage i:nil="true"/>
                            <a:Data>
                                <xop:Include href="cid:%s" xmlns:xop="http://www.w3.org/2004/08/xop/include"/>
                            </a:Data>
                        </DownloadPartFileResult>
                    </DownloadPartFileResponse>
                </s:Body>
            </s:Envelope>
        ''' % quote_plus(href_id)

        (joinedmsg, numreplaces) = _join_attachment(href_id, envelope, payload)

        soaptree = etree.fromstring(joinedmsg)

        body = soaptree.find("{%s}Body" % ns.soap11_env)
        response = body.getchildren()[0]
        result = response.getchildren()[0]
        r = XmlDocument().from_element(None, DownloadPartFileResult, result)

        self.assertEquals(payload, r.Data)

if __name__ == '__main__':
    unittest.main()
