#!/usr/bin/env python
# coding=utf-8
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
import uuid
import datetime
import unittest

import pytz

from datetime import timedelta

import spyne
from lxml import etree

from spyne.util import total_seconds
from spyne.const import xml_ns as ns

from spyne import Null, AnyDict, Uuid, Array, ComplexModel, Date, Time, \
    Boolean, DateTime, Duration, Float, Integer, UnsignedInteger, Unicode, \
    String, Decimal
from spyne.model import ModelBase

from spyne.protocol import ProtocolBase
from spyne.protocol.xml import XmlDocument

ns_test = 'test_namespace'


class TestPrimitive(unittest.TestCase):
    def test_getitem_cust(self):
        assert Unicode[dict(max_len=2)].Attributes.max_len

    def test_nillable_quirks(self):
        assert ModelBase.Attributes.nillable == True
        class Attributes(ModelBase.Attributes):
            nillable = False
            nullable = False

        assert Attributes.nillable == False
        assert Attributes.nullable == False

        class Attributes(ModelBase.Attributes):
            nillable = True

        assert Attributes.nillable == True
        assert Attributes.nullable == True

        class Attributes(ModelBase.Attributes):
            nillable = False

        assert Attributes.nillable == False
        assert Attributes.nullable == False

        class Attributes(ModelBase.Attributes):
            nullable = True

        assert Attributes.nillable == True
        assert Attributes.nullable == True

        class Attributes(ModelBase.Attributes):
            nullable = False

        assert Attributes.nillable == False
        assert Attributes.nullable == False

        class Attributes(ModelBase.Attributes):
            nullable = False
        class Attributes(Attributes):
            pass
        assert Attributes.nullable == False

    def test_nillable_inheritance_quirks(self):
        class Attributes(ModelBase.Attributes):
            nullable = False

        class AttrMixin:
            pass
        class NewAttributes(Attributes, AttrMixin):
            pass
        assert NewAttributes.nullable is False

        class AttrMixin:
            pass
        class NewAttributes(AttrMixin, Attributes):
            pass

        assert NewAttributes.nullable is False

    def test_decimal(self):
        assert Decimal(10,4).Attributes.total_digits == 10
        assert Decimal(10,4).Attributes.fraction_digits == 4

    def test_decimal_format(self):
        f = 123456
        str_format='${0}'
        element = etree.Element('test')
        XmlDocument().to_parent(None, Decimal(str_format=str_format), f, element, ns_test)
        element = element[0]

        self.assertEquals(element.text, '$123456')

    def test_string(self):
        s = String()
        element = etree.Element('test')
        XmlDocument().to_parent(None, String, 'value', element, ns_test)
        element=element[0]

        self.assertEquals(element.text, 'value')
        value = XmlDocument().from_element(None, String, element)
        self.assertEquals(value, 'value')

    def test_datetime(self):
        n = datetime.datetime.now(pytz.utc)

        element = etree.Element('test')
        XmlDocument().to_parent(None, DateTime, n, element, ns_test)
        element = element[0]

        self.assertEquals(element.text, n.isoformat())
        dt = XmlDocument().from_element(None, DateTime, element)
        self.assertEquals(n, dt)

    def test_datetime_format(self):
        n = datetime.datetime.now().replace(microsecond=0)
        format = "%Y %m %d %H %M %S"

        element = etree.Element('test')
        XmlDocument().to_parent(None, DateTime(format=format), n, element, ns_test)
        element = element[0]

        assert element.text == datetime.datetime.strftime(n, format)
        dt = XmlDocument().from_element(None, DateTime(format=format), element)
        assert n == dt

    def test_datetime_unicode_format(self):
        n = datetime.datetime.now().replace(microsecond=0)
        format = u"%Y %m %d\u00a0%H %M %S"

        element = etree.Element('test')
        XmlDocument().to_parent(None, DateTime(format=format), n, element, ns_test)
        element = element[0]

        assert element.text == n.strftime(format.encode('utf8')).decode('utf8')
        dt = XmlDocument().from_element(None, DateTime(format=format), element)
        assert n == dt

    def test_date_format(self):
        t = datetime.date.today()
        format = "%Y %m %d"

        element = etree.Element('test')
        XmlDocument().to_parent(None, Date(format=format), t, element, ns_test)
        assert element[0].text == datetime.date.strftime(t, format)

        dt = XmlDocument().from_element(None, Date(format=format), element[0])
        assert t == dt

    def test_datetime_timezone(self):
        import pytz

        n = datetime.datetime.now(pytz.timezone('EST'))
        element = etree.Element('test')
        cls = DateTime(as_timezone=pytz.utc, timezone=False)
        XmlDocument().to_parent(None, cls, n, element, ns_test)
        element = element[0]

        c = n.astimezone(pytz.utc).replace(tzinfo=None)
        self.assertEquals(element.text, c.isoformat())
        dt = XmlDocument().from_element(None, cls, element)
        assert dt.tzinfo is not None
        dt = dt.replace(tzinfo=None)
        self.assertEquals(c, dt)

    def test_date_timezone(self):
        elt = etree.Element('wot')
        elt.text = '2013-08-09+02:00'
        dt = XmlDocument().from_element(None, Date, elt)
        print("ok without validation.")
        dt = XmlDocument(validator='soft').from_element(None, Date, elt)
        print(dt)

    def test_time(self):
        n = datetime.time(1, 2, 3, 4)

        ret = ProtocolBase().to_string(Time, n)
        self.assertEquals(ret, n.isoformat())

        dt = ProtocolBase().from_string(Time, ret)
        self.assertEquals(n, dt)

    def test_time_usec(self):
        # python's datetime and time only accept ints between [0, 1e6[
        # if the incoming data is 999999.8 microseconds, rounding it up means
        # adding 1 second to time. For many reasons, we want to avoid that. (see
        # http://bugs.python.org/issue1487389) That's why 999999.8 usec is
        # rounded to 999999.

        # rounding 0.1 µsec down
        t = ProtocolBase().from_string(Time, "12:12:12.0000001")
        self.assertEquals(datetime.time(12, 12, 12), t)

        # rounding 0.5 µsec up
        t = ProtocolBase().from_string(Time, "12:12:12.0000005")
        self.assertEquals(datetime.time(12, 12, 12, 1), t)

        # rounding 999998.8 µsec up
        t = ProtocolBase().from_string(Time, "12:12:12.9999988")
        self.assertEquals(datetime.time(12, 12, 12, 999999), t)

        # rounding 999999.1 µsec down
        t = ProtocolBase().from_string(Time, "12:12:12.9999991")
        self.assertEquals(datetime.time(12, 12, 12, 999999), t)

        # rounding 999999.8 µsec down, not up.
        t = ProtocolBase().from_string(Time, "12:12:12.9999998")
        self.assertEquals(datetime.time(12, 12, 12, 999999), t)

    def test_date(self):
        n = datetime.date(2011,12,13)

        ret = ProtocolBase().to_string(Date, n)
        self.assertEquals(ret, n.isoformat())

        dt = ProtocolBase().from_string(Date, ret)
        self.assertEquals(n, dt)

    def test_utcdatetime(self):
        datestring = '2007-05-15T13:40:44Z'
        e = etree.Element('test')
        e.text = datestring

        dt = XmlDocument().from_element(None, DateTime, e)

        self.assertEquals(dt.year, 2007)
        self.assertEquals(dt.month, 5)
        self.assertEquals(dt.day, 15)

        datestring = '2007-05-15T13:40:44.003Z'
        e = etree.Element('test')
        e.text = datestring

        dt = XmlDocument().from_element(None, DateTime, e)

        self.assertEquals(dt.year, 2007)
        self.assertEquals(dt.month, 5)
        self.assertEquals(dt.day, 15)

    def test_date_exclusive_boundaries(self):
        test_model = Date.customize(gt=datetime.date(2016, 1, 1), lt=datetime.date(2016, 2, 1))
        self.assertFalse(test_model.validate_native(test_model, datetime.date(2016, 1, 1)))
        self.assertFalse(test_model.validate_native(test_model, datetime.date(2016, 2, 1)))

    def test_date_inclusive_boundaries(self):
        test_model = Date.customize(ge=datetime.date(2016, 1, 1), le=datetime.date(2016, 2, 1))
        self.assertTrue(test_model.validate_native(test_model, datetime.date(2016, 1, 1)))
        self.assertTrue(test_model.validate_native(test_model, datetime.date(2016, 2, 1)))

    def test_datetime_exclusive_boundaries(self):
        test_model = DateTime.customize(
            gt=datetime.datetime(2016, 1, 1, 12, 00).replace(tzinfo=spyne.LOCAL_TZ),
            lt=datetime.datetime(2016, 2, 1, 12, 00).replace(tzinfo=spyne.LOCAL_TZ))
        self.assertFalse(test_model.validate_native(test_model,
                                                    datetime.datetime(2016, 1, 1, 12, 00)))
        self.assertFalse(test_model.validate_native(test_model,
                                                    datetime.datetime(2016, 2, 1, 12, 00)))

    def test_datetime_inclusive_boundaries(self):
        test_model = DateTime.customize(
            ge=datetime.datetime(2016, 1, 1, 12, 00).replace(tzinfo=spyne.LOCAL_TZ),
            le=datetime.datetime(2016, 2, 1, 12, 00).replace(tzinfo=spyne.LOCAL_TZ))
        self.assertTrue(test_model.validate_native(test_model,
                                                   datetime.datetime(2016, 1, 1, 12, 00)))
        self.assertTrue(test_model.validate_native(test_model,
                                                   datetime.datetime(2016, 2, 1, 12, 00)))

    def test_time_exclusive_boundaries(self):
        test_model = Time.customize(gt=datetime.time(12, 00),
                                    lt=datetime.time(13, 00))
        self.assertFalse(test_model.validate_native(test_model, datetime.time(12, 00)))
        self.assertFalse(test_model.validate_native(test_model, datetime.time(13, 00)))

    def test_time_inclusive_boundaries(self):
        test_model = Time.customize(ge=datetime.time(12, 00),
                                    le=datetime.time(13, 00))
        self.assertTrue(test_model.validate_native(test_model, datetime.time(12, 00)))
        self.assertTrue(test_model.validate_native(test_model, datetime.time(13, 00)))

    def test_datetime_extreme_boundary(self):
        self.assertTrue(DateTime.validate_native(DateTime, datetime.datetime.min))
        self.assertTrue(DateTime.validate_native(DateTime, datetime.datetime.max))

    def test_time_extreme_boundary(self):
        self.assertTrue(Time.validate_native(Time, datetime.time(0,0,0,0)))
        self.assertTrue(Time.validate_native(Time, datetime.time(23, 59, 59, 999999)))

    def test_date_extreme_boundary(self):
        self.assertTrue(Date.validate_native(Date, datetime.date.min))
        self.assertTrue(Date.validate_native(Date, datetime.date.max))

    def test_integer(self):
        i = 12
        integer = Integer()

        element = etree.Element('test')
        XmlDocument().to_parent(None, Integer, i, element, ns_test)
        element = element[0]

        self.assertEquals(element.text, '12')
        value = XmlDocument().from_element(None, integer, element)
        self.assertEquals(value, i)

    def test_limits(self):
        try:
            ProtocolBase().from_string(Integer, "1" * (Integer.__max_str_len__ + 1))
        except:
            pass
        else:
            raise Exception("must fail.")

        ProtocolBase().from_string(UnsignedInteger, "-1") # This is not supposed to fail.

        try:
            UnsignedInteger.validate_native(-1)  # This is supposed to fail.
        except:
            pass
        else:
            raise Exception("must fail.")

    def test_large_integer(self):
        i = 128375873458473
        integer = Integer()

        element = etree.Element('test')
        XmlDocument().to_parent(None, Integer, i, element, ns_test)
        element = element[0]

        self.assertEquals(element.text, '128375873458473')
        value = XmlDocument().from_element(None, integer, element)
        self.assertEquals(value, i)

    def test_float(self):
        f = 1.22255645

        element = etree.Element('test')
        XmlDocument().to_parent(None, Float, f, element, ns_test)
        element = element[0]

        self.assertEquals(element.text, repr(f))

        f2 = XmlDocument().from_element(None, Float, element)
        self.assertEquals(f2, f)

    def test_array(self):
        type = Array(String)
        type.resolve_namespace(type, "zbank")

        values = ['a', 'b', 'c', 'd', 'e', 'f']

        element = etree.Element('test')
        XmlDocument().to_parent(None, type, values, element, ns_test)
        element = element[0]

        self.assertEquals(len(values), len(element.getchildren()))

        values2 = XmlDocument().from_element(None, type, element)
        self.assertEquals(values[3], values2[3])

    def test_array_empty(self):
        type = Array(String)
        type.resolve_namespace(type, "zbank")

        values = []

        element = etree.Element('test')
        XmlDocument().to_parent(None, type, values, element, ns_test)
        element = element[0]

        self.assertEquals(len(values), len(element.getchildren()))

        values2 = XmlDocument().from_element(None, type, element)
        self.assertEquals(len(values2), 0)

    def test_unicode(self):
        s = u'\x34\x55\x65\x34'
        self.assertEquals(4, len(s))
        element = etree.Element('test')
        XmlDocument().to_parent(None, String, s, element, 'test_ns')
        element = element[0]
        value = XmlDocument().from_element(None, String, element)
        self.assertEquals(value, s)

    def test_unicode_pattern_mult_cust(self):
        assert Unicode(pattern='a').Attributes.pattern == 'a'
        assert Unicode(pattern='a')(5).Attributes.pattern == 'a'

    def test_unicode_upattern(self):
        patt = r'[\w .-]+'
        attr = Unicode(unicode_pattern=patt).Attributes
        assert attr.pattern == patt
        assert attr._pattern_re.flags & re.UNICODE
        assert attr._pattern_re.match(u"Ğ Ğ ç .-")
        assert attr._pattern_re.match(u"\t") is None

    def test_unicode_nullable_mult_cust_false(self):
        assert Unicode(nullable=False).Attributes.nullable == False
        assert Unicode(nullable=False)(5).Attributes.nullable == False

    def test_unicode_nullable_mult_cust_true(self):
        assert Unicode(nullable=True).Attributes.nullable == True
        assert Unicode(nullable=True)(5).Attributes.nullable == True

    def test_null(self):
        element = etree.Element('test')
        XmlDocument().to_parent(None, Null, None, element, ns_test)
        print(etree.tostring(element))

        element = element[0]
        self.assertTrue( bool(element.attrib.get('{%s}nil' % ns.xsi)) )
        value = XmlDocument().from_element(None, Null, element)
        self.assertEquals(None, value)

    def test_point(self):
        from spyne.model.primitive.spatial import _get_point_pattern

        a=re.compile(_get_point_pattern(2))
        assert a.match('POINT (10 40)') is not None
        assert a.match('POINT(10 40)') is not None

        assert a.match('POINT(10.0 40)') is not None
        assert a.match('POINT(1.310e4 40)') is not None

    def test_multipoint(self):
        from spyne.model.primitive.spatial import _get_multipoint_pattern

        a=re.compile(_get_multipoint_pattern(2))
        assert a.match('MULTIPOINT (10 40, 40 30, 20 20, 30 10)') is not None
        # FIXME:
        #assert a.match('MULTIPOINT ((10 40), (40 30), (20 20), (30 10))') is not None

    def test_linestring(self):
        from spyne.model.primitive.spatial import _get_linestring_pattern

        a=re.compile(_get_linestring_pattern(2))
        assert a.match('LINESTRING (30 10, 10 30, 40 40)') is not None

    def test_multilinestring(self):
        from spyne.model.primitive.spatial import _get_multilinestring_pattern

        a=re.compile(_get_multilinestring_pattern(2))
        assert a.match('''MULTILINESTRING ((10 10, 20 20, 10 40),
                                (40 40, 30 30, 40 20, 30 10))''') is not None

    def test_polygon(self):
        from spyne.model.primitive.spatial import _get_polygon_pattern

        a=re.compile(_get_polygon_pattern(2))
        assert a.match('POLYGON ((30 10, 10 20, 20 40, 40 40, 30 10))') is not None

    def test_multipolygon(self):
        from spyne.model.primitive.spatial import _get_multipolygon_pattern

        a=re.compile(_get_multipolygon_pattern(2))
        assert a.match('''MULTIPOLYGON (((30 20, 10 40, 45 40, 30 20)),
                            ((15 5, 40 10, 10 20, 5 10, 15 5)))''') is not None
        assert a.match('''MULTIPOLYGON (((40 40, 20 45, 45 30, 40 40)),
                                ((20 35, 45 20, 30 5, 10 10, 10 30, 20 35),
                                (30 20, 20 25, 20 15, 30 20)))''') is not None

    def test_boolean(self):
        b = etree.Element('test')
        XmlDocument().to_parent(None, Boolean, True, b, ns_test)
        b = b[0]
        self.assertEquals('true', b.text)

        b = etree.Element('test')
        XmlDocument().to_parent(None, Boolean, 0, b, ns_test)
        b = b[0]
        self.assertEquals('false', b.text)

        b = etree.Element('test')
        XmlDocument().to_parent(None, Boolean, 1, b, ns_test)
        b = b[0]
        self.assertEquals('true', b.text)

        b = XmlDocument().from_element(None, Boolean, b)
        self.assertEquals(b, True)

        b = etree.Element('test')
        XmlDocument().to_parent(None, Boolean, False, b, ns_test)
        b = b[0]
        self.assertEquals('false', b.text)

        b = XmlDocument().from_element(None, Boolean, b)
        self.assertEquals(b, False)

        b = etree.Element('test')
        XmlDocument().to_parent(None, Boolean, None, b, ns_test)
        b = b[0]
        self.assertEquals('true', b.get('{%s}nil' % ns.xsi))

        b = XmlDocument().from_element(None, Boolean, b)
        self.assertEquals(b, None)

    def test_new_type(self):
        """Customized primitives go into namespace based on module name."""
        custom_type = Unicode(pattern='123')
        self.assertEqual(custom_type.get_namespace(), custom_type.__module__)

    def test_default_nullable(self):
        """Test if default nullable changes nullable attribute."""
        try:
            self.assertTrue(Unicode.Attributes.nullable)
            orig_default = Unicode.Attributes.NULLABLE_DEFAULT
            Unicode.Attributes.NULLABLE_DEFAULT = False
            self.assertFalse(Unicode.Attributes.nullable)
            self.assertFalse(Unicode.Attributes.nillable)
        finally:
            Unicode.Attributes.NULLABLE_DEFAULT = orig_default
            self.assertEqual(Unicode.Attributes.nullable, orig_default)

    def test_simple_type_explicit_customization(self):
        assert Unicode(max_len=5).__extends__ is not None
        assert Unicode.customize(max_len=5).__extends__ is not None

    def test_anydict_customization(self):
        from spyne.model import json
        assert isinstance(AnyDict.customize(store_as='json').Attributes.store_as, json)

    def test_uuid_serialize(self):
        value = uuid.UUID('12345678123456781234567812345678')

        assert ProtocolBase().to_string(Uuid, value) == \
                                '12345678-1234-5678-1234-567812345678'
        assert ProtocolBase().to_string(Uuid(serialize_as='hex'), value) == \
                                '12345678123456781234567812345678'
        assert ProtocolBase().to_string(Uuid(serialize_as='urn'), value) == \
                                'urn:uuid:12345678-1234-5678-1234-567812345678'
        assert ProtocolBase().to_string(Uuid(serialize_as='bytes'), value) == \
                                '\x124Vx\x124Vx\x124Vx\x124Vx'
        assert ProtocolBase().to_string(Uuid(serialize_as='bytes_le'), value) == \
                                'xV4\x124\x12xV\x124Vx\x124Vx'
        assert ProtocolBase().to_string(Uuid(serialize_as='fields'), value) == \
                                (305419896, 4660, 22136, 18, 52, 95073701484152)
        assert ProtocolBase().to_string(Uuid(serialize_as='int'), value) == \
                                24197857161011715162171839636988778104

    def test_uuid_deserialize(self):
        value = uuid.UUID('12345678123456781234567812345678')

        assert ProtocolBase().from_string(Uuid,
                '12345678-1234-5678-1234-567812345678') == value
        assert ProtocolBase().from_string(Uuid(serialize_as='hex'),
                '12345678123456781234567812345678') == value
        assert ProtocolBase().from_string(Uuid(serialize_as='urn'),
                'urn:uuid:12345678-1234-5678-1234-567812345678') == value
        assert ProtocolBase().from_string(Uuid(serialize_as='bytes'),
                '\x124Vx\x124Vx\x124Vx\x124Vx') == value
        assert ProtocolBase().from_string(Uuid(serialize_as='bytes_le'),
                'xV4\x124\x12xV\x124Vx\x124Vx') == value
        assert ProtocolBase().from_string(Uuid(serialize_as='fields'),
                (305419896, 4660, 22136, 18, 52, 95073701484152)) == value
        assert ProtocolBase().from_string(Uuid(serialize_as='int'),
                24197857161011715162171839636988778104) == value

    def test_uuid_validate(self):
        assert Uuid.validate_string(Uuid,
                          '12345678-1234-5678-1234-567812345678')
        assert Uuid.validate_native(Uuid,
                uuid.UUID('12345678-1234-5678-1234-567812345678'))

    def test_datetime_serialize_as(self):
        i = 1234567890123456
        v = datetime.datetime.fromtimestamp(i / 1e6)

        assert ProtocolBase().to_string(
                            DateTime(serialize_as='sec'), v) == i//1e6
        assert ProtocolBase().to_string(
                            DateTime(serialize_as='sec_float'), v) == i/1e6
        assert ProtocolBase().to_string(
                            DateTime(serialize_as='msec'), v) == i//1e3
        assert ProtocolBase().to_string(
                            DateTime(serialize_as='msec_float'), v) == i/1e3
        assert ProtocolBase().to_string(
                            DateTime(serialize_as='usec'), v) == i

    def test_datetime_deserialize(self):
        i = 1234567890123456
        v = datetime.datetime.fromtimestamp(i / 1e6)

        assert ProtocolBase().from_string(
                    DateTime(serialize_as='sec'), i//1e6) == \
                                     datetime.datetime.fromtimestamp(i//1e6)
        assert ProtocolBase().from_string(
                    DateTime(serialize_as='sec_float'), i/1e6) == v

        assert ProtocolBase().from_string(
                    DateTime(serialize_as='msec'), i//1e3) == \
                                    datetime.datetime.fromtimestamp(i/1e3//1000)
        assert ProtocolBase().from_string(
                    DateTime(serialize_as='msec_float'), i/1e3) == v

        assert ProtocolBase().from_string(
                    DateTime(serialize_as='usec'), i) == v

    def test_datetime_usec(self):
        # see the comments on time test for why the rounding here is weird

        # rounding 0.1 µsec down
        dt = ProtocolBase().from_string(DateTime, "2015-01-01 12:12:12.0000001")
        self.assertEquals(datetime.datetime(2015, 1, 1, 12, 12, 12), dt)

        # rounding 0.5 µsec up
        dt = ProtocolBase().from_string(DateTime, "2015-01-01 12:12:12.0000005")
        self.assertEquals(datetime.datetime(2015, 1, 1, 12, 12, 12, 1), dt)

        # rounding 999998.8 µsec up
        dt = ProtocolBase().from_string(DateTime, "2015-01-01 12:12:12.9999988")
        self.assertEquals(datetime.datetime(2015, 1, 1, 12, 12, 12, 999999), dt)

        # rounding 999999.1 µsec down
        dt = ProtocolBase().from_string(DateTime, "2015-01-01 12:12:12.9999991")
        self.assertEquals(datetime.datetime(2015, 1, 1, 12, 12, 12, 999999), dt)

        # rounding 999999.8 µsec down, not up.
        dt = ProtocolBase().from_string(DateTime, "2015-01-01 12:12:12.9999998")
        self.assertEquals(datetime.datetime(2015, 1, 1, 12, 12, 12, 999999), dt)

### Duration Data Type
## http://www.w3schools.com/schema/schema_dtypes_date.asp
# Duration Data type
#  The time interval is specified in the following form "PnYnMnDTnHnMnS" where:
# P indicates the period (required)
# nY indicates the number of years
# nM indicates the number of months
# nD indicates the number of days
# T indicates the start of a time section (*required* if you are going to
#                               specify hours, minutes, seconds or microseconds)
# nH indicates the number of hours
# nM indicates the number of minutes
# nS indicates the number of seconds

class SomeBlob(ComplexModel):
    __namespace__ = 'myns'
    howlong = Duration()

class TestDurationPrimitive(unittest.TestCase):
    def test_onehour_oneminute_onesecond(self):
        answer = 'PT1H1M1S'
        gg = SomeBlob()
        gg.howlong = timedelta(hours=1, minutes=1, seconds=1)

        element = etree.Element('test')
        XmlDocument().to_parent(None, SomeBlob, gg, element, gg.get_namespace())
        element = element[0]

        print(gg.howlong)
        print(etree.tostring(element, pretty_print=True))
        assert element[0].text == answer

        data = element.find('{%s}howlong' % gg.get_namespace()).text
        self.assertEquals(data, answer)
        s1 = XmlDocument().from_element(None, SomeBlob, element)
        assert total_seconds(s1.howlong) == total_seconds(gg.howlong)

    def test_4suite(self):
        # borrowed from 4Suite
        tests_seconds =  [
            (0, u'PT0S'),
            (1, u'PT1S'),
            (59, u'PT59S'),
            (60, u'PT1M'),
            (3599, u'PT59M59S'),
            (3600, u'PT1H'),
            (86399, u'PT23H59M59S'),
            (86400, u'P1D'),
            (86400*60, u'P60D'),
            (86400*400, u'P400D')
        ]

        for secs, answer in tests_seconds:
            gg = SomeBlob()
            gg.howlong = timedelta(seconds=secs)

            element = etree.Element('test')
            XmlDocument().to_parent(None, SomeBlob, gg, element, gg.get_namespace())
            element = element[0]

            print(gg.howlong)
            print(etree.tostring(element, pretty_print=True))
            assert element[0].text == answer

            data = element.find('{%s}howlong' % gg.get_namespace()).text
            self.assertEquals(data, answer)
            s1 = XmlDocument().from_element(None, SomeBlob, element)
            assert total_seconds(s1.howlong) == secs

        for secs, answer in tests_seconds:
            if secs > 0:
                secs *= -1
                answer = '-' + answer
                gg = SomeBlob()
                gg.howlong = timedelta(seconds=secs)

                element = etree.Element('test')
                XmlDocument().to_parent(None, SomeBlob, gg, element, gg.get_namespace())
                element = element[0]

                print(gg.howlong)
                print(etree.tostring(element, pretty_print=True))
                assert element[0].text == answer

                data = element.find('{%s}howlong' % gg.get_namespace()).text
                self.assertEquals(data, answer)
                s1 = XmlDocument().from_element(None, SomeBlob, element)
                assert total_seconds(s1.howlong) == secs

    def test_duration_positive_seconds_only(self):
        answer = 'PT35S'
        gg = SomeBlob()
        gg.howlong = timedelta(seconds=35)

        element = etree.Element('test')
        XmlDocument().to_parent(None, SomeBlob, gg, element, gg.get_namespace())
        element = element[0]

        print(gg.howlong)
        print(etree.tostring(element, pretty_print=True))
        assert element[0].text == answer

        data = element.find('{%s}howlong' % gg.get_namespace()).text
        self.assertEquals(data, answer)
        s1 = XmlDocument().from_element(None, SomeBlob, element)
        assert total_seconds(s1.howlong) == total_seconds(gg.howlong)

    def test_duration_positive_minutes_and_seconds_only(self):
        answer = 'PT5M35S'
        gg = SomeBlob()
        gg.howlong = timedelta(minutes=5, seconds=35)

        element = etree.Element('test')
        XmlDocument().to_parent(None, SomeBlob, gg, element, gg.get_namespace())
        element = element[0]

        print(gg.howlong)
        print(etree.tostring(element, pretty_print=True))
        assert element[0].text == answer

        data = element.find('{%s}howlong' % gg.get_namespace()).text
        self.assertEquals(data, answer)
        s1 = XmlDocument().from_element(None, SomeBlob, element)
        assert total_seconds(s1.howlong) == total_seconds(gg.howlong)

    def test_duration_positive_milliseconds_only(self):
        answer = 'PT0.666000S'
        gg = SomeBlob()
        gg.howlong = timedelta(milliseconds=666)

        element = etree.Element('test')
        XmlDocument().to_parent(None, SomeBlob, gg, element, gg.get_namespace())
        element = element[0]

        print(gg.howlong)
        print(etree.tostring(element, pretty_print=True))
        assert element[0].text == answer

        data = element.find('{%s}howlong' % gg.get_namespace()).text
        self.assertEquals(data, answer)
        s1 = XmlDocument().from_element(None, SomeBlob, element)
        assert total_seconds(s1.howlong) == total_seconds(gg.howlong)

    def test_duration_xml_duration(self):
        dur = datetime.timedelta(days=5 + 30 + 365, hours=1, minutes=1,
                                                   seconds=12, microseconds=8e5)

        str1 = 'P400DT3672.8S'
        str2 = 'P1Y1M5DT1H1M12.8S'

        self.assertEquals(dur, ProtocolBase().from_string(Duration, str1))
        self.assertEquals(dur, ProtocolBase().from_string(Duration, str2))

        self.assertEquals(dur, ProtocolBase().from_string(Duration,
                               ProtocolBase().to_string(Duration, dur)))


if __name__ == '__main__':
    unittest.main()
