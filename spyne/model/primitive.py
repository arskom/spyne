
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


"""
The ``spyne.model.primitive`` package contains types with values that fit
in a single field.

See :mod:`spyne.protocol._model` for {to,from}_string implementations.
"""


from __future__ import absolute_import

import sys
if sys.version > '3':
    long = int

import re
import math
import uuid
import decimal
import datetime
import platform
import spyne

import spyne.const.xml_ns

from spyne.model import SimpleModel
from spyne.util import memoize

string_encoding = 'utf8'

FLOAT_PATTERN = r'-?[0-9]+\.?[0-9]*(e-?[0-9]+)?'
DATE_PATTERN = r'(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})'
TIME_PATTERN = r'(?P<hr>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})(?P<sec_frac>\.\d+)?'
OFFSET_PATTERN = r'(?P<tz_hr>[+-]\d{2}):(?P<tz_min>\d{2})'
DATETIME_PATTERN = DATE_PATTERN + '[T ]' + TIME_PATTERN
UUID_PATTERN = "%(x)s{8}-%(x)s{4}-%(x)s{4}-%(x)s{4}-%(x)s{12}" % \
                                                            {'x': '[a-fA-F0-9]'}

#
# FIXME: Supports e.g.
#     MULTIPOINT (10 40, 40 30, 20 20, 30 10)
#
# but not:
#     MULTIPOINT ((10 40), (40 30), (20 20), (30 10))
#

_rinse_and_repeat = r'\s*\(%s\s*(,\s*%s)*\)\s*'
def _get_one_point_pattern(dim):
    return ' +'.join([FLOAT_PATTERN] * dim)

def _get_point_pattern(dim):
    return r'POINT\s*\(%s\)' % _get_one_point_pattern(dim)

def _get_one_multipoint_pattern(dim):
    one_point = _get_one_point_pattern(dim)
    return _rinse_and_repeat % (one_point, one_point)

def _get_multipoint_pattern(dim):
    return r'MULTIPOINT\s*%s' % _get_one_multipoint_pattern(dim)


def _get_one_line_pattern(dim):
    one_point = _get_one_point_pattern(dim)
    return _rinse_and_repeat % (one_point, one_point)

def _get_linestring_pattern(dim):
    return r'LINESTRING\s*%s' % _get_one_line_pattern(dim)

def _get_one_multilinestring_pattern(dim):
    one_line = _get_one_line_pattern(dim)
    return _rinse_and_repeat % (one_line, one_line)

def _get_multilinestring_pattern(dim):
    return r'MULTILINESTRING\s*%s' % _get_one_multilinestring_pattern(dim)


def _get_one_polygon_pattern(dim):
    one_line = _get_one_line_pattern(dim)
    return _rinse_and_repeat % (one_line, one_line)

def _get_polygon_pattern(dim):
    return r'POLYGON\s*%s' % _get_one_polygon_pattern(dim)

def _get_one_multipolygon_pattern(dim):
    one_line = _get_one_polygon_pattern(dim)
    return _rinse_and_repeat % (one_line, one_line)

def _get_multipolygon_pattern(dim):
    return r'MULTIPOLYGON\s*%s' % _get_one_multipolygon_pattern(dim)


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


# EXPERIMENTAL
class AnyHtml(SimpleModel):
    pass

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

    @staticmethod
    def is_default(cls):
        return (    SimpleModel.is_default(cls)
                and cls.Attributes.min_len == Unicode.Attributes.min_len
                and cls.Attributes.max_len == Unicode.Attributes.max_len
                and cls.Attributes.pattern == Unicode.Attributes.pattern
            )

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

    Note that it is your responsibility to make sure that the scale and
    precision constraints set in this type is consistent with the values in the
    context of the decimal package. See the :func:`decimal.getcontext`
    documentation for more information.
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

        str_format = None
        """A regular python string formatting string used by invoking its
        ``format()`` function. See here:
        http://docs.python.org/2/library/string.html#format-string-syntax"""

        pattern = None
        """A regular expression that matches the whole field. See here for more
        info: http://www.regular-expressions.info/xml.html"""

        total_digits = decimal.Decimal('inf')
        """Maximum number of digits."""

        fraction_digits = decimal.Decimal('inf')
        """Maximum number of digits after the decimal separator."""

        min_bound = None
        """Hardware limit that determines the lowest value this type can
        store."""

        max_bound = None
        """Hardware limit that determines the highest value this type can
        store."""

    def __new__(cls, *args, **kwargs):
        assert len(args) <= 2

        if len(args) >= 1 and args[0] is not None:
            kwargs['total_digits'] = args[0]
            kwargs['fraction_digits'] = 0
            if len(args) == 2 and args[1] is not None:
                kwargs['fraction_digits'] = args[1]
                assert args[0] > 0, "'total_digits' must be positive."
                assert args[1] <= args[0], "'total_digits' must be greater than" \
                                          " or equal to 'fraction_digits'." \
                                          " %r ! <= %r" % (args[1], args[0])

            # + 1 for decimal separator
            # + 1 for negative sign
            msl = kwargs.get('max_str_len', None)
            if msl is None:
                kwargs['max_str_len'] = (cls.Attributes.total_digits +
                                             cls.Attributes.fraction_digits + 2)
            else:
                kwargs['max_str_len'] = msl

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
            value is None or (len(value) <= (cls.Attributes.max_str_len))
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


class Float(Double):
    """Synonym for Double (as far as python side of things are concerned).
    It's here for compatibility reasons."""

    __type_name__ = 'float'


class Integer(Decimal):
    """The arbitrary-size signed integer."""

    __type_name__ = 'integer'

    @staticmethod
    def validate_native(cls, value):
        return (    Decimal.validate_native(cls, value)
                and ((value is None) or (int(value) == value))
            )

class UnsignedInteger(Integer):
    """The arbitrary-size unsigned integer, also known as nonNegativeInteger."""

    __type_name__ = 'nonNegativeInteger'

    @staticmethod
    def validate_native(cls, value):
        return (    Integer.validate_native(cls, value)
                and (value is None or value >= 0)
            )

NonNegativeInteger = UnsignedInteger
"""The arbitrary-size unsigned integer, alias for UnsignedInteger."""


@memoize
def TBoundedInteger(num_bits, type_name):
    _min_b = -(0x8<<(num_bits-4))     # 0x8 is 4 bits.
    _max_b =  (0x8<<(num_bits-4)) - 1 # -1? c'est la vie ;)

    class _BoundedInteger(Integer):
        __type_name__ = type_name

        class Attributes(Integer.Attributes):
            max_str_len = math.ceil(math.log(2**num_bits, 10))
            min_bound = _min_b
            max_bound = _max_b

        @staticmethod
        def validate_native(cls, value):
            return (
                    Integer.validate_native(cls, value)
                and (value is None or (_min_b <= value <= _max_b))
            )

    return _BoundedInteger


@memoize
def TBoundedUnsignedInteger(num_bits, type_name):
    _min_b = 0
    _max_b = 2 ** num_bits - 1 # -1? c'est la vie ;)

    class _BoundedUnsignedInteger(UnsignedInteger):
        __type_name__ = type_name

        class Attributes(UnsignedInteger.Attributes):
            max_str_len = math.ceil(math.log(2**num_bits, 10))
            min_bound = _min_b
            max_bound = _max_b

        @staticmethod
        def validate_native(cls, value):
            return (
                    UnsignedInteger.validate_native(cls, value)
                and (value is None or (_min_b <= value < _max_b))
            )

    return _BoundedUnsignedInteger


Integer64 = TBoundedInteger(64, 'long')
"""The 64-bit signed integer, also known as ``long``."""

Long = Integer64
"""The 64-bit signed integer, alias for :class:`Integer64`."""


Integer32 = TBoundedInteger(32, 'int')
"""The 64-bit signed integer, also known as ``int``."""

Int = Integer32
"""The 32-bit signed integer, alias for :class:`Integer32`."""


Integer16 = TBoundedInteger(16, 'short')
"""The 16-bit signed integer, also known as ``short``."""

Short = Integer16
"""The 16-bit signed integer, alias for :class:`Integer16`."""


Integer8 = TBoundedInteger(8, 'byte')
"""The 8-bit signed integer, also known as ``byte``."""

Byte = Integer8
"""The 8-bit signed integer, alias for :class:`Integer8`."""


UnsignedInteger64 = TBoundedUnsignedInteger(64, 'unsignedLong')
"""The 64-bit unsigned integer, also known as ``unsignedLong``."""

UnsignedLong = UnsignedInteger64
"""The 64-bit unsigned integer, alias for :class:`UnsignedInteger64`."""


UnsignedInteger32 = TBoundedUnsignedInteger(32, 'unsignedInt')
"""The 64-bit unsigned integer, also known as ``unsignedInt``."""

UnsignedInt = UnsignedInteger32
"""The 32-bit unsigned integer, alias for :class:`UnsignedInteger32`."""


UnsignedInteger16 = TBoundedUnsignedInteger(16, 'unsignedShort')
"""The 16-bit unsigned integer, also known as ``unsignedShort``."""

UnsignedShort = UnsignedInteger16
"""The 16-bit unsigned integer, alias for :class:`UnsignedInteger16`."""


UnsignedInteger8 = TBoundedUnsignedInteger(8, 'unsignedByte')
"""The 8-bit unsigned integer, also known as ``unsignedByte``."""

UnsignedByte = UnsignedInteger8
"""The 8-bit unsigned integer, alias for :class:`UnsignedInteger8`."""


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
    Working with timezones is a bit quirky -- Spyne works very hard to have
    all datetimes with time zones internally and only strips them when
    explicitly requested with ``timezone=False``\. See
    :attr:`DateTime.Attributes.as_timezone` for more information.

    Native type is :class:`datetime.datetime`.
    """

    __type_name__ = 'dateTime'

    _local_re = re.compile(DATETIME_PATTERN)
    _utc_re = re.compile(DATETIME_PATTERN + 'Z')
    _offset_re = re.compile(DATETIME_PATTERN + OFFSET_PATTERN)

    class Attributes(SimpleModel.Attributes):
        """Customizable attributes of the :class:`spyne.model.primitive.DateTime`
        type."""

        gt = datetime.datetime(datetime.MINYEAR, 1, 1, 0, 0, 0, 0, spyne.LOCAL_TZ) # minExclusive
        """The datetime should be greater than this datetime. It must always
        have a timezone."""

        ge = datetime.datetime(datetime.MINYEAR, 1, 1, 0, 0, 0, 0, spyne.LOCAL_TZ) # minInclusive
        """The datetime should be greater than or equal to this datetime. It
        must always have a timezone."""

        lt = datetime.datetime(datetime.MAXYEAR, 12, 31, 23, 59, 59, 999999, spyne.LOCAL_TZ) # maxExclusive
        """The datetime should be lower than this datetime. It must always have
        a timezone."""

        le = datetime.datetime(datetime.MAXYEAR, 12, 31, 23, 59, 59, 999999, spyne.LOCAL_TZ) # maxInclusive
        """The datetime should be lower than or equal to this datetime. It must
        always have a timezone."""

        pattern = None
        """A regular expression that matches the whole datetime. See here for
        more info: http://www.regular-expressions.info/xml.html"""

        format = None
        """DateTime format fed to the ``strftime`` function. See:
        http://docs.python.org/library/datetime.html?highlight=strftime#strftime-strptime-behavior
        Ignored by protocols like SOAP which have their own ideas about how
        DateTime objects should be serialized."""

        string_format = None
        """A regular python string formatting string. %s will contain the date
        string. See here for more info:
        http://docs.python.org/library/stdtypes.html#string-formatting"""

        as_timezone = None
        """When not None, converts:
            - Outgoing values to the given time zone (by calling
              ``.astimezone()``).
            - Incoming values without tzinfo to the given time zone by calling
              ``.replace(tzinfo=<as_timezone>)`` and values with tzinfo to the
               given timezone by calling ``.astimezone()``.

        Either None or a return value of pytz.timezone()

        When this is None and a datetime with tzinfo=None comes in, it's
        converted to spyne.LOCAL_TZ which defaults to ``pytz.utc``. You can use
        `tzlocal <https://pypi.python.org/pypi/tzlocal>`_ to set it to local
        time right after ``import spyne``.
        """

        timezone = True
        """If False, time zone info is stripped before serialization. Also makes
        sqlalchemy schema generator emit 'timestamp without timezone'."""

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
        if isinstance(value, datetime.datetime) and value.tzinfo is None:
            value = value.replace(tzinfo=spyne.LOCAL_TZ)
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

    _offset_re = re.compile(DATE_PATTERN + '(' + OFFSET_PATTERN + '|Z)')

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


class Uuid(Unicode(pattern=UUID_PATTERN)):
    """Unicode subclass for Universially-Unique Identifiers."""

    __namespace__ = 'http://spyne.io/schema'
    __type_name__ = 'uuid'


class NormalizedString(Unicode):
    __type_name__ = 'normalizedString'
    __extends__ = Unicode

    class Attributes(Unicode.Attributes):
        white_space = "replace"

class Token(NormalizedString):
    __type_name__ = 'token'

    class Attributes(Unicode.Attributes):
        white_space = "collapse"


class Name(Token):
    __type_name__ = 'Name'

    class Attributes(Unicode.Attributes):
        # Original: '[\i-[:]][\c-[:]]*'
        # See: http://www.regular-expressions.info/xmlcharclass.html
        pattern = '[[_:A-Za-z]-[:]][[-._:A-Za-z0-9]-[:]]*'


class NCName(Name):
    __type_name__ = 'NCName'



class ID(NCName):
    __type_name__ = 'ID'



class Language(Token):
    __type_name__ = 'language'

    class Attributes(Unicode.Attributes):
        pattern = '[a-zA-Z]{1,8}(-[a-zA-Z0-9]{1,8})*'


class Point(Unicode):
    """A point type whose native format is a WKT string. You can use
    :func:`shapely.wkt.loads` to get a proper point type."""
    __type_name__ = None

    class Attributes(Unicode.Attributes):
        dim = None

    @staticmethod
    def Value(x, y):
        return 'POINT(%3.15f %3.15f)' % (x,y)

    def __new__(cls, dim=None, **kwargs):
        assert dim in (None,2,3)
        if dim is not None:
            kwargs['dim'] = dim
            kwargs['pattern'] = _get_point_pattern(dim)
            kwargs['type_name'] = 'point%dd' % dim

        retval = SimpleModel.__new__(cls, **kwargs)
        retval.__namespace__ = 'http://spyne.io/schema'
        retval.__extends__ = Unicode
        retval.__orig__ = Unicode
        return retval


class Line(Unicode):
    """A point type whose native format is a WKT string. You can use
    :func:`shapely.wkt.loads` to get a proper point type."""
    __type_name__ = None

    class Attributes(Unicode.Attributes):
        dim = None

    def __new__(cls, dim=None, **kwargs):
        assert dim in (None,2,3)
        if dim is not None:
            kwargs['dim'] = dim
            kwargs['pattern'] = _get_linestring_pattern(dim)
            kwargs['type_name'] = 'line%dd' % dim

        retval = SimpleModel.__new__(cls, **kwargs)
        retval.__namespace__ = 'http://spyne.io/schema'
        retval.__extends__ = Unicode
        retval.__orig__ = Unicode
        return retval

LineString = Line


class Polygon(Unicode):
    """A Polygon type whose native format is a WKT string. You can use
    :func:`shapely.wkt.loads` to get a proper polygon type."""
    __type_name__ = None

    class Attributes(Unicode.Attributes):
        dim = None

    def __new__(cls, dim=None, **kwargs):
        assert dim in (None,2,3)
        if dim is not None:
            kwargs['dim'] = dim
            kwargs['pattern'] = _get_polygon_pattern(dim)
            kwargs['type_name'] = 'polygon%dd' % dim

        retval = SimpleModel.__new__(cls, **kwargs)
        retval.__namespace__ = 'http://spyne.io/schema'
        retval.__extends__ = Unicode
        retval.__orig__ = Unicode
        return retval


class MultiPoint(Unicode):
    """A Multipolygon type whose native format is a WKT string. You can use
    :func:`shapely.wkt.loads` to get a proper multipolygon type."""
    __type_name__ = None

    class Attributes(Unicode.Attributes):
        dim = None

    def __new__(cls, dim=None, **kwargs):
        assert dim in (None,2,3)
        if dim is not None:
            kwargs['dim'] = dim
            kwargs['pattern'] = _get_multipoint_pattern(dim)
            kwargs['type_name'] = 'multiPoint%dd' % dim

        retval = SimpleModel.__new__(cls, **kwargs)
        retval.__namespace__ = 'http://spyne.io/schema'
        retval.__extends__ = Unicode
        retval.__orig__ = Unicode
        return retval


class MultiLine(Unicode):
    """A Multipolygon type whose native format is a WKT string. You can use
    :func:`shapely.wkt.loads` to get a proper multipolygon type."""
    __type_name__ = None

    class Attributes(Unicode.Attributes):
        dim = None

    def __new__(cls, dim=None, **kwargs):
        assert dim in (None,2,3)
        if dim is not None:
            kwargs['dim'] = dim
            kwargs['pattern'] = _get_multilinestring_pattern(dim)
            kwargs['type_name'] = 'multiLine%dd' % dim

        retval = SimpleModel.__new__(cls, **kwargs)
        retval.__namespace__ = 'http://spyne.io/schema'
        retval.__extends__ = Unicode
        retval.__orig__ = Unicode
        return retval

MultiLineString = MultiLine


class MultiPolygon(Unicode):
    """A Multipolygon type whose native format is a WKT string. You can use
    :func:`shapely.wkt.loads` to get a proper multipolygon type."""
    __type_name__ = None

    class Attributes(Unicode.Attributes):
        dim = None

    def __new__(cls, dim=None, **kwargs):
        assert dim in (None,2,3)
        if dim is not None:
            kwargs['dim'] = dim
            kwargs['pattern'] = _get_multipolygon_pattern(dim)
            kwargs['type_name'] = 'multipolygon%dd' % dim

        retval = SimpleModel.__new__(cls, **kwargs)
        retval.__namespace__ = 'http://spyne.io/schema'
        retval.__extends__ = Unicode
        retval.__orig__ = Unicode
        return retval


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
    Double = Double(type_name="MandatoryDouble", min_occurs=1, nillable=False)
    Float = Float(type_name="MandatoryFloat", min_occurs=1, nillable=False)

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

    Uuid = Uuid(type_name="MandatoryUuid", min_len=1, min_occurs=1, nillable=False)

    Point = Point(type_name="Point", min_len=1, min_occurs=1, nillable=False)
    Line = Line(type_name="LineString", min_len=1, min_occurs=1, nillable=False)
    LineString = Line
    Polygon = Polygon(type_name="Polygon", min_len=1, min_occurs=1, nillable=False)

    MultiPoint = MultiPoint(type_name="MandatoryMultiPoint", min_len=1, min_occurs=1, nillable=False)
    MultiLine = MultiLine(type_name="MandatoryMultiLineString", min_len=1, min_occurs=1, nillable=False)
    MultiLineString = MultiLine
    MultiPolygon = MultiPolygon(type_name="MandatoryMultiPolygon", min_len=1, min_occurs=1, nillable=False)


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
        int: Integer,
    })

else:
    NATIVE_MAP.update({
        str: String,
        unicode: Unicode,
        long: Integer,
    })

    if isinstance (0x80000000, long): # 32-bit architecture
        NATIVE_MAP[int] = Integer32
    else: # not 32-bit (so most probably 64-bit) architecture
        NATIVE_MAP[int] = Integer64

assert Mandatory.Long == Mandatory.Integer64
