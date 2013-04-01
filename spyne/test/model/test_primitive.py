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

import re
import datetime
import unittest

from lxml import etree

from spyne.const import xml_ns as ns
from spyne.model import Null
from spyne.model.binary import File
from spyne.model.binary import ByteArray
from spyne.model.complex import Array
from spyne.model.complex import ComplexModel
from spyne.model.primitive import Date
from spyne.model.primitive import Time
from spyne.model.primitive import Boolean
from spyne.model.primitive import DateTime
from spyne.model.primitive import Duration
from spyne.model.primitive import Float
from spyne.model.primitive import Integer
from spyne.model.primitive import UnsignedInteger
from spyne.model.primitive import AnyXml
from spyne.model.primitive import AnyDict
from spyne.model.primitive import AnyUri
from spyne.model.primitive import Unicode
from spyne.model.primitive import String
from spyne.model.primitive import Decimal
from spyne.model.primitive import Double
from spyne.model.primitive import Integer64
from spyne.model.primitive import Integer32
from spyne.model.primitive import Integer16
from spyne.model.primitive import Integer8
from spyne.model.primitive import UnsignedInteger64
from spyne.model.primitive import UnsignedInteger32
from spyne.model.primitive import UnsignedInteger16
from spyne.model.primitive import UnsignedInteger8

from spyne.protocol import ProtocolBase
from spyne.protocol.xml import XmlDocument

from spyne.application import Application
from spyne.decorator import srpc
from spyne.service import ServiceBase
from spyne.interface.xml_schema import XmlSchema

ns_test = 'test_namespace'


class TestPrimitive(unittest.TestCase):
    def test_invalid_name(self):
        class Service(ServiceBase):
            @srpc()
            def XResponse():
                pass

        try:
            Application([Service], 'hey', in_protocol=XmlDocument(),
                                          out_protocol=XmlDocument())
        except:
            pass
        else:
            raise Exception("must fail.")

    def test_string(self):
        s = String()
        element = etree.Element('test')
        XmlDocument().to_parent_element(String, 'value', ns_test, element)
        element=element[0]

        self.assertEquals(element.text, 'value')
        value = XmlDocument().from_element(String, element)
        self.assertEquals(value, 'value')

    def test_datetime(self):
        n = datetime.datetime.now()

        element = etree.Element('test')
        XmlDocument().to_parent_element(DateTime, n, ns_test, element)
        element = element[0]

        self.assertEquals(element.text, n.isoformat())
        dt = XmlDocument().from_element(DateTime, element)
        self.assertEquals(n, dt)

    def test_datetime_format(self):
        n = datetime.datetime.now().replace(microsecond=0)
        format = "%Y %m %d %H %M %S"

        element = etree.Element('test')
        XmlDocument().to_parent_element(DateTime(format=format), n, ns_test, element)
        element = element[0]

        assert element.text == datetime.datetime.strftime(n, format)
        dt = XmlDocument().from_element(DateTime(format=format), element)
        assert n == dt

    def test_date_format(self):
        t = datetime.date.today()
        format = "%Y %m %d"

        element = etree.Element('test')
        XmlDocument().to_parent_element(Date(format=format), t, ns_test, element)
        assert element[0].text == datetime.date.strftime(t, format)

        dt = XmlDocument().from_element(Date(format=format), element[0])
        assert t == dt

    def test_datetime_timezone(self):
        import pytz

        n = datetime.datetime.now(pytz.timezone('EST'))
        element = etree.Element('test')
        XmlDocument().to_parent_element(DateTime(as_time_zone=pytz.utc), n, ns_test, element)
        element = element[0]

        c = n.astimezone(pytz.utc).replace(tzinfo=None)
        self.assertEquals(element.text, c.isoformat())
        dt = XmlDocument().from_element(DateTime, element)
        self.assertEquals(c, dt)

    def test_time(self):
        n = datetime.time(1, 2, 3, 4)

        ret = ProtocolBase.to_string(Time, n)
        self.assertEquals(ret, n.isoformat())

        dt = ProtocolBase.from_string(Time, ret)
        self.assertEquals(n, dt)

    def test_date(self):
        n = datetime.date(2011,12,13)

        ret = ProtocolBase.to_string(Date, n)
        self.assertEquals(ret, n.isoformat())

        dt = ProtocolBase.from_string(Date, ret)
        self.assertEquals(n, dt)

    def test_duration_xml_duration(self):
        dur = datetime.timedelta(days=5 + 30 + 365, hours=1, minutes=1,
                                                   seconds=12, microseconds=8e5)

        str1 = 'P400DT3672.8S'
        str2 = 'P1Y1M5DT1H1M12.8S'

        self.assertEquals(dur, ProtocolBase.from_string(Duration, str1))
        self.assertEquals(dur, ProtocolBase.from_string(Duration, str2))

        self.assertEquals(dur, ProtocolBase.from_string(Duration, ProtocolBase.to_string(Duration, dur)))

    def test_utcdatetime(self):
        datestring = '2007-05-15T13:40:44Z'
        e = etree.Element('test')
        e.text = datestring

        dt = XmlDocument().from_element(DateTime, e)

        self.assertEquals(dt.year, 2007)
        self.assertEquals(dt.month, 5)
        self.assertEquals(dt.day, 15)

        datestring = '2007-05-15T13:40:44.003Z'
        e = etree.Element('test')
        e.text = datestring

        dt = XmlDocument().from_element(DateTime, e)

        self.assertEquals(dt.year, 2007)
        self.assertEquals(dt.month, 5)
        self.assertEquals(dt.day, 15)

    def test_integer(self):
        i = 12
        integer = Integer()

        element = etree.Element('test')
        XmlDocument().to_parent_element(Integer, i, ns_test, element)
        element = element[0]

        self.assertEquals(element.text, '12')
        value = XmlDocument().from_element(integer, element)
        self.assertEquals(value, i)

    def test_limits(self):
        try:
            ProtocolBase.from_string(Integer, "1" * (Integer.__max_str_len__ + 1))
        except:
            pass
        else:
            raise Exception("must fail.")

        ProtocolBase.from_string(UnsignedInteger, "-1") # This is not supposed to fail.

        try:
            UnsignedInteger.validate_native(-1) # This is supposed to fail.
        except:
            pass
        else:
            raise Exception("must fail.")

    def test_large_integer(self):
        i = 128375873458473
        integer = Integer()

        element = etree.Element('test')
        XmlDocument().to_parent_element(Integer, i, ns_test, element)
        element = element[0]

        self.assertEquals(element.text, '128375873458473')
        value = XmlDocument().from_element(integer, element)
        self.assertEquals(value, i)

    def test_float(self):
        f = 1.22255645

        element = etree.Element('test')
        XmlDocument().to_parent_element(Float, f, ns_test, element)
        element = element[0]

        self.assertEquals(element.text, repr(f))

        f2 = XmlDocument().from_element(Float, element)
        self.assertEquals(f2, f)

    def test_array(self):
        type = Array(String)
        type.resolve_namespace(type, "zbank")

        values = ['a', 'b', 'c', 'd', 'e', 'f']

        element = etree.Element('test')
        XmlDocument().to_parent_element(type, values, ns_test, element)
        element = element[0]

        self.assertEquals(len(values), len(element.getchildren()))

        values2 = XmlDocument().from_element(type, element)
        self.assertEquals(values[3], values2[3])

    def test_array_empty(self):
        type = Array(String)
        type.resolve_namespace(type, "zbank")

        values = []

        element = etree.Element('test')
        XmlDocument().to_parent_element(type, values, ns_test, element)
        element = element[0]

        self.assertEquals(len(values), len(element.getchildren()))

        values2 = XmlDocument().from_element(type, element)
        self.assertEquals(len(values2), 0)

    def test_unicode(self):
        s = u'\x34\x55\x65\x34'
        self.assertEquals(4, len(s))
        element = etree.Element('test')
        XmlDocument().to_parent_element(String, s, 'test_ns', element)
        element = element[0]
        value = XmlDocument().from_element(String, element)
        self.assertEquals(value, s)

    def test_null(self):
        element = etree.Element('test')
        XmlDocument().to_parent_element(Null, None, ns_test, element)
        print(etree.tostring(element))

        element = element[0]
        self.assertTrue( bool(element.attrib.get('{%s}nil' % ns.xsi)) )
        value = XmlDocument().from_element(Null, element)
        self.assertEquals(None, value)

    def test_point(self):
        from spyne.model.primitive import _get_point_pattern

        a=re.compile(_get_point_pattern(2))
        assert a.match('POINT (10 40)') is not None
        assert a.match('POINT(10 40)') is not None

        assert a.match('POINT(10.0 40)') is not None
        assert a.match('POINT(1.310e4 40)') is not None

    def test_multipoint(self):
        from spyne.model.primitive import _get_multipoint_pattern

        a=re.compile(_get_multipoint_pattern(2))
        assert a.match('MULTIPOINT (10 40, 40 30, 20 20, 30 10)') is not None
        # FIXME:
        #assert a.match('MULTIPOINT ((10 40), (40 30), (20 20), (30 10))') is not None

    def test_linestring(self):
        from spyne.model.primitive import _get_linestring_pattern

        a=re.compile(_get_linestring_pattern(2))
        assert a.match('LINESTRING (30 10, 10 30, 40 40)') is not None

    def test_multilinestring(self):
        from spyne.model.primitive import _get_multilinestring_pattern

        a=re.compile(_get_multilinestring_pattern(2))
        assert a.match('''MULTILINESTRING ((10 10, 20 20, 10 40),
                                (40 40, 30 30, 40 20, 30 10))''') is not None

    def test_polygon(self):
        from spyne.model.primitive import _get_polygon_pattern

        a=re.compile(_get_polygon_pattern(2))
        assert a.match('POLYGON ((30 10, 10 20, 20 40, 40 40, 30 10))') is not None

    def test_multipolygon(self):
        from spyne.model.primitive import _get_multipolygon_pattern

        a=re.compile(_get_multipolygon_pattern(2))
        assert a.match('''MULTIPOLYGON (((30 20, 10 40, 45 40, 30 20)),
                            ((15 5, 40 10, 10 20, 5 10, 15 5)))''') is not None
        assert a.match('''MULTIPOLYGON (((40 40, 20 45, 45 30, 40 40)),
                                ((20 35, 45 20, 30 5, 10 10, 10 30, 20 35),
                                (30 20, 20 25, 20 15, 30 20)))''') is not None

    def test_boolean(self):
        b = etree.Element('test')
        XmlDocument().to_parent_element(Boolean, True, ns_test, b)
        b = b[0]
        self.assertEquals('true', b.text)

        b = etree.Element('test')
        XmlDocument().to_parent_element(Boolean, 0, ns_test, b)
        b = b[0]
        self.assertEquals('false', b.text)

        b = etree.Element('test')
        XmlDocument().to_parent_element(Boolean, 1, ns_test, b)
        b = b[0]
        self.assertEquals('true', b.text)

        b = XmlDocument().from_element(Boolean, b)
        self.assertEquals(b, True)

        b = etree.Element('test')
        XmlDocument().to_parent_element(Boolean, False, ns_test, b)
        b = b[0]
        self.assertEquals('false', b.text)

        b = XmlDocument().from_element(Boolean, b)
        self.assertEquals(b, False)

        b = etree.Element('test')
        XmlDocument().to_parent_element(Boolean, None, ns_test, b)
        b = b[0]
        self.assertEquals('true', b.get('{%s}nil' % ns.xsi))

        b = XmlDocument().from_element(Boolean, b)
        self.assertEquals(b, None)

    def test_type_names(self):
        class Test(ComplexModel):
            any_xml = AnyXml
            any_dict = AnyDict
            unicode_ = Unicode
            any_uri = AnyUri
            decimal = Decimal
            double = Double
            float = Float
            integer = Integer
            unsigned = UnsignedInteger
            int64 = Integer64
            int32 = Integer32
            int16 = Integer16
            int8 = Integer8
            uint64 = UnsignedInteger64
            uint32 = UnsignedInteger32
            uint16 = UnsignedInteger16
            uint8 = UnsignedInteger8
            t = Time
            d = Date
            dt = DateTime
            dur = Duration
            bool = Boolean
            f = File
            b = ByteArray

        class Service(ServiceBase):
            @srpc(Test)
            def call(t):
                pass

        AnyXml.__type_name__ = 'oui'
        try:
            app.interface.build_interface_document()
        except:
            pass
        else:
            raise Exception("must fail.")

        AnyXml.__type_name__ = 'anyType'

        app = Application([Service], 'hey', in_protocol=XmlDocument(), out_protocol=XmlDocument())
        XmlSchema(app.interface).build_interface_document()


if __name__ == '__main__':
    unittest.main()
