
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

"""The ``spyne.model.primitive`` package contains atomic, single-value types."""

import sys
if sys.version > '3':
    long = int

import re
import math
import uuid
import pytz
import decimal
import datetime
import platform
import time

import spyne.const.xml_ns

from collections import deque

from pytz import FixedOffset

from spyne.model import SimpleModel
from spyne.model import nillable_string
from spyne.error import ValidationError
from spyne.error import Fault

try:
    from lxml import etree
except ImportError:
    pass

string_encoding = 'utf8'

FLOAT_PATTERN = '-?[0-9]+\.?[0-9]*'
DATE_PATTERN = r'(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})'
TIME_PATTERN = r'(?P<hr>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})(?P<sec_frac>\.\d+)?'
OFFSET_PATTERN = r'(?P<tz_hr>[+-]\d{2}):(?P<tz_min>\d{2})'
DATETIME_PATTERN = DATE_PATTERN + '[T ]' + TIME_PATTERN
UUID_PATTERN = "%(x)s{8}-%(x)s{4}-%(x)s{4}-%(x)s{4}-%(x)s{12}" % \
                                                            {'x': '[a-fA-F0-9]'}

def _get_one_point_pattern(dim):
    return ' +'.join([FLOAT_PATTERN] * dim)

def _get_point_pattern(dim):
    return 'POINT *\\(%s\\)' % _get_one_point_pattern(dim)

def _get_one_line_pattern(dim):
    one_point = _get_one_point_pattern(dim)
    return '\\(%s *(, *%s)*\\)' % (one_point, one_point)

def _get_linestring_pattern(dim):
    return 'LINESTRING *%s' % _get_one_line_pattern(dim)

def _get_one_polygon_pattern(dim):
    one_line = _get_one_line_pattern(dim)
    return '\\(%s *(, *%s)*\\)' % (one_line, one_line)

def _get_polygon_pattern(dim):
    return 'POLYGON *%s' % _get_one_polygon_pattern(dim)


_local_re = re.compile(DATETIME_PATTERN)
_utc_re = re.compile(DATETIME_PATTERN + 'Z')
_offset_re = re.compile(DATETIME_PATTERN + OFFSET_PATTERN)
_date_re = re.compile(DATE_PATTERN)
_time_re = re.compile(TIME_PATTERN)
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


_ns_xs = spyne.const.xml_ns.xsd
_ns_xsi = spyne.const.xml_ns.xsi


class AnyXml(SimpleModel):
    """An xml node that can contain any number of sub nodes. It's represented by
    an ElementTree object."""

    __type_name__ = 'anyType'

    class Attributes(SimpleModel.Attributes):
        namespace = None
        """Xml-Schema specific namespace attribute"""

        process_contents = None
        """Xml-Schema specific processContents attribute"""

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
    """A dict instance that can contain other dicts, iterables or primitive
    types. Its serialization is protocol-dependent.
    """

    __type_name__ = 'anyType'


class Unicode(SimpleModel):
    """The type to represent human-readable data. Its native format is `unicode`
    or `str` with given encoding.
    """

    __type_name__ = 'string'

    class Attributes(SimpleModel.Attributes):
        """Customizable attributes of the :class:`spyne.model.primitive.Unicode`
        type."""

        min_len = 0
        """Minimum length of string. Can be set to any positive integer"""

        max_len = decimal.Decimal('inf')
        """Maximum length of string. Can be set to ``decimal.Decimal('inf')`` to
        accept strings of arbitrary length. You may also need to adjust
        :const:`spyne.server.wsgi.MAX_CONTENT_LENGTH`."""

        pattern = None
        """A regular expression that matches the whole string. See here for more
        info: http://www.regular-expressions.info/xml.html"""

        encoding = None
        """The encoding of `str` objects this class may have to deal with."""

        unicode_errors = 'strict'
        """The argument to the ``unicode`` builtin; one of 'strict', 'replace'
        or 'ignore'."""

        format = None
        """A regular python string formatting string. See here:
        http://docs.python.org/library/stdtypes.html#string-formatting"""

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
        if cls.Attributes.format is None:
            return retval
        else:
            return cls.Attributes.format % retval

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
                    len(value) >= cls.Attributes.min_len
                and len(value) <= cls.Attributes.max_len
                and _re_match_with_span(cls.Attributes, value)
            )))


def _re_match_with_span(attr, value):
    if attr.pattern is None:
        return True

    m = attr._pattern_re.match(value)
    return (m is not None) and (m.span() == (0, len(value)))


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
    """A special kind of String type designed to hold an uri."""

    __type_name__ = 'anyURI'

    class Attributes(String.Attributes):
        text = None
        """The text shown in link. This is an object-wide constant."""

    class Value(object):
        """A special object that is just a better way of carrying the
        information carried with a link.

        :param href: The uri string.
        :param text: The text data that goes with the link. This is a
            ``str`` or a ``unicode`` instance.
        :param content: The structured data that goes with the link. This is an
            `lxml.etree.Element` instance.
        """

        def __init__(self, href, text=None, content=None):
            self.href = href
            self.text = text
            self.content = content


class ImageUri(AnyUri):
    """A special kind of String that holds the uri of an image."""


class Decimal(SimpleModel):
    """The primitive that corresponds to the native python Decimal.

    This is also the base class for denoting numbers.
    """

    __type_name__ = 'decimal'

    class Attributes(SimpleModel.Attributes):
        """Customizable attributes of the :class:`spyne.model.primitive.Decimal`
        type."""

        gt = decimal.Decimal('-inf') # minExclusive
        """The value should be greater than this number."""

        ge = decimal.Decimal('-inf') # minInclusive
        """The value should be greater than or equal to this number."""

        lt = decimal.Decimal('inf') # maxExclusive
        """The value should be lower than this number."""

        le = decimal.Decimal('inf') # maxInclusive
        """The value should be lower than or equal to this number."""

        max_str_len = 1024
        """The maximum length of string to be attempted to convert to number."""

        format = None
        """A regular python string formatting string. See here:
        http://docs.python.org/library/stdtypes.html#string-formatting"""

        pattern = None
        """A regular expression that matches the whole field. See here for more
        info: http://www.regular-expressions.info/xml.html"""

        total_digits = decimal.Decimal('inf')
        """Maximum number of digits."""

        fraction_digits = decimal.Decimal('inf')
        """Maximum number of digits after the decimal separator."""

    def __new__(cls, *args, **kwargs):
        assert len(args) <= 2

        if len(args) >= 1 and args[0] is not None:
            kwargs['total_digits'] = args[0]
            kwargs['fraction_digits'] = 0
            if len(args) == 2 and args[1] is not None:
                kwargs['fraction_digits'] = args[1]
                assert args[1] <= args[0], "Total digits should be greater than" \
                                          " or equal to fraction digits." \
                                          " %r ! <= %r" % (args[1], args[0])

        retval = SimpleModel.__new__(cls,  ** kwargs)

        return retval

    @staticmethod
    def is_default(cls):
        return (    SimpleModel.is_default(cls)
                and cls.Attributes.gt == Decimal.Attributes.gt
                and cls.Attributes.ge == Decimal.Attributes.ge
                and cls.Attributes.lt == Decimal.Attributes.lt
                and cls.Attributes.le == Decimal.Attributes.le
                and cls.Attributes.total_digits == \
                                            Decimal.Attributes.total_digits
                and cls.Attributes.fraction_digits == \
                                            Decimal.Attributes.fraction_digits
            )

    @staticmethod
    def validate_string(cls, value):
        return SimpleModel.validate_string(cls, value) and (
            value is None or (
                len(value) <= (cls.Attributes.total_digits +
                                             cls.Attributes.fraction_digits + 1)
                                                  # + 1 is for decimal separator
            ))

    @staticmethod
    def validate_native(cls, value):
        return SimpleModel.validate_native(cls, value) and (
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
        if cls.Attributes.format is None:
            return str(value)
        else:
            return cls.Attributes.format % value

    @classmethod
    @nillable_string
    def from_string(cls, string):
        if cls.Attributes.max_str_len is not None and len(string) > cls.Attributes.max_str_len:
            raise ValidationError(string, 'string too long.')

        try:
            return decimal.Decimal(string)
        except decimal.InvalidOperation, e:
            raise ValidationError(string)


class Double(Decimal):
    """This is serialized as the python ``float``. So this type comes with its
     gotchas. Unless you really know what you're doing, you should use a
     :class:`Decimal` with a pre-defined number of integer and decimal digits.
     """

    __type_name__ = 'double'

    if platform.python_version_tuple()[:2] == ('2','6'):
        class Attributes(Decimal.Attributes):
            """Customizable attributes of the :class:`spyne.model.primitive.Double`
            type. This class is only here for Python 2.6: See this bug report
            for more info: http://bugs.python.org/issue2531
            """

            gt = float('-inf') # minExclusive
            """The value should be greater than this number."""

            ge = float('-inf') # minInclusive
            """The value should be greater than or equal to this number."""

            lt = float('inf') # maxExclusive
            """The value should be lower than this number."""

            le = float('inf') # maxInclusive
            """The value should be lower than or equal to this number."""

        @staticmethod
        def is_default(cls):
            return (    SimpleModel.is_default(cls)
                    and cls.Attributes.gt == Double.Attributes.gt
                    and cls.Attributes.ge == Double.Attributes.ge
                    and cls.Attributes.lt == Double.Attributes.lt
                    and cls.Attributes.le == Double.Attributes.le
                )

    @classmethod
    @nillable_string
    def to_string(cls, value):
        float(value)
        if cls.Attributes.format is None:
            return repr(value)
        else:
            return cls.Attributes.format % value

    @classmethod
    @nillable_string
    def from_string(cls, string):
        try:
            return float(string)
        except ValueError:
            raise ValidationError(string)


class Float(Double):
    """Synonym for Double (as far as python side of things are concerned).
    It's here for compatibility reasons."""

    __type_name__ = 'float'


class Integer(Decimal):
    """The arbitrary-size signed integer."""

    __type_name__ = 'integer'

    @classmethod
    @nillable_string
    def to_string(cls, value):
        int(value) # sanity check

        return str(value)

    @classmethod
    @nillable_string
    def from_string(cls, string):
        if cls.Attributes.max_str_len is not None and \
                                 len(str(string)) > cls.Attributes.max_str_len:
            raise Fault('Client.ValidationError', 'String longer than '
                        '%d characters.' % cls.Attributes.max_str_len)

        try:
            return int(string)
        except ValueError:
            try:
                return int(string)
            except ValueError:
                raise ValidationError(string)


class UnsignedInteger(Integer):
    """The arbitrary-size unsigned integer, aka nonNegativeInteger."""

    __type_name__ = 'nonNegativeInteger'

    @staticmethod
    def validate_native(cls, value):
        return (     Integer.validate_native(cls, value)
                and value >= 0
            )


NonNegativeInteger = UnsignedInteger


class Integer64(Integer):
    """The 64-bit signed integer, aka long."""

    __type_name__ = 'long'

    class Attributes(Integer.Attributes):
        max_str_len = math.ceil(math.log(2**64, 10)) + 1 # +1 for negatives

    @staticmethod
    def validate_native(cls, value):
        return (     Integer.validate_native(cls, value)
                and -0x8000000000000000 <= value < 0x8000000000000000
            )

Long = Integer64


class Integer32(Integer):
    """The 32-bit signed integer, aka int."""

    __type_name__ = 'int'

    class Attributes(Integer.Attributes):
        max_str_len = math.ceil(math.log(2**32, 10)) + 1 # +1 for negatives

    @staticmethod
    def validate_native(cls, value):
        return (     Integer.validate_native(cls, value)
                and -0x80000000 <= value < 0x80000000
            )

Int = Integer32


class Integer16(Integer):
    """The 8-bit signed integer, aka short."""

    __type_name__ = 'short'

    class Attributes(Integer.Attributes):
        max_str_len = math.ceil(math.log(2**16, 10)) + 1 # +1 for negatives

    @staticmethod
    def validate_native(cls, value):
        return (     Integer.validate_native(cls, value)
                and -0x8000 <= value < 0x8000
            )

Short = Integer64


class Integer8(Integer):
    """The 8-bit signed integer, aka byte."""

    __type_name__ = 'byte'

    class Attributes(Integer.Attributes):
        max_str_len = math.ceil(math.log(2**8, 10)) + 1 # +1 for negatives


    @staticmethod
    def validate_native(cls, value):
        return (     Integer.validate_native(cls, value)
                and -0x80 <= value < 0x80
            )

Byte = Integer8


class UnsignedInteger64(UnsignedInteger):
    """The 64-bit unsigned integer, aka unsignedLong."""

    __type_name__ = 'unsignedLong'

    class Attributes(Integer.Attributes):
        max_str_len = math.ceil(math.log(2**64, 10))

    @staticmethod
    def validate_native(cls, value):
        return (     UnsignedInteger.validate_native(cls, value)
                and  value <= 0xFFFFFFFFFFFFFFFF
            )

UnsignedLong = UnsignedInteger64


class UnsignedInteger32(UnsignedInteger):
    """The 32-bit unsigned integer, aka unsignedInt."""

    __type_name__ = 'unsignedInt'

    class Attributes(Integer.Attributes):
        max_str_len = math.ceil(math.log(2**32, 10))

    @staticmethod
    def validate_native(cls, value):
        return (     UnsignedInteger.validate_native(cls, value)
                and  value <= 0xFFFFFFFF
            )

UnsignedInt = UnsignedInteger32


class UnsignedInteger16(Integer):
    """The 16-bit unsigned integer, aka unsignedShort."""

    __type_name__ = 'unsignedShort'

    class Attributes(Integer.Attributes):
        max_str_len = math.ceil(math.log(2**16, 10))

    @staticmethod
    def validate_native(cls, value):
        return (     UnsignedInteger.validate_native(cls, value)
                and  value <= 0xFFFF
            )

UnsignedShort = UnsignedInteger16


class UnsignedInteger8(Integer):
    """The 8-bit unsigned integer, aka unsignedByte."""

    __type_name__ = 'unsignedByte'

    class Attributes(Integer.Attributes):
        max_str_len = math.ceil(math.log(2**8, 10))

    @staticmethod
    def validate_native(cls, value):
        return (     UnsignedInteger.validate_native(cls, value)
                and  value <= 0xFF
            )

UnsignedByte = UnsignedInteger8


class Time(SimpleModel):
    """Just that, Time. No time zone support.

    Native type is :class:`datetime.time`.
    """

    __type_name__ = 'time'

    class Attributes(SimpleModel.Attributes):
        """Customizable attributes of the :class:`spyne.model.primitive.Time`
        type."""

        gt = datetime.time(0, 0, 0, 0) # minExclusive
        """The time should be greater than this time."""

        ge = datetime.time(0, 0, 0, 0) # minInclusive
        """The time should be greater than or equal to this time."""

        lt = datetime.time(23, 59, 59, 999999) # maxExclusive
        """The time should be lower than this time."""

        le = datetime.time(23, 59, 59, 999999) # maxInclusive
        """The time should be lower than or equal to this time."""

        pattern = None
        """A regular expression that matches the whole time. See here for more
        info: http://www.regular-expressions.info/xml.html"""

    @classmethod
    @nillable_string
    def to_string(cls, value):
        """Returns ISO formatted dates."""

        return value.isoformat()

    @classmethod
    @nillable_string
    def from_string(cls, string):
        """Expects ISO formatted times."""

        match = _time_re.match(string)
        if match is None:
            raise ValidationError(string)

        fields = match.groupdict(0)
        microsec = fields.get("sec_frac")
        if microsec is None or microsec == 0:
            microsec = 0
        else:
            microsec = int(microsec[1:])

        return datetime.time(int(fields['hr']), int(fields['min']),
                    int(fields['sec']), microsec)

    @staticmethod
    def is_default(cls):
        return (    SimpleModel.is_default(cls)
                and cls.Attributes.gt == Time.Attributes.gt
                and cls.Attributes.ge == Time.Attributes.ge
                and cls.Attributes.lt == Time.Attributes.lt
                and cls.Attributes.le == Time.Attributes.le
                and cls.Attributes.pattern == Time.Attributes.pattern
        )

    @staticmethod
    def validate_native(cls, value):
        return SimpleModel.validate_native(cls, value) and (
            value is None or (
                value >  cls.Attributes.gt and
                value >= cls.Attributes.ge and
                value <  cls.Attributes.lt and
                value <= cls.Attributes.le
            ))

class DateTime(SimpleModel):
    """A compact way to represent dates and times together. Supports time zones.

    Native type is :class:`datetime.datetime`.
    """
    __type_name__ = 'dateTime'

    class Attributes(SimpleModel.Attributes):
        """Customizable attributes of the :class:`spyne.model.primitive.DateTime`
        type."""

        gt = datetime.datetime(datetime.MINYEAR, 1, 1, 0, 0, 0, 0, pytz.utc) # minExclusive
        """The datetime should be greater than this datetime."""

        ge = datetime.datetime(datetime.MINYEAR, 1, 1, 0, 0, 0, 0, pytz.utc) # minInclusive
        """The datetime should be greater than or equal to this datetime."""

        lt = datetime.datetime(datetime.MAXYEAR, 12, 31, 23, 59, 59, 999999, pytz.utc) # maxExclusive
        """The datetime should be lower than this datetime."""

        le = datetime.datetime(datetime.MAXYEAR, 12, 31, 23, 59, 59, 999999, pytz.utc) # maxInclusive
        """The datetime should be lower than or equal to this datetime."""

        pattern = None
        """A regular expression that matches the whole datetime. See here for more
        info: http://www.regular-expressions.info/xml.html"""

        format = None
        """DateTime format fed to the ``strftime`` function. See:
        http://docs.python.org/library/datetime.html?highlight=strftime#strftime-strptime-behavior
        Ignored by protocols like SOAP which have their own ideas about how
        DateTime objects should be serialized."""

        string_format = None
        """A regular python string formatting string. %s will contain the date
        string. See here for more info:
        http://docs.python.org/library/stdtypes.html#string-formatting"""

    @classmethod
    @nillable_string
    def to_string(cls, value):
        format = cls.Attributes.format
        if format is None:
            ret_str = value.isoformat()
        else:
            ret_str = datetime.datetime.strftime(value, format)

        string_format = cls.Attributes.string_format
        if string_format is None:
            return ret_str
        else:
            return string_format % ret_str

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
    def default_parse(cls, string):
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

    @classmethod
    @nillable_string
    def from_string(cls, string):
        """expect ISO formatted dates"""
        format = cls.Attributes.format

        if format is None:
            return cls.default_parse(string)
        else:
            return datetime.datetime.strptime(string, format)

    @staticmethod
    def is_default(cls):
        return (    SimpleModel.is_default(cls)
                and cls.Attributes.gt == DateTime.Attributes.gt
                and cls.Attributes.ge == DateTime.Attributes.ge
                and cls.Attributes.lt == DateTime.Attributes.lt
                and cls.Attributes.le == DateTime.Attributes.le
                and cls.Attributes.pattern == DateTime.Attributes.pattern
        )

    @staticmethod
    def validate_native(cls, value):
        return SimpleModel.validate_native(cls, value) and (
            value is None or (
                value >  cls.Attributes.gt and
                value >= cls.Attributes.ge and
                value <  cls.Attributes.lt and
                value <= cls.Attributes.le
            ))


class Date(DateTime):
    """Just that, Date. No time zone support.

    Native type is :class:`datetime.date`.
    """

    __type_name__ = 'date'

    class Attributes(DateTime.Attributes):
        """Customizable attributes of the :class:`spyne.model.primitive.Date`
        type."""

        gt = datetime.date(1, 1, 1) # minExclusive
        """The date should be greater than this date."""

        ge = datetime.date(1, 1, 1) # minInclusive
        """The date should be greater than or equal to this date."""

        lt = datetime.date(datetime.MAXYEAR, 12, 31) # maxExclusive
        """The date should be lower than this date."""

        le = datetime.date(datetime.MAXYEAR, 12, 31) # maxInclusive
        """The date should be lower than or equal to this date."""

        format = '%Y-%m-%d'
        """DateTime format fed to the ``strftime`` function. See:
        http://docs.python.org/library/datetime.html?highlight=strftime#strftime-strptime-behavior
        Ignored by protocols like SOAP which have their own ideas about how
        Date objects should be serialized."""

        pattern = None
        """A regular expression that matches the whole date. See here for more
        info: http://www.regular-expressions.info/xml.html"""

    @classmethod
    @nillable_string
    def to_string(cls, value):
        """Returns ISO formatted date."""

        return value.isoformat()

    @classmethod
    def default_parse(cls, string):
        """This is used by protocols like SOAP who need ISO8601-formatted dates
        no matter what.
        """
        try:
            return datetime.date(*(time.strptime(string, '%Y-%m-%d')[0:3]))

        except ValueError:
            raise ValidationError(string)

    @classmethod
    @nillable_string
    def from_string(cls, string):
        try:
            d = datetime.datetime.strptime(string, cls.Attributes.format)
            return datetime.date(d.year, d.month, d.day)

        except ValueError:
            raise ValidationError(string)

    @staticmethod
    def is_default(cls):
        return (    SimpleModel.is_default(cls)
                and cls.Attributes.gt == Date.Attributes.gt
                and cls.Attributes.ge == Date.Attributes.ge
                and cls.Attributes.lt == Date.Attributes.lt
                and cls.Attributes.le == Date.Attributes.le
                and cls.Attributes.pattern == Date.Attributes.pattern
        )

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


class Uuid(Unicode(pattern=UUID_PATTERN, type_name='uuid')):
    """Unicode subclass for Universially-Unique Identifiers."""

    @classmethod
    @nillable_string
    def to_string(cls, value):
        return str(value)

    @classmethod
    @nillable_string
    def from_string(cls, string):
        return uuid.UUID(string)


class Polygon(Unicode):
    """An experimental point type whose native format is WKT. You can use
    :func:`shapely.wkt.loads` to get a proper polygon type."""

    __base_type__ = Unicode

    class Attributes(Unicode.Attributes):
        dim = None

    def __new__(cls, dim=None, **kwargs):
        assert dim in (None,2,3)
        if dim is not None:
            kwargs['dim'] = dim
            kwargs['pattern'] = _get_polygon_pattern(dim)
            kwargs['type_name'] = 'polygon%dd' % dim

        return SimpleModel.__new__(cls,  ** kwargs)


class Point(Unicode):
    """An experimental point type whose native format is WKT. You can use
    :func:`shapely.wkt.loads` to get a proper point type."""

    __base_type__ = Unicode

    class Attributes(Unicode.Attributes):
        dim = None

    def __new__(cls, dim=None, **kwargs):
        assert dim in (None,2,3)
        if dim is not None:
            kwargs['dim'] = dim
            kwargs['pattern'] = _get_point_pattern(dim)
            kwargs['type_name'] = 'point%dd' % dim

        return SimpleModel.__new__(cls,  ** kwargs)


# a class that is really a namespace
class Mandatory:
    """Class that contains mandatory variants of primitives."""

    Unicode = Unicode(type_name="MandatoryString", min_occurs=1, nillable=False, min_len=1)
    String = String(type_name="MandatoryString", min_occurs=1, nillable=False, min_len=1)

    AnyXml = AnyXml(type_name="MandatoryXml", min_occurs=1, nillable=False)
    AnyDict = AnyDict(type_name="MandatoryDict", min_occurs=1, nillable=False)
    AnyUri = AnyUri(type_name="MandatoryUri", min_occurs=1, nillable=False, min_len=1)
    ImageUri = ImageUri(type_name="MandatoryImageUri", min_occurs=1, nillable=False, min_len=1)

    Boolean = Boolean(type_name="MandatoryBoolean", min_occurs=1, nillable=False)

    Date = Date(type_name="MandatoryDate", min_occurs=1, nillable=False)
    Time = Time(type_name="MandatoryTime", min_occurs=1, nillable=False)
    DateTime = DateTime(type_name="MandatoryDateTime", min_occurs=1, nillable=False)
    Duration = Duration(type_name="MandatoryDuration", min_occurs=1, nillable=False)

    Decimal = Decimal(type_name="MandatoryDecimal", min_occurs=1, nillable=False)
    Double = Decimal(type_name="MandatoryDouble", min_occurs=1, nillable=False)
    Float = Double

    Integer = Integer(type_name="MandatoryInteger", min_occurs=1, nillable=False)
    Integer64 = Integer64(type_name="MandatoryLong", min_occurs=1, nillable=False)
    Integer32 = Integer32(type_name="MandatoryInt", min_occurs=1, nillable=False)
    Integer16 = Integer16(type_name="MandatoryShort", min_occurs=1, nillable=False)
    Integer8 = Integer8(type_name="MandatoryByte", min_occurs=1, nillable=False)

    Long = Integer64
    Int = Integer32
    Short = Integer16
    Byte = Integer8

    UnsignedInteger = UnsignedInteger(type_name="MandatoryUnsignedInteger", min_occurs=1, nillable=False)
    UnsignedInteger64 = UnsignedInteger64(type_name="MandatoryUnsignedLong", min_occurs=1, nillable=False)
    UnsignedInteger32 = UnsignedInteger32(type_name="MandatoryUnsignedInt", min_occurs=1, nillable=False)
    UnsignedInteger16 = UnsignedInteger16(type_name="MandatoryUnsignedShort", min_occurs=1, nillable=False)
    UnsignedInteger8 = UnsignedInteger8(type_name="MandatoryUnsignedByte", min_occurs=1, nillable=False)

    UnsignedLong = UnsignedInteger64
    UnsignedInt = UnsignedInteger32
    UnsignedShort = UnsignedInteger16
    UnsignedByte = UnsignedInteger8

    Uuid = Unicode(type_name="MandatoryUuid", min_occurs=1, nillable=False, min_len=1, pattern=UUID_PATTERN)


NATIVE_MAP = {
    float: Double,
    bool: Boolean,
    datetime.datetime: DateTime,
    datetime.time: Time,
    datetime.date: Date,
    datetime.timedelta: Duration,
    decimal.Decimal: Decimal,
    uuid.UUID: Uuid,
}


if sys.version > '3':
    NATIVE_MAP.update({
        str: Unicode,
        unicode: Unicode,
        int: Integer,
    })

else:
    NATIVE_MAP.update({
        str: String,
        unicode: Unicode,
        int: Integer64,
        long: Integer,
    })
