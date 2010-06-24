
#
# soaplib - Copyright (C) 2009 Aaron Bickell, Jamie Kirkpatrick
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

import soaplib
_ns_xs = soaplib.nsmap['xs']
_ns_xsi = soaplib.nsmap['xsi']

from soaplib.serializers.primitive import Array
from soaplib.serializers.primitive import Boolean
from soaplib.serializers.primitive import DateTime
from soaplib.serializers.primitive import Float
from soaplib.serializers.primitive import Integer
from soaplib.serializers.base import Null
from soaplib.serializers.primitive import String

class TestPrimitive(unittest.TestCase):
    def test_string(self):
        s = String()
        element = String.to_xml('value')
        self.assertEquals(element.text, 'value')
        value = String.from_xml(element)
        self.assertEquals(value, 'value')

    def test_datetime(self):
        d = DateTime()
        n = datetime.datetime.now()
        element = DateTime.to_xml(n)
        self.assertEquals(element.text, n.isoformat())
        dt = DateTime.from_xml(element)
        self.assertEquals(n, dt)

    def test_utcdatetime(self):
        datestring = '2007-05-15T13:40:44Z'
        e = etree.Element('test')
        e.text = datestring

        dt = DateTime.from_xml(e)

        self.assertEquals(dt.year, 2007)
        self.assertEquals(dt.month, 5)
        self.assertEquals(dt.day, 15)

        datestring = '2007-05-15T13:40:44.003Z'
        e = etree.Element('test')
        e.text = datestring

        dt = DateTime.from_xml(e)

        self.assertEquals(dt.year, 2007)
        self.assertEquals(dt.month, 5)
        self.assertEquals(dt.day, 15)

    def test_integer(self):
        i = 12
        integer = Integer()
        element = Integer.to_xml(i)
        self.assertEquals(element.text, '12')
        self.assertEquals('xs:integer', element.get('{%s}type' % _ns_xsi))
        value = integer.from_xml(element)
        self.assertEquals(value, i)

    def test_large_integer(self):
        i = 128375873458473
        integer = Integer()
        element = Integer.to_xml(i)
        self.assertEquals(element.text, '128375873458473')
        self.assertEquals('xs:integer', element.get('{%s}type' % _ns_xsi))
        value = integer.from_xml(element)
        self.assertEquals(value, i)

    def test_float(self):
        f = 1.22255645

        element = Float.to_xml(f)
        self.assertEquals(element.text, '1.22255645')
        self.assertEquals('xs:float', element.get('{%s}type' % _ns_xsi))

        f2 = Float.from_xml(element)
        self.assertEquals(f2, f)

    def test_array(self):
        serializer = Array(String)
        values = ['a', 'b', 'c', 'd', 'e', 'f']

        element = serializer.to_xml(values)
        self.assertEquals(len(values), len(element.getchildren()))

        print etree.tostring(element, pretty_print=True)

        print serializer.from_xml

        values2 = serializer.from_xml(element)
        self.assertEquals(values[3], values2[3])

    def test_unicode(self):
        s = u'\x34\x55\x65\x34'
        self.assertEquals(4, len(s))
        element = String.to_xml(s)
        value = String.from_xml(element)
        self.assertEquals(value, s)

    def test_null(self):
        element = Null.to_xml('doesnt matter')
        self.assertEquals('1', element.get('{%s}nil' % _ns_xs))
        value = Null.from_xml(element)
        self.assertEquals(None, value)

    def test_boolean(self):
        b = Boolean.to_xml(True)
        self.assertEquals('true', b.text)

        b = Boolean.to_xml(0)
        self.assertEquals('false', b.text)

        b = Boolean.to_xml(1)
        self.assertEquals('true', b.text)

        b = Boolean.from_xml(b)
        self.assertEquals(b, True)

        b = Boolean.to_xml(False)
        self.assertEquals('false', b.text)

        b = Boolean.from_xml(b)
        self.assertEquals(b, False)

        b = Boolean.to_xml(False)
        self.assertEquals('xs:boolean', b.get('{%s}type' % _ns_xsi))

        b = Boolean.to_xml(None)
        self.assertEquals('1', b.get('{%s}nil' % _ns_xs))

        b = Boolean.from_xml(b)
        self.assertEquals(b, None)

def test_suite():
    loader = unittest.TestLoader()
    return loader.loadTestsFromTestCase(TestPrimitive)

if __name__== '__main__':
    unittest.TextTestRunner().run(test_suite())
