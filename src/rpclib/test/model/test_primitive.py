#!/usr/bin/env python
#
# rpclib - Copyright (C) Rpclib contributors.
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

import datetime
import unittest

from lxml import etree

from rpclib.model.complex import Array
from rpclib.model.primitive import Date
from rpclib.model.primitive import Time
from rpclib.model.primitive import Boolean
from rpclib.model.primitive import DateTime
from rpclib.model.primitive import Duration
from rpclib.model.primitive import Float
from rpclib.model.primitive import Integer
from rpclib.model._base import Null
from rpclib.model.primitive import String
from rpclib.const import xml_ns as ns

from rpclib.protocol.xml import XmlObject

ns_test = 'test_namespace'

class TestPrimitive(unittest.TestCase):
    def test_string(self):
        s = String()
        element = etree.Element('test')
        XmlObject().to_parent_element(String, 'value', ns_test, element)
        element=element[0]

        self.assertEquals(element.text, 'value')
        value = XmlObject().from_element(String, element)
        self.assertEquals(value, 'value')

    def test_datetime(self):
        n = datetime.datetime.now()

        element = etree.Element('test')
        XmlObject().to_parent_element(DateTime, n, ns_test, element)
        element = element[0]

        self.assertEquals(element.text, n.isoformat())
        dt = XmlObject().from_element(DateTime, element)
        self.assertEquals(n, dt)

    def test_time(self):
        n = datetime.time(1, 2, 3, 4)

        ret = Time.to_string(n)
        self.assertEquals(ret, n.isoformat())

        dt = Time.from_string(ret)
        self.assertEquals(n, dt)

    def test_date(self):
        n = datetime.time(1, 2, 3, 4)

        ret = Date.to_string(n)
        self.assertEquals(ret, n.isoformat())

        dt = Time.from_string(ret)
        self.assertEquals(n, dt)

    def test_duration_xml_duration(self):
        dur = datetime.timedelta(days=5 + 30 + 365, hours=1, minutes=1,
                                                   seconds=12, microseconds=8e5)

        str1 = 'P400DT3672.8S'
        str2 = 'P1Y1M5DT1H1M12.8S'

        self.assertEquals(dur, Duration.from_string(str1))
        self.assertEquals(dur, Duration.from_string(str2))

        self.assertEquals(dur, Duration.from_string(Duration.to_string(dur)))

    def test_utcdatetime(self):
        datestring = '2007-05-15T13:40:44Z'
        e = etree.Element('test')
        e.text = datestring

        dt = XmlObject().from_element(DateTime, e)

        self.assertEquals(dt.year, 2007)
        self.assertEquals(dt.month, 5)
        self.assertEquals(dt.day, 15)

        datestring = '2007-05-15T13:40:44.003Z'
        e = etree.Element('test')
        e.text = datestring

        dt = XmlObject().from_element(DateTime, e)

        self.assertEquals(dt.year, 2007)
        self.assertEquals(dt.month, 5)
        self.assertEquals(dt.day, 15)

    def test_integer(self):
        i = 12
        integer = Integer()

        element = etree.Element('test')
        XmlObject().to_parent_element(Integer, i, ns_test, element)
        element = element[0]

        self.assertEquals(element.text, '12')
        value = XmlObject().from_element(integer, element)
        self.assertEquals(value, i)

    def test_large_integer(self):
        i = 128375873458473
        integer = Integer()

        element = etree.Element('test')
        XmlObject().to_parent_element(Integer, i, ns_test, element)
        element = element[0]

        self.assertEquals(element.text, '128375873458473')
        value = XmlObject().from_element(integer, element)
        self.assertEquals(value, i)

    def test_float(self):
        f = 1.22255645

        element = etree.Element('test')
        XmlObject().to_parent_element(Float, f, ns_test, element)
        element = element[0]

        self.assertEquals(element.text, repr(f))

        f2 = XmlObject().from_element(Float, element)
        self.assertEquals(f2, f)

    def test_array(self):
        type = Array(String)
        type.resolve_namespace(type, "zbank")

        values = ['a', 'b', 'c', 'd', 'e', 'f']

        element = etree.Element('test')
        XmlObject().to_parent_element(type, values, ns_test, element)
        element = element[0]

        self.assertEquals(len(values), len(element.getchildren()))

        values2 = XmlObject().from_element(type, element)
        self.assertEquals(values[3], values2[3])

    def test_array_empty(self):
        type = Array(String)
        type.resolve_namespace(type, "zbank")

        values = []

        element = etree.Element('test')
        XmlObject().to_parent_element(type, values, ns_test, element)
        element = element[0]

        self.assertEquals(len(values), len(element.getchildren()))

        values2 = XmlObject().from_element(type, element)
        self.assertEquals(len(values2), 0)

    def test_unicode(self):
        s = u'\x34\x55\x65\x34'
        self.assertEquals(4, len(s))
        element = etree.Element('test')
        XmlObject().to_parent_element(String, s, 'test_ns', element)
        element = element[0]
        value = XmlObject().from_element(String, element)
        self.assertEquals(value, s)

    def test_null(self):
        element = etree.Element('test')
        XmlObject().to_parent_element(Null, None, ns_test, element)
        print etree.tostring(element)

        element = element[0]
        self.assertTrue( bool(element.attrib.get('{%s}nil' % ns.xsi)) )
        value = XmlObject().from_element(Null, element)
        self.assertEquals(None, value)

    def test_boolean(self):
        b = etree.Element('test')
        XmlObject().to_parent_element(Boolean, True, ns_test, b)
        b = b[0]
        self.assertEquals('true', b.text)

        b = etree.Element('test')
        XmlObject().to_parent_element(Boolean, 0, ns_test, b)
        b = b[0]
        self.assertEquals('false', b.text)

        b = etree.Element('test')
        XmlObject().to_parent_element(Boolean, 1, ns_test, b)
        b = b[0]
        self.assertEquals('true', b.text)

        b = XmlObject().from_element(Boolean, b)
        self.assertEquals(b, True)

        b = etree.Element('test')
        XmlObject().to_parent_element(Boolean, False, ns_test, b)
        b = b[0]
        self.assertEquals('false', b.text)

        b = XmlObject().from_element(Boolean, b)
        self.assertEquals(b, False)

        b = etree.Element('test')
        XmlObject().to_parent_element(Boolean, None, ns_test, b)
        b = b[0]
        self.assertEquals('true', b.get('{%s}nil' % ns.xsi))

        b = XmlObject().from_element(Boolean, b)
        self.assertEquals(b, None)

if __name__ == '__main__':
    unittest.main()
