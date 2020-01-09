
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

from __future__ import absolute_import

import re
import spyne
import datetime

from spyne.model import SimpleModel
from spyne.model.primitive import NATIVE_MAP

FLOAT_PATTERN = r'-?[0-9]+\.?[0-9]*(e-?[0-9]+)?'
DATE_PATTERN = r'(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})'
TIME_PATTERN = r'(?P<hr>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})(?P<sec_frac>\.\d+)?'
OFFSET_PATTERN = r'(?P<tz_hr>[+-]\d{2}):(?P<tz_min>\d{2})'
DATETIME_PATTERN = DATE_PATTERN + '[T ]' + TIME_PATTERN


class Time(SimpleModel):
    """Just that, Time. No time zone support.

    Native type is :class:`datetime.time`.
    """

    __type_name__ = 'time'
    Value = datetime.time

    class Attributes(SimpleModel.Attributes):
        """Customizable attributes of the :class:`spyne.model.primitive.Time`
        type."""

        gt = None  # minExclusive
        """The time should be greater than this time."""

        ge = datetime.time(0, 0, 0, 0)  # minInclusive
        """The time should be greater than or equal to this time."""

        lt = None  # maxExclusive
        """The time should be lower than this time."""

        le = datetime.time(23, 59, 59, 999999)  # maxInclusive
        """The time should be lower than or equal to this time."""

        pattern = None
        """A regular expression that matches the whole time. See here for more
        info: http://www.regular-expressions.info/xml.html"""

        time_format = None
        """Time format fed to the ``strftime`` function. See:
        http://docs.python.org/library/datetime.html?highlight=strftime#strftime-strptime-behavior
        Ignored by protocols like SOAP which have their own ideas about how
        Date objects should be serialized."""

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
                (cls.Attributes.gt is None or value >  cls.Attributes.gt)
                and value >= cls.Attributes.ge
                and (cls.Attributes.lt is None or value <  cls.Attributes.lt)
                and value <= cls.Attributes.le
            ))

_min_dt = datetime.datetime.min.replace(tzinfo=spyne.LOCAL_TZ)
_max_dt = datetime.datetime.max.replace(tzinfo=spyne.LOCAL_TZ)


class DateTime(SimpleModel):
    """A compact way to represent dates and times together. Supports time zones.
    Working with timezones is a bit quirky -- Spyne works very hard to have
    all datetimes with time zones internally and only strips them when
    explicitly requested with ``timezone=False``\\. See
    :attr:`DateTime.Attributes.as_timezone` for more information.

    Native type is :class:`datetime.datetime`.
    """

    __type_name__ = 'dateTime'
    Value = datetime.datetime

    _local_re = re.compile(DATETIME_PATTERN)
    _utc_re = re.compile(DATETIME_PATTERN + 'Z')
    _offset_re = re.compile(DATETIME_PATTERN + OFFSET_PATTERN)

    class Attributes(SimpleModel.Attributes):
        """Customizable attributes of the :class:`spyne.model.primitive.DateTime`
        type."""

        gt = None  # minExclusive
        """The datetime should be greater than this datetime. It must always
        have a timezone."""

        ge = _min_dt  # minInclusive
        """The datetime should be greater than or equal to this datetime. It
        must always have a timezone."""

        lt = None  # maxExclusive
        """The datetime should be lower than this datetime. It must always have
        a timezone."""

        le = _max_dt  # maxInclusive
        """The datetime should be lower than or equal to this datetime. It must
        always have a timezone."""

        pattern = None
        """A regular expression that matches the whole datetime. See here for
        more info: http://www.regular-expressions.info/xml.html"""

        dt_format = None
        """DateTime format fed to the ``strftime`` function. See:
        http://docs.python.org/library/datetime.html?highlight=strftime#strftime-strptime-behavior
        Ignored by protocols like SOAP which have their own ideas about how
        DateTime objects should be serialized."""

        out_format = None
        """DateTime format fed to the ``strftime`` function only when
        serializing. See:
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

        serialize_as = None
        """One of (None, 'sec', 'sec_float', 'msec', 'msec_float', 'usec')"""

        # TODO: Move this to ModelBase and make it work with all types in all
        # protocols.
        parser = None
        """Callable for string parser. It must accept exactly four arguments:
        `protocol, cls, string` and must return a `datetime.datetime` object.
        If this is not None, all other parsing configurations (e.g.
        `date_format`) are ignored.
        """

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
                # min_dt is also a valid value if gt is intact.
                    (cls.Attributes.gt is None or value > cls.Attributes.gt)
                and value >= cls.Attributes.ge
                # max_dt is also a valid value if lt is intact.
                and (cls.Attributes.lt is None or value < cls.Attributes.lt)
                and value <= cls.Attributes.le
            ))


class Date(DateTime):
    """Just that, Date. No time zone support.

    Native type is :class:`datetime.date`.
    """

    __type_name__ = 'date'

    _offset_re = re.compile(DATE_PATTERN + '(' + OFFSET_PATTERN + '|Z)')
    Value = datetime.date

    class Attributes(DateTime.Attributes):
        """Customizable attributes of the :class:`spyne.model.primitive.Date`
        type."""

        gt = None  # minExclusive
        """The date should be greater than this date."""

        ge = datetime.date(1, 1, 1)  # minInclusive
        """The date should be greater than or equal to this date."""

        lt = None  # maxExclusive
        """The date should be lower than this date."""

        le = datetime.date(datetime.MAXYEAR, 12, 31)  # maxInclusive
        """The date should be lower than or equal to this date."""

        date_format = None
        """Date format fed to the ``strftime`` function. See:
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
    Value = datetime.timedelta


NATIVE_MAP.update({
    datetime.datetime: DateTime,
    datetime.time: Time,
    datetime.date: Date,
    datetime.timedelta: Duration,
})
