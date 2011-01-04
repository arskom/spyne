#!/usr/bin/env python
#
# soaplib - Copyright (C) Soaplib contributors.
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

from soaplib.core import namespaces

_ns_xs = namespaces.ns_xsd
_ns_xsi = namespaces.ns_xsi

from soaplib.core import Application
Application.transport = 'test'

from soaplib.core.service import DefinitionBase
from soaplib.core.service import soap

from soaplib.core.model.enum import Enum

from lxml import etree

vals = [
    'Monday',
    'Tuesday',
    'Wednesday',
    'Friday',
    'Saturday',
    'Sunday',
]

DaysOfWeekEnum = Enum(
    'Monday',
    'Tuesday',
    'Wednesday',
    'Friday',
    'Saturday',
    'Sunday',
    type_name = 'DaysOfWeekEnum'
)

class TestService(DefinitionBase):
    @soap(DaysOfWeekEnum, _returns=DaysOfWeekEnum)
    def remote_call(self, day):
        return DaysOfWeekEnum.Sunday

class TestEnum(unittest.TestCase):
    def test_wsdl(self):
        app = Application([TestService],'tns')
        wsdl = app.get_wsdl('punk')
        elt = etree.fromstring(wsdl)
        simple_type = elt.xpath('//xs:simpleType', namespaces=app.nsmap)[0]

        # Avoid printing debug output during test runs.
        #print etree.tostring(elt, pretty_print=True)
        #print simple_type

        self.assertEquals(simple_type.attrib['name'], 'DaysOfWeekEnum')
        self.assertEquals(simple_type[0].tag, "{%s}restriction" % namespaces.ns_xsd)
        self.assertEquals([e.attrib['value'] for e in simple_type[0]], vals)

    def test_serialize(self):
        DaysOfWeekEnum.resolve_namespace(DaysOfWeekEnum, 'punk')
        mo = DaysOfWeekEnum.Monday
        # Avoid printing debug output during test runs.
        #print repr(mo)

        elt = etree.Element('test')
        DaysOfWeekEnum.to_parent_element(mo, 'test_namespace', elt)
        elt = elt[0]
        ret = DaysOfWeekEnum.from_xml(elt)

        self.assertEquals(mo, ret)

if __name__ == '__main__':
    unittest.main()
