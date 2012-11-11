
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
from pytz import FixedOffset

import spyne.const.xml_ns
from spyne.model import SimpleModel

try:
    from lxml import etree
except ImportError:
    pass

string_encoding = 'utf8'

DATE_PATTERN = r'(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})'
TIME_PATTERN = r'(?P<hr>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})(?P<sec_frac>\.\d+)?'
OFFSET_PATTERN = r'(?P<tz_hr>[+-]\d{2}):(?P<tz_min>\d{2})'
DATETIME_PATTERN = DATE_PATTERN + '[T ]' + TIME_PATTERN
UUID_PATTERN = "%(x)s{8}-%(x)s{4}-%(x)s{4}-%(x)s{4}-%(x)s{12}" % \
                                                            {'x': '[a-fA-F0-9]'}

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

    def __new__(cls, *args, **kwargs):
        assert len(args) <= 1

        if len(args) == 1:
            kwargs['max_len'] = args[0]

        retval = SimpleModel.__new__(cls,  ** kwargs)

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
    pass

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
        """A regular expression that matches the whole time. See here for more
        info: http://www.regular-expressions.info/xml.html"""

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
        return SimpleModel.validate_native(cls, value) and (
            value is None or (
                value >  cls.Attributes.gt and
                value >= cls.Attributes.ge and
                value <  cls.Attributes.lt and
                value <= cls.Attributes.le
            ))


class Double(Decimal):
    """This is serialized as the python ``float``. So this type comes with its
     gotchas."""

    __type_name__ = 'double'


class Float(Double):
    """Synonym for Double (as far as python side of things are concerned).
    It's here for compatibility reasons."""

    __type_name__ = 'float'


class Integer(Decimal):
    """The arbitrary-size signed integer."""

    __type_name__ = 'integer'
    __length__ = None

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
        http://docs.python.org/library/datetime.html?highlight=strftime#strftime-strptime-behavior"""

        string_format = None
        """A regular python string formatting string. %s will contain the date
        string. See here for more info:
        http://docs.python.org/library/stdtypes.html#string-formatting"""

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
            raise ValueError("time data '%s' does not match any of these regex:\n'%s'\n'%s'\n'%s'"
                             %(string, _utc_re.pattern, _offset_re.pattern, _local_re.pattern))

        return cls.parse(match)

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

        pattern = None
        """A regular expression that matches the whole date. See here for more
        info: http://www.regular-expressions.info/xml.html"""

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


class Boolean(SimpleModel):
    """Life is simple here. Just true or false."""

    __type_name__ = 'boolean'


Uuid = Unicode(pattern=UUID_PATTERN, type_name='Uuid')
"""Unicode subclass for Universially-Unique Identifiers."""


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
