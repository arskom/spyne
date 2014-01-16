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

from spyne.model.complex import ComplexModel
import unittest

from pprint import pprint

from spyne.application import Application
from spyne.const.xml_ns import xsd as _ns_xsd
from spyne.interface.wsdl.wsdl11 import Wsdl11
from spyne.model.complex import Array
from spyne.protocol.xml import XmlDocument
from spyne.protocol.soap.soap11 import Soap11

from spyne.server.wsgi import WsgiApplication
from spyne.service import ServiceBase
from spyne.decorator import rpc

from spyne.model.enum import Enum

from lxml import etree

vals = [
    'Monday',
    'Tuesday',
    'Wednesday',
    'Thursday',
    'Friday',
    'Saturday',
    'Sunday',
]

DaysOfWeekEnum = Enum(
    'Monday',
    'Tuesday',
    'Wednesday',
    'Thursday',
    'Friday',
    'Saturday',
    'Sunday',
    type_name = 'DaysOfWeekEnum',
)

class TestService(ServiceBase):
    @rpc(DaysOfWeekEnum, _returns=DaysOfWeekEnum)
    def get_the_day(self, day):
        return DaysOfWeekEnum.Sunday

class Test(ComplexModel):
    days = DaysOfWeekEnum(max_occurs=7)

class TestEnum(unittest.TestCase):
    def setUp(self):
        self.app = Application([TestService], 'tns', in_protocol=Soap11(), out_protocol=Soap11())
        self.app.transport = 'test'

        self.server = WsgiApplication(self.app)
        self.wsdl = Wsdl11(self.app.interface)
        self.wsdl.build_interface_document('prot://url')

    def test_wsdl(self):
        wsdl = self.wsdl.get_interface_document()

        elt = etree.fromstring(wsdl)
        simple_type = elt.xpath('//xs:simpleType', namespaces=self.app.interface.nsmap)[0]

        print((etree.tostring(elt, pretty_print=True)))
        print(simple_type)

        self.assertEquals(simple_type.attrib['name'], 'DaysOfWeekEnum')
        self.assertEquals(simple_type[0].tag, "{%s}restriction" % _ns_xsd)
        self.assertEquals([e.attrib['value'] for e in simple_type[0]], vals)

    def test_serialize(self):
        mo = DaysOfWeekEnum.Monday
        print((repr(mo)))

        elt = etree.Element('test')
        XmlDocument().to_parent(None, DaysOfWeekEnum, mo, elt, 'test_namespace')
        elt = elt[0]
        ret = XmlDocument().from_element(None, DaysOfWeekEnum, elt)

        self.assertEquals(mo, ret)

    def test_serialize_complex_array(self):
        days = [
                DaysOfWeekEnum.Monday,
                DaysOfWeekEnum.Tuesday,
                DaysOfWeekEnum.Wednesday,
                DaysOfWeekEnum.Thursday,
                DaysOfWeekEnum.Friday,
                DaysOfWeekEnum.Saturday,
                DaysOfWeekEnum.Sunday,
            ]

        days_xml = [
            ('{tns}DaysOfWeekEnum', 'Monday'),
            ('{tns}DaysOfWeekEnum', 'Tuesday'),
            ('{tns}DaysOfWeekEnum', 'Wednesday'),
            ('{tns}DaysOfWeekEnum', 'Thursday'),
            ('{tns}DaysOfWeekEnum', 'Friday'),
            ('{tns}DaysOfWeekEnum', 'Saturday'),
            ('{tns}DaysOfWeekEnum', 'Sunday'),
        ]

        DaysOfWeekEnumArray = Array(DaysOfWeekEnum)
        DaysOfWeekEnumArray.__namespace__ = 'tns'

        elt = etree.Element('test')
        XmlDocument().to_parent(None, DaysOfWeekEnumArray, days,
                                                          elt, 'test_namespace')

        elt = elt[0]
        ret = XmlDocument().from_element(None, Array(DaysOfWeekEnum), elt)
        assert days == ret

        print((etree.tostring(elt, pretty_print=True)))

        pprint(self.app.interface.nsmap)
        assert days_xml == [ (e.tag, e.text) for e in
            elt.xpath('//tns:DaysOfWeekEnum', namespaces=self.app.interface.nsmap)]

    def test_serialize_simple_array(self):
        t = Test(days=[
                DaysOfWeekEnum.Monday,
                DaysOfWeekEnum.Tuesday,
                DaysOfWeekEnum.Wednesday,
                DaysOfWeekEnum.Thursday,
                DaysOfWeekEnum.Friday,
                DaysOfWeekEnum.Saturday,
                DaysOfWeekEnum.Sunday,
            ])

        Test.resolve_namespace(Test, 'tns')

        elt = etree.Element('test')
        XmlDocument().to_parent(None, Test, t, elt, 'test_namespace')
        elt = elt[0]

        print((etree.tostring(elt, pretty_print=True)))

        ret = XmlDocument().from_element(None, Test, elt)
        self.assertEquals(t.days, ret.days)

if __name__ == '__main__':
    unittest.main()
