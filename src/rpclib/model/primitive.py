
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

"""This module defines primitives that are atomic, basic types."""

import sys
if sys.version > '3':
    long = int

import re
import math
import pytz
import decimal
import datetime

import rpclib.const.xml_ns
import pickle

from collections import deque

from lxml import etree
from pytz import FixedOffset

from rpclib.model import SimpleModel
from rpclib.model import nillable_string
from rpclib.error import ValidationError
from rpclib.error import Fault

string_encoding = 'utf8'

_date_pattern = r'(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})'
_time_pattern = r'(?P<hr>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})(?P<sec_frac>\.\d+)?'
_offset_pattern = r'(?P<tz_hr>[+-]\d{2}):(?P<tz_min>\d{2})'
_datetime_pattern = _date_pattern + '[T ]' + _time_pattern

_local_re = re.compile(_datetime_pattern)
_utc_re = re.compile(_datetime_pattern + 'Z')
_offset_re = re.compile(_datetime_pattern + _offset_pattern)
_date_re = re.compile(_date_pattern)
_time_re = re.compile(_time_pattern)
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
    """An xml node that can contain any number of sub nodes. It's represented by
    an ElementTree object."""

    __type_name__ = 'anyType'

    @classmethod
    @nillable_string
    def to_string(cls, value):
        return etree.tostring(value)

    @classmethod
    @nillable_string
    def from_string(cls, string):
        try:
            return etree.fromstring(string)
        except etree.XMLSyntaxError:
            raise ValidationError(string)

class AnyDict(SimpleModel):
    """An xml node that can contain any number of sub nodes. It's represented by
    a dict instance that can contain other dicts or iterables of strings as
    values.
    """

    __type_name__ = 'anyType'

    @classmethod
    @nillable_string
    def to_string(cls, value):
        return pickle.dumps(value)

    @classmethod
    @nillable_string
    def from_string(cls, string):
        try:
            return pickle.loads(string)
        except:
            raise ValidationError(string)

class Unicode(SimpleModel):
    """The type to represent human-readable data. Its native format is `unicode`.
    or `str` with given encoding.
    """

    __type_name__ = 'string'

    class Attributes(SimpleModel.Attributes):
        """Customizable attributes of the :class:`rpclib.model.primitive.Unicode`
        type."""

        min_len = 0
        """Minimum length of string. Can be set to any positive integer"""

        max_len = "unbounded"
        """Maximum length of string. Can be set to 'unbounded' to accept strings
        of arbitrary sizes. Also check :const:`rpclib.server.wsgi.MAX_CONTENT_LENGTH`."""

        pattern = None
        """A regular expression that matches the whole string. See here for more
        info: http://www.regular-expressions.info/xml.html"""

        encoding = None
        """The encoding of `str` objects this class may have to deal with."""

        unicode_errors = 'strict'
        """The argument to the ``unicode`` builtin; one of 'strict', 'replace' or
        'ignore'."""

    def __new__(cls, *args, **kwargs):
        assert len(args) <= 1

        if len(args) == 1:
            kwargs['max_len'] = args[0]

        retval = SimpleModel.__new__(cls,  ** kwargs)

        return retval

    @classmethod
    @nillable_string
    def from_string(cls, value):
        retval = value
        if isinstance(value, str):
            if cls.Attributes.encoding is None:
                retval = unicode(value, errors=cls.Attributes.unicode_errors)
            else:
                retval = unicode(value, cls.Attributes.encoding,
                                        errors=cls.Attributes.unicode_errors)
        return retval

    @classmethod
    @nillable_string
    def to_string(cls, value):
        retval = value
        if cls.Attributes.encoding is not None and isinstance(value, unicode):
            retval = value.encode(cls.Attributes.encoding)
        return retval

    @staticmethod
    def is_default(cls):
        return (    SimpleModel.is_default(cls)
                and cls.Attributes.min_len == Unicode.Attributes.min_len
                and cls.Attributes.max_len == Unicode.Attributes.max_len
                and cls.Attributes.pattern == Unicode.Attributes.pattern)

    @staticmethod
    def validate_string(cls, value):
        return (     SimpleModel.validate_string(cls, value)
                and (value is None or (
                        len(value) >= cls.Attributes.min_len and
                        len(value) <= cls.Attributes.max_len))
                and (cls.Attributes.pattern is None or
                            re.match(cls.Attributes.pattern, value) is not None)
            )


class String(Unicode):
    @classmethod
    @nillable_string
    def from_string(cls, value):
        retval = value
        if isinstance(value, unicode):
            if cls.Attributes.encoding is None:
                raise Exception("You need to define an encoding to convert the "
                                "incoming unicode values to.")
            else:
                retval = value.encode(cls.Attributes.encoding)

        return retval

if sys.version > '3':
    String = Unicode

class AnyUri(Unicode):
    """This is an xml schema type with is a special kind of String."""
    __type_name__ = 'anyURI'

class Decimal(SimpleModel):
    """The primitive that corresponds to the native python Decimal.

    This is also the base class for representing numbers.
    """

    __type_name__ = 'decimal'
    __max_str_len__ = 1024

    class Attributes(SimpleModel.Attributes):
        gt = -float('inf') # minExclusive
        ge = -float('inf') # minInclusive
        lt =  float('inf') # maxExclusive
        le =  float('inf') # maxInclusive

    @staticmethod
    def is_default(cls):
        return (    SimpleModel.is_default(cls)
                and cls.Attributes.gt == Decimal.Attributes.gt
                and cls.Attributes.ge == Decimal.Attributes.ge
                and cls.Attributes.lt == Decimal.Attributes.lt
                and cls.Attributes.le == Decimal.Attributes.le
            )

    @staticmethod
    def validate_native(cls, value):
        return (    SimpleModel.validate_native(cls, value) and
                value is None or (
                    value >  cls.Attributes.gt and
                    value >= cls.Attributes.ge and
                    value <  cls.Attributes.lt and
                    value <= cls.Attributes.le
            ))

    @classmethod
    @nillable_string
    def to_string(cls, value):
        decimal.Decimal(value)

        return str(value)

    @classmethod
    @nillable_string
    def from_string(cls, string):
        if cls.__max_str_len__ is not None and len(string) > cls.__max_str_len__:
            raise ValidationError(string, 'string too long.')

        try:
            return decimal.Decimal(string)
        except decimal.InvalidOperation, e:
            raise ValidationError(string)

class Double(SimpleModel):
    """This is serialized as the python float. So this type comes with its
     gotchas."""

    __type_name__ = 'double'

    @classmethod
    @nillable_string
    def to_string(cls, value):
        return repr(value)

    @classmethod
    @nillable_string
    def from_string(cls, string):
        try:
            return float(string)
        except ValueError:
            raise ValidationError(string)

class Float(Double):
    """Synonym for Double. This is here for compatibility purposes."""

    __type_name__ = 'float'

class Integer(Decimal):
    """The arbitrary-size signed integer."""

    __type_name__ = 'integer'
    __length__ = None
    """length of the number, in bits"""

    @classmethod
    @nillable_string
    def to_string(cls, value):
        assert (cls.__length__ is None) or (0 <= value < 2** cls.__length__)
        int(value) # sanity check

        return str(value)

    @classmethod
    @nillable_string
    def from_string(cls, string):
        if cls.__max_str_len__ is not None and len(string) > cls.__max_str_len__:
            raise Fault('Client.ValidationError', 'String longer than '
                        '%d characters.' % cls.__max_str_len__)

        try:
            return int(string)
        except ValueError:
            try:
                return int(string)
            except ValueError:
                raise ValidationError(string)

    @staticmethod
    def validate_native(cls, value):
        return (     Decimal.validate_native(cls, value)
                and (cls.__length__ is None or
                    (-2**( cls.__length__ -1) <= value < 2 ** (cls.__length__ - 1))
                )
            )

class UnsignedInteger(Integer):
    """The arbitrary-size unsigned integer, aka nonNegativeInteger."""
    __type_name__ = 'nonNegativeInteger'

    @staticmethod
    def validate_native(cls, value):
        return (     Integer.validate_native(cls, value)
                and value >= 0
                and (cls.__length__ is None or (value < 2 ** cls.__length__))
            )

NonNegativeInteger = UnsignedInteger

class Integer64(Integer):
    """The 64-bit signed integer, aka long."""

    __type_name__ = 'long'
    __length__ = 64
    __max_str_len__ = math.ceil(math.log(2**__length__, 10)) + 1

Long = Integer64

class Integer32(Integer):
    """The 32-bit signed integer, aka int."""

    __type_name__ = 'int'
    __length__ = 32
    __max_str_len__ = math.ceil(math.log(2**__length__, 10)) + 1

Int = Integer32

class Integer16(Integer):
    """The 8-bit signed integer, aka short."""

    __type_name__ = 'short'
    __length__ = 16
    __max_str_len__ = math.ceil(math.log(2**__length__, 10)) + 1

Short = Integer64

class Integer8(Integer):
    """The 8-bit signed integer, aka byte."""

    __type_name__ = 'byte'
    __length__ = 16
    __max_str_len__ = math.ceil(math.log(2**__length__, 10)) + 1

Byte = Integer8

class UnsignedInteger64(UnsignedInteger):
    """The 64-bit unsigned integer, aka unsignedLong."""

    __type_name__ = 'unsignedLong'
    __length__ = 64
    __max_str_len__ = math.ceil(math.log(2**__length__, 10)) + 1

UnsignedLong = UnsignedInteger64

class UnsignedInteger32(UnsignedInteger):
    """The 32-bit unsigned integer, aka unsignedInt."""

    __type_name__ = 'unsignedInt'
    __length__ = 32
    __max_str_len__ = math.ceil(math.log(2**__length__, 10)) + 1

UnsignedInt = UnsignedInteger32

class UnsignedInteger16(Integer):
    """The 16-bit unsigned integer, aka unsignedShort."""

    __type_name__ = 'unsignedShort'
    __length__ = 16
    __max_str_len__ = math.ceil(math.log(2**__length__, 10)) + 1

UnsignedShort = UnsignedInteger16

class UnsignedInteger8(Integer):
    """The 8-bit unsigned integer, aka unsignedByte."""

    __type_name__ = 'unsignedByte'
    __length__ = 8
    __max_str_len__ = math.ceil(math.log(2**__length__, 10)) + 1

UnsignedByte = UnsignedInteger8

class Time(SimpleModel):
    """Just that, Time. No time zone support.

    Native type is :class:`datetime.time`.
    """

    __type_name__ = 'time'

    @classmethod
    @nillable_string
    def to_string(cls, value):
        """Returns ISO formatted dates."""

        return value.isoformat()

    @classmethod
    @nillable_string
    def from_string(cls, string):
        """Expects ISO formatted dates."""

        match = _time_re.match(string)
        if match is None:
            raise ValidationError(string)

        fields = match.groupdict(0)

        return datetime.time(int(fields['hr']), int(fields['min']),
                    int(fields['sec']), int(fields.get("sec_frac", '.')[1:]))

class Date(SimpleModel):
    """Just that, Date. It also supports time zones.

    Native type is :class:`datetime.date`.
    """

    __type_name__ = 'date'

    @classmethod
    @nillable_string
    def to_string(cls, value):
        """Returns ISO formatted dates."""

        return value.isoformat()

    @classmethod
    @nillable_string
    def from_string(cls, string):
        """Expects ISO formatted dates."""

        match = _date_re.match(string)
        if match is None:
            raise ValidationError(string)

        fields = match.groupdict(0)

        return datetime.date(int(fields['year']), int(fields['month']), int(fields['day']))

class DateTime(SimpleModel):
    """A compact way to represent dates and times together. Supports time zones.

    Native type is :class:`datetime.datetime`.
    """
    __type_name__ = 'dateTime'

    @classmethod
    @nillable_string
    def to_string(cls, value):
        return value.isoformat('T')

    @staticmethod
    def parse(date_match, tz=None):
        fields = date_match.groupdict()

        year = int(fields.get('year'))
        month =  int(fields.get('month'))
        day = int(fields.get('day'))
        hour = int(fields.get('hr'))
        min = int(fields.get('min'))
        sec = int(fields.get('sec'))
        microsec = fields.get("sec_frac")
        if microsec is None:
            microsec = 0
        else:
            microsec = int(microsec[1:])

        return datetime.datetime(year, month, day, hour, min, sec, microsec, tz)

    @classmethod
    @nillable_string
    def from_string(cls, string):
        """expect ISO formatted dates"""

        match = _utc_re.match(string)
        if match:
            return cls.parse(match, tz=pytz.utc)

        match = _offset_re.match(string)
        if match:
            tz_hr, tz_min = [int(match.group(x)) for x in ("tz_hr", "tz_min")]
            return cls.parse(match, tz=FixedOffset(tz_hr * 60 + tz_min, {}))

        match = _local_re.match(string)
        if match is None:
            raise ValidationError(string)

        return cls.parse(match)

# this object tries to follow ISO 8601 standard.
class Duration(SimpleModel):
    """Native type is :class:`datetime.timedelta`."""

    __type_name__ = 'duration'

    @classmethod
    @nillable_string
    def from_string(cls, string):
        duration = _duration_re.match(string).groupdict(0)
        if duration is None:
            ValidationError(string)

        days = int(duration['days'])
        days += int(duration['months']) * 30
        days += int(duration['years']) * 365
        hours = int(duration['hours'])
        minutes = int(duration['minutes'])
        seconds = float(duration['seconds'])
        f, i = math.modf(seconds)
        seconds = i
        microseconds = int(1e6 * f)

        delta = datetime.timedelta(days=days, hours=hours, minutes=minutes,
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

class Boolean(SimpleModel):
    """Life is simple here. Just true or false."""

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
    """Class that contains mandatory variants of primitives."""

    String = String(type_name="mandatory_string", min_occurs=1, nillable=False, min_len=1)
    Integer = Integer(type_name="mandatory_integer", min_occurs=1, nillable=False)
    UnsignedInteger = UnsignedInteger(type_name="mandatory_unsigned_integer", min_occurs=1, nillable=False)
    UnsignedLong = UnsignedLong(type_name="mandatory_unsigned_integer", min_occurs=1, nillable=False)
