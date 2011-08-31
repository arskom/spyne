
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

import re
import math
import pytz
import decimal

import rpclib.const.xml_ns
import cPickle as pickle

from collections import deque

from datetime import date
from datetime import datetime
from datetime import timedelta

from lxml import etree
from pytz import FixedOffset

from rpclib.model import SimpleModel
from rpclib.model import nillable_string

string_encoding = 'utf8'

_date_pattern = r'(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})'
_time_pattern = r'(?P<hr>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})(?P<sec_frac>\.\d+)?'
_offset_pattern = r'(?P<tz_hr>[+-]\d{2}):(?P<tz_min>\d{2})'
_datetime_pattern = _date_pattern + '[T ]' + _time_pattern

_local_re = re.compile(_datetime_pattern)
_utc_re = re.compile(_datetime_pattern + 'Z')
_offset_re = re.compile(_datetime_pattern + _offset_pattern)
_date_re = re.compile(_date_pattern)
_duration_re = re.compile(
        r'(?P<sign>-?)'
        r'P'
        r'(?:(?P<years>\d+)Y)?'
        r'(?:(?P<months>\d+)M)?'
        r'(?:(?P<days>\d+)D)?'
        r'(?:T(?:(?P<hours>\d+)H)?'
        r'(?:(?P<minutes>\d+)M)?'
        r'(?:(?P<seconds>\d+(.\d+)?)S)?)?'
    )

_ns_xs = rpclib.const.xml_ns.xsd
_ns_xsi = rpclib.const.xml_ns.xsi

class AnyXml(SimpleModel):
    __type_name__ = 'anyType'

    @classmethod
    @nillable_string
    def to_string(cls, value):
        return etree.tostring(value)

    @classmethod
    @nillable_string
    def from_string(cls, string):
        return etree.fromstring(string)

class AnyDict(SimpleModel):
    __type_name__ = 'anyType'

    @classmethod
    @nillable_string
    def to_string(cls, value):
        return pickle.dumps(value)

    @classmethod
    @nillable_string
    def from_string(cls, string):
        return pickle.loads(string)

class String(SimpleModel):
    __type_name__ = 'string'

    class Attributes(SimpleModel.Attributes):
        min_len = 0
        max_len = "unbounded"
        pattern = None

    def __new__(cls, *args, **kwargs):
        assert len(args) <= 1

        if len(args) == 1:
            kwargs['max_len'] = args[0]

        retval = SimpleModel.__new__(cls,  ** kwargs)

        return retval

    @classmethod
    @nillable_string
    def from_string(cls, value):
        return value

    @staticmethod
    def is_default(cls):
        return (    SimpleModel.is_default(cls)
                and cls.Attributes.min_len == String.Attributes.min_len
                and cls.Attributes.max_len == String.Attributes.max_len
                and cls.Attributes.pattern == String.Attributes.pattern)

class AnyUri(String):
    __type_name__ = 'anyURI'

class Decimal(SimpleModel):
    __type_name__ = 'decimal'

    class Attributes(SimpleModel.Attributes):
        gt = None # minExclusive
        ge = None # minInclusive
        lt = None # maxExclusive
        le = None # maxInclusive

    @staticmethod
    def is_default(cls):
        return (    SimpleModel.is_default(cls)
                and cls.Attributes.gt == Decimal.Attributes.gt
                and cls.Attributes.ge == Decimal.Attributes.ge
                and cls.Attributes.lt == Decimal.Attributes.lt
                and cls.Attributes.le == Decimal.Attributes.le)

    @classmethod
    @nillable_string
    def to_string(cls, value):
        decimal.Decimal(value)

        return str(value)

    @classmethod
    @nillable_string
    def from_string(cls, string):
        return decimal.Decimal(string)

class Int(Decimal):
    __type_name__ = 'int'

    @classmethod
    @nillable_string
    def to_string(cls, value):
        int(value)
        return str(value)

    @classmethod
    @nillable_string
    def from_string(cls, string):
        return int(string)

class Integer(Decimal):
    __type_name__ = 'integer'

    @classmethod
    @nillable_string
    def to_string(cls, value):
        try:
            int(value)
        except:
            long(value)

        return str(value)

    @classmethod
    @nillable_string
    def from_string(cls, string):
        try:
            return int(string)
        except:
            return long(string)

class UnsignedInteger(Integer):
    __type_name__ = 'unsignedLong'
    __length__ = None
    @classmethod
    @nillable_string
    def to_string(cls, value):
        assert (cls.__length__ is None) or (0 <= value < 2**cls.__length__)

        return str(value)

    @classmethod
    @nillable_string
    def from_string(cls, string):
        try:
            retval = int(string)
        except:
            retval = long(string)

        assert (cls.__length__ is None) or (0 <= retval < 2**cls.__length__)

        return retval

class UnsignedInteger64(UnsignedInteger):
    __type_name__ = 'unsignedLong'
    __length__ = 64

class UnsignedInteger32(UnsignedInteger):
    __type_name__ = 'unsignedLong'
    __length__ = 32

class UnsignedInteger16(Integer):
    __type_name__ = 'unsignedShort'
    __length__ = 16

class UnsignedInteger8(Integer):
    __type_name__ = 'unsignedByte'
    __length__ = 8

class Date(SimpleModel):
    __type_name__ = 'date'

    @classmethod
    @nillable_string
    def to_string(cls, value):
        return value.isoformat()

    @classmethod
    @nillable_string
    def from_string(cls, string):
        """expect ISO formatted dates"""
        def parse_date(date_match):
            fields = date_match.groupdict(0)
            year, month, day = [int(fields[x]) for x in
                ("year", "month", "day")]
            return date(year, month, day)

        match = _date_re.match(string)
        if not match:
            raise Exception("Date [%s] not in known format" % string)

        return parse_date(match)

class DateTime(SimpleModel):
    __type_name__ = 'dateTime'

    @classmethod
    @nillable_string
    def to_string(cls, value):
        return value.isoformat('T')

    @classmethod
    @nillable_string
    def from_string(cls, string):
        """expect ISO formatted dates"""
        def parse_date(date_match, tz=None):
            fields = date_match.groupdict(0)
            year, month, day, hour, min, sec = [int(fields[x]) for x in
                ("year", "month", "day", "hr", "min", "sec")]

            # use of decimal module here (rather than float) might be better
            # here, if willing to require python 2.4 or higher
            microsec = int(float(fields.get("sec_frac", 0)) * 10 ** 6)

            return datetime(year,month,day, hour,min,sec, microsec, tz)

        match = _utc_re.match(string)
        if match:
            return parse_date(match, tz=pytz.utc)

        match = _offset_re.match(string)
        if match:
            tz_hr, tz_min = [int(match.group(x)) for x in "tz_hr", "tz_min"]
            return parse_date(match, tz=FixedOffset(tz_hr * 60 + tz_min, {}))

        match = _local_re.match(string)
        if not match:
            raise Exception("DateTime [%s] not in known format" % string)

        return parse_date(match)

# this object tries to follow ISO 8601 standard.
class Duration(SimpleModel):
    __type_name__ = 'duration'

    @classmethod
    @nillable_string
    def from_string(cls, string):
        duration = _duration_re.match(string).groupdict(0)

        days = int(duration['days'])
        days += int(duration['months']) * 30
        days += int(duration['years']) * 365
        hours = int(duration['hours'])
        minutes = int(duration['minutes'])
        seconds = float(duration['seconds'])
        f,i = math.modf(seconds)
        seconds = i
        microseconds = int(1e6 * f)

        delta = timedelta(days=days, hours=hours, minutes=minutes,
                                    seconds=seconds, microseconds=microseconds)

        if duration['sign'] == "-":
            delta *= -1

        return delta

    @classmethod
    def to_string(cls, value):
        if value.days < 0:
            value = -value
            negative = True
        else:
            negative = False

        seconds = value.seconds % 60
        minutes = value.seconds / 60
        hours = minutes / 60
        minutes = minutes % 60
        seconds = float(seconds) + value.microseconds / 1e6

        retval = deque()
        if negative:
            retval.append("-")

        retval = ['P']
        if value.days > 0:
            retval.extend([
                    "%iD" % value.days,
                ])

        if hours > 0 and minutes > 0 and seconds > 0:
            retval.extend([
                    "T",
                    "%iH" % hours,
                    "%iM" % minutes,
                    "%fS" % seconds,
                ])

        else:
            retval.extend([
                    "0S",
                ])

        return ''.join(retval)

class Double(SimpleModel):
    __type_name__ = 'double'

    @classmethod
    @nillable_string
    def to_string(cls, value):
        return repr(value)

    @classmethod
    @nillable_string
    def from_string(cls, string):
        return float(string)

class Float(Double):
    __type_name__ = 'float'

class Boolean(SimpleModel):
    __type_name__ = 'boolean'

    @classmethod
    @nillable_string
    def to_string(cls, value):
        return str(bool(value)).lower()

    @classmethod
    @nillable_string
    def from_string(cls, string):
        return (string.lower() in ['true', '1'])

# a class that is really a namespace
class Mandatory(object):
    String = String(min_occurs=1, nillable=False, min_len=1)
    Integer = Integer(min_occurs=1, nillable=False)
