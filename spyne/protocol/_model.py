
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


import decimal
import datetime
import math
import time
import pytz
import uuid

from collections import deque

from pytz import FixedOffset

from spyne.error import ValidationError
from spyne.model import nillable_string
from spyne.model import nillable_iterable
from spyne.model.binary import File
from spyne.model.binary import Attachment
from spyne.model.binary import binary_encoding_handlers
from spyne.model.binary import binary_decoding_handlers
from spyne.model.binary import BINARY_ENCODING_USE_DEFAULT
from spyne.model.primitive import _time_re
from spyne.model.primitive import _duration_re

try:
    from lxml import etree
    from lxml import html
except ImportError:
    etree = None
    html = None

__all__ = [
    'uuid_to_string', 'uuid_from_string',
    'null_to_string', 'null_from_string',
    'any_xml_to_string', 'any_xml_from_string',
    'any_html_to_string', 'any_html_from_string',
    'unicode_to_string', 'unicode_from_string',
    'string_from_string',
    'decimal_to_string', 'decimal_from_string',
    'double_to_string', 'double_from_string',
    'integer_to_string', 'integer_from_string',
    'time_to_string', 'time_from_string',
    'datetime_to_string', 'datetime_from_string', 'datetime_from_string_iso',
    'date_from_string', 'date_from_string_iso',
    'duration_to_string', 'duration_from_string',
    'boolean_to_string', 'boolean_from_string',
    'byte_array_to_string', 'byte_array_from_string', 'byte_array_to_string_iterable',
    'file_from_string', 'file_to_string_iterable',
    'attachment_to_string', 'attachment_from_string',
    'complex_model_base_to_string', 'complex_model_base_from_string',
    'simple_model_to_string_iterable',
]

def null_to_string(cls, value):
    return ""

def null_from_string(cls, value):
    return None


@nillable_string
def any_xml_to_string(cls, value):
    return etree.tostring(value)

@nillable_string
def any_xml_from_string(cls, string):
    try:
        return etree.fromstring(string)
    except etree.XMLSyntaxError, e:
        raise ValidationError(string, "%%r: %r" % e)

@nillable_string
def any_html_to_string(cls, value):
    return html.tostring(value)

@nillable_string
def any_html_from_string(cls, string):
    return html.fromstring(string)


@nillable_string
def uuid_to_string(cls, value):
    return str(value)

@nillable_string
def uuid_from_string(cls, string):
    return uuid.UUID(string)


@nillable_string
def unicode_to_string(cls, value):
    retval = value
    if cls.Attributes.encoding is not None and isinstance(value, unicode):
        retval = value.encode(cls.Attributes.encoding)
    if cls.Attributes.format is None:
        return retval
    else:
        return cls.Attributes.format % retval

@nillable_string
def unicode_from_string(cls, value):
    retval = value
    if isinstance(value, str):
        if cls.Attributes.encoding is None:
            retval = unicode(value, errors = cls.Attributes.unicode_errors)
        else:
            retval = unicode(value, cls.Attributes.encoding,
                                    errors = cls.Attributes.unicode_errors)
    return retval


@nillable_string
def string_from_string(cls, value):
    retval = value
    if isinstance(value, unicode):
        if cls.Attributes.encoding is None:
            raise Exception("You need to define an encoding to convert the "
                            "incoming unicode values to.")
        else:
            retval = value.encode(cls.Attributes.encoding)

    return retval


@nillable_string
def decimal_to_string(cls, value):
    decimal.Decimal(value)
    if cls.Attributes.str_format is not None:
        return cls.Attributes.str_format.format(value)
    elif cls.Attributes.format is not None:
        return cls.Attributes.format % value
    else:
        return str(value)

@nillable_string
def decimal_from_string(cls, string):
    if cls.Attributes.max_str_len is not None and len(string) > \
                                                     cls.Attributes.max_str_len:
        raise ValidationError(string, "Decimal %%r longer than %d characters"
                                                   % cls.Attributes.max_str_len)

    try:
        return decimal.Decimal(string)
    except decimal.InvalidOperation, e:
        raise ValidationError(string, "%%r: %r" % e)


@nillable_string
def double_to_string(cls, value):
    float(value) # sanity check

    if cls.Attributes.format is None:
        return repr(value)
    else:
        return cls.Attributes.format % value

@nillable_string
def double_from_string(cls, string):
    try:
        return float(string)
    except (TypeError, ValueError), e:
        raise ValidationError(string, "%%r: %r" % e)


@nillable_string
def integer_to_string(cls, value):
    int(value) # sanity check

    if cls.Attributes.format is None:
        return str(value)
    else:
        return cls.Attributes.format % value

@nillable_string
def integer_from_string(cls, string):
    if cls.Attributes.max_str_len is not None and len(string) > \
                                                     cls.Attributes.max_str_len:
        raise ValidationError(string, "Integer %%r longer than %d characters"
                                                   % cls.Attributes.max_str_len)

    try:
        return int(string)
    except ValueError:
        raise ValidationError(string, "Could not cast %r to integer")


@nillable_string
def time_to_string(cls, value):
    """Returns ISO formatted dates."""

    return value.isoformat()

@nillable_string
def time_from_string(cls, string):
    """Expects ISO formatted times."""

    match = _time_re.match(string)
    if match is None:
        raise ValidationError(string, "%%r does not match regex %r " %
                                                               _time_re.pattern)

    fields = match.groupdict(0)
    microsec = fields.get('sec_frac')
    if microsec is None or microsec == 0:
        microsec = 0
    else:
        microsec = int(microsec[1:])

    return datetime.time(int(fields['hr']), int(fields['min']),
                                                   int(fields['sec']), microsec)


@nillable_string
def datetime_to_string(cls, value):
    if cls.Attributes.as_time_zone is not None and value.tzinfo is not None:
        value = value.astimezone(cls.Attributes.as_time_zone) \
                                                    .replace(tzinfo=None)

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

@nillable_string
def datetime_from_string_iso(cls, string):
    match = cls._utc_re.match(string)
    if match:
        return cls.parse(match, tz=pytz.utc)

    match = cls._offset_re.match(string)
    if match:
        tz_hr, tz_min = [int(match.group(x)) for x in ("tz_hr", "tz_min")]
        return cls.parse(match, tz=FixedOffset(tz_hr * 60 + tz_min, {}))

    match = cls._local_re.match(string)
    if match is None:
        raise ValidationError(string)

    return cls.parse(match)

@nillable_string
def date_from_string_iso(cls, string):
    """This is used by protocols like SOAP who need ISO8601-formatted dates
    no matter what.
    """
    try:
        return datetime.date(*(time.strptime(string, '%Y-%m-%d')[0:3]))
    except ValueError:
        raise ValidationError(string)


@nillable_string
def datetime_from_string(cls, string):
    format = cls.Attributes.format

    if format is None:
        retval = datetime_from_string_iso(cls, string)
    else:
        retval = datetime.datetime.strptime(string, format)

    if cls.Attributes.as_time_zone is not None and retval.tzinfo is not None:
        retval = retval.astimezone(cls.Attributes.as_time_zone) \
                                                    .replace(tzinfo=None)

    return retval


@nillable_string
def date_from_string(cls, string):
    try:
        d = datetime.datetime.strptime(string, cls.Attributes.format)
        return datetime.date(d.year, d.month, d.day)
    except ValueError, e:
        raise ValidationError(string, "%%r: %r" % e)


if hasattr(datetime.timedelta, 'total_seconds'):
    def _total_seconds(td):
        return td.total_seconds()

else:
    def _total_seconds(td):
        return (td.microseconds +
                            (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6

@nillable_string
def duration_to_string(cls, value):
    if value.days < 0:
        value = -value
        negative = True
    else:
        negative = False

    tot_sec = _total_seconds(value)
    seconds = value.seconds % 60
    minutes = value.seconds / 60
    hours = minutes / 60
    minutes = minutes % 60
    seconds = float(seconds)
    useconds = value.microseconds

    retval = deque()
    if negative:
        retval.append("-P")
    else:
        retval.append("P")
    if value.days != 0:
        retval.extend([
            "%iD" % value.days,
            ])

    if tot_sec != 0 and tot_sec % 86400 == 0 and useconds == 0:
        return ''.join(retval)

    retval.append('T')

    if hours > 0:
        retval.append("%iH" % hours)

    if minutes > 0:
        retval.append("%iM" % minutes)

    if seconds > 0 or useconds > 0:
        retval.append("%i" % seconds)
        if useconds > 0:
            retval.append(".%i" % useconds)
        retval.append("S")

    if len(retval) == 2:
        retval.append('0S')

    return ''.join(retval)

@nillable_string
def duration_from_string(cls, string):
    duration = _duration_re.match(string).groupdict(0)
    if duration is None:
        raise ValidationError("time data '%s' does not match regex '%s'" %(string, _duration_re.pattern))

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


@nillable_string
def boolean_to_string(cls, value):
    return str(bool(value)).lower()

@nillable_string
def boolean_from_string(cls, string):
    return (string.lower() in ['true', '1'])


@nillable_string
def byte_array_from_string(cls, value, suggested_encoding=None):
    encoding = cls.Attributes.encoding
    if encoding is BINARY_ENCODING_USE_DEFAULT:
        encoding = suggested_encoding
    return binary_decoding_handlers[encoding](value)

@nillable_string
def byte_array_to_string(cls, value, suggested_encoding=None):
    encoding = cls.Attributes.encoding
    if encoding is BINARY_ENCODING_USE_DEFAULT:
        encoding = suggested_encoding
    return binary_encoding_handlers[suggested_encoding](value)

@nillable_iterable
def byte_array_to_string_iterable(prot, cls, value):
    return value


@nillable_string
def file_from_string(cls, value, suggested_encoding=None):
    encoding = cls.Attributes.encoding
    if encoding is BINARY_ENCODING_USE_DEFAULT:
        encoding = suggested_encoding

    return File.Value(data=binary_decoding_handlers[encoding](value))


def _file_to_iter(f):
    data = f.read(65536)
    while len(data) > 0:
        yield data
        data = f.read(65536)

    f.close()

@nillable_iterable
def file_to_string_iterable(prot, cls, value):
    if value.data is None:
        if value.handle is None:
            assert value.path is not None, "You need to write data to " \
                        "persistent storage first if you want to read it back."

            f = open(value.path, 'rb')

        else:
            f = value.handle
            f.seek(0)

        return _file_to_iter(f)

    else:
        return iter(value.data)

@nillable_iterable
def simple_model_to_string_iterable(prot, cls, value):
    retval = prot.to_string(cls, value)
    if retval is None:
        return ('',)
    return (retval,)

@nillable_string
def attachment_to_string(cls, value):
    if not (value.data is None):
        # the data has already been loaded, just encode
        # and return the element
        data = value.data

    elif not (value.file_name is None):
        # the data hasn't been loaded, but a file has been
        # specified
        data = open(value.file_name, 'rb').read()

    else:
        raise ValueError("Neither data nor a file_name has been specified")

    return data

@nillable_string
def attachment_from_string(cls, value):
    return Attachment(data=value)


@nillable_string
def complex_model_base_to_string(cls, value):
    raise TypeError("Only primitives can be serialized to string.")

@nillable_string
def complex_model_base_from_string(cls, string):
    raise TypeError("Only primitives can be deserialized from string.")
