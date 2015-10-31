
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

from __future__ import print_function

import logging
logger = logging.getLogger(__name__)

import re
import pytz
import uuid

from datetime import timedelta, time, datetime, date
from math import modf
from decimal import Decimal as D, InvalidOperation
from pytz import FixedOffset
from time import strptime, mktime

try:
    from lxml import etree
    from lxml import html
except ImportError:
    etree = None
    html = None

from spyne.protocol._base import ProtocolMixin
from spyne.model import ModelBase, XmlAttribute, Array, Null, \
    ByteArray, File, ComplexModelBase, AnyXml, AnyHtml, Unicode, String, \
    Decimal, Double, Integer, Time, DateTime, Uuid, Date, Duration, Boolean

from spyne.error import ValidationError

from spyne.model.binary import binary_decoding_handlers, BINARY_ENCODING_USE_DEFAULT

from spyne.util import six
from spyne.model.enum import EnumBase
from spyne.model.binary import Attachment  # DEPRECATED
from spyne.model.primitive.datetime import TIME_PATTERN, DATE_PATTERN

from spyne.util.cdict import cdict


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


class InProtocolBase(ProtocolMixin):
    """This is the abstract base class for all input protocol implementations.
    Child classes can implement only the required subset of the public methods.

    An output protocol must implement :func:`serialize` and
    :func:`create_out_string`.

    An input protocol must implement :func:`create_in_document`,
    :func:`decompose_incoming_envelope` and :func:`deserialize`.

    The ProtocolBase class supports the following events:

    * ``before_deserialize``:
      Called before the deserialization operation is attempted.

    * ``after_deserialize``:
      Called after the deserialization operation is finished.

    The arguments the constructor takes are as follows:

    :param app: The application this protocol belongs to.
    :param mime_type: The mime_type this protocol should set for transports
        that support this. This is a quick way to override the mime_type by
        default instead of subclassing the releavant protocol implementation.
    """

    def __init__(self, app=None, validator=None, mime_type=None,
                                   ignore_wrappers=False, binary_encoding=None):

        self.validator = None

        super(InProtocolBase, self).__init__(app=app, mime_type=mime_type,
               ignore_wrappers=ignore_wrappers, binary_encoding=binary_encoding)

        self.message = None
        self.validator = None
        self.set_validator(validator)

        if self.binary_encoding is None:
            self.binary_encoding = self.default_binary_encoding

        if mime_type is not None:
            self.mime_type = mime_type

        fsh = {
            Null: self.null_from_string,
            Time: self.time_from_string,
            Date: self.date_from_string,
            Uuid: self.uuid_from_string,
            File: self.file_from_string,
            Array: self.array_from_string,
            Double: self.double_from_string,
            String: self.string_from_string,
            AnyXml: self.any_xml_from_string,
            Boolean: self.boolean_from_string,
            Integer: self.integer_from_string,
            Unicode: self.unicode_from_string,
            Decimal: self.decimal_from_string,
            AnyHtml: self.any_html_from_string,
            DateTime: self.datetime_from_string,
            Duration: self.duration_from_string,
            ByteArray: self.byte_array_from_string,
            EnumBase: self.enum_base_from_string,
            ModelBase: self.model_base_from_string,
            Attachment: self.attachment_from_string,
            XmlAttribute: self.xmlattribute_from_string,
            ComplexModelBase: self.complex_model_base_from_string
        }

        self._from_string_handlers = cdict(fsh)
        self._from_unicode_handlers = cdict(fsh)

        self._datetime_dsmap = {
            None: self._datetime_from_string,
            'sec': self._datetime_from_sec,
            'sec_float': self._datetime_from_sec_float,
            'msec': self._datetime_from_msec,
            'msec_float': self._datetime_from_msec_float,
            'usec': self._datetime_from_usec,
        }

    def _datetime_from_sec(self, cls, value):
        try:
            return datetime.fromtimestamp(value)
        except TypeError:
            logger.error("Invalid value %r", value)
            raise

    def _datetime_from_sec_float(self, cls, value):
        try:
            return datetime.fromtimestamp(value)
        except TypeError:
            logger.error("Invalid value %r", value)
            raise

    def _datetime_from_msec(self, cls, value):
        try:
            return datetime.fromtimestamp(value // 1000)
        except TypeError:
            logger.error("Invalid value %r", value)
            raise

    def _datetime_from_msec_float(self, cls, value):
        try:
            return datetime.fromtimestamp(value / 1000)
        except TypeError:
            logger.error("Invalid value %r", value)
            raise

    def _datetime_from_usec(self, cls, value):
        try:
            return datetime.fromtimestamp(value / 1e6)
        except TypeError:
            logger.error("Invalid value %r", value)
            raise

    def create_in_document(self, ctx, in_string_encoding=None):
        """Uses ``ctx.in_string`` to set ``ctx.in_document``."""

    def decompose_incoming_envelope(self, ctx, message):
        """Sets the ``ctx.method_request_string``, ``ctx.in_body_doc``,
        ``ctx.in_header_doc`` and ``ctx.service`` properties of the ctx object,
        if applicable.
        """

    def deserialize(self, ctx, message):
        """Takes a MethodContext instance and a string containing ONE document
        instance in the ``ctx.in_string`` attribute.

        Returns the corresponding native python object in the ctx.in_object
        attribute.
        """

    def validate_document(self, payload):
        """Method to be overriden to perform any sort of custom input
        validation on the parsed input document.
        """

    def set_validator(self, validator):
        """You must override this function if you want your protocol to support
        validation."""

        assert validator is None

        self.validator = None

    def from_string(self, class_, string, *args, **kwargs):
        if string is None:
            return None

        if six.PY3:
            assert isinstance(string, bytes)

        if isinstance(string, six.string_types) and \
                           len(string) == 0 and class_.Attributes.empty_is_none:
            return None

        handler = self._from_string_handlers[class_]
        return handler(class_, string, *args, **kwargs)

    def from_unicode(self, class_, string, *args, **kwargs):
        if string is None:
            return None

        if six.PY3:
            assert isinstance(string, str)

        if isinstance(string, six.string_types) and len(string) == 0 and \
                                                class_.Attributes.empty_is_none:
            return None

        handler = self._from_unicode_handlers[class_]
        return handler(class_, string, *args, **kwargs)

    def null_from_string(self, cls, value):
        return None

    def any_xml_from_string(self, cls, string):
        try:
            return etree.fromstring(string)
        except etree.XMLSyntaxError as e:
            raise ValidationError(string, "%%r: %r" % e)

    def any_html_from_string(self, cls, string):
        try:
            return html.fromstring(string)
        except etree.ParserError as e:
            if e.args[0] == "Document is empty":
                pass
            else:
                raise

    def uuid_from_string(self, cls, string, suggested_encoding=None):
        attr = self.get_cls_attrs(cls)
        ser_as = attr.serialize_as
        encoding = attr.encoding

        if encoding is None:
            encoding = suggested_encoding

        retval = string

        if ser_as in ('bytes', 'bytes_le'):
            retval, = binary_decoding_handlers[encoding](string)

        retval = _uuid_deserialize[ser_as](retval)

        return retval

    def unicode_from_string(self, cls, value):
        retval = value
        cls_attrs = self.get_cls_attrs(cls)
        if isinstance(value, six.binary_type):
            if cls_attrs.encoding is None:
                retval = six.text_type(value,
                                           errors=cls_attrs.unicode_errors)
            else:
                retval = six.text_type(value, cls_attrs.encoding,
                                           errors=cls_attrs.unicode_errors)
        return retval

    def string_from_string(self, cls, value):
        retval = value
        cls_attrs = self.get_cls_attrs(cls)
        if isinstance(value, six.text_type):
            if cls_attrs.encoding is None:
                raise Exception("You need to define a source encoding for "
                                "decoding incoming unicode values.")
            else:
                retval = value.encode(cls_attrs.encoding)

        return retval

    def decimal_from_string(self, cls, string):
        cls_attrs = self.get_cls_attrs(cls)
        if cls_attrs.max_str_len is not None and len(string) > \
                                                     cls_attrs.max_str_len:
            raise ValidationError(string, "Decimal %%r longer than %d "
                                          "characters" % cls_attrs.max_str_len)

        try:
            return D(string)
        except InvalidOperation as e:
            raise ValidationError(string, "%%r: %r" % e)

    def double_from_string(self, cls, string):
        try:
            return float(string)
        except (TypeError, ValueError) as e:
            raise ValidationError(string, "%%r: %r" % e)

    def integer_from_string(self, cls, string):
        cls_attrs = self.get_cls_attrs(cls)
        if isinstance(string, six.string_types) and \
                                    cls_attrs.max_str_len is not None and \
                                    len(string) > cls_attrs.max_str_len:
            raise ValidationError(string,
                                    "Integer %%r longer than %d characters"
                                                   % cls_attrs.max_str_len)

        try:
            return int(string)
        except ValueError:
            raise ValidationError(string, "Could not cast %r to integer")

    def time_from_string(self, cls, string):
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
            microsec = min(999999, int(round(float(microsec) * 1e6)))

        return time(int(fields['hr']), int(fields['min']),
                                                   int(fields['sec']), microsec)

    def date_from_string_iso(self, cls, string):
        """This is used by protocols like SOAP who need ISO8601-formatted dates
        no matter what.
        """

        try:
            return date(*(strptime(string, '%Y-%m-%d')[0:3]))

        except ValueError:
            match = cls._offset_re.match(string)

            if match:
                year = int(match.group('year'))
                month = int(match.group('month'))
                day = int(match.group('day'))

                return date(year, month, day)

            raise ValidationError(string)

    def enum_base_from_string(self, cls, value):
        if self.validator is self.SOFT_VALIDATION and not (
                                        cls.validate_string(cls, value)):
            raise ValidationError(value)
        return getattr(cls, value)

    def model_base_from_string(self, cls, value):
        return cls.from_string(value)

    def datetime_from_string_iso(self, cls, string):
        astz = self.get_cls_attrs(cls).as_timezone

        match = cls._utc_re.match(string)
        if match:
            tz = pytz.utc
            retval = _parse_datetime_iso_match(match, tz=tz)
            if astz is not None:
                retval = retval.astimezone(astz)
            return retval

        if match is None:
            match = cls._offset_re.match(string)
            if match:
                tz_hr, tz_min = [int(match.group(x))
                                                   for x in ("tz_hr", "tz_min")]
                tz = FixedOffset(tz_hr * 60 + tz_min, {})
                retval = _parse_datetime_iso_match(match, tz=tz)
                if astz is not None:
                    retval = retval.astimezone(astz)
                return retval

        if match is None:
            match = cls._local_re.match(string)
            if match:
                retval = _parse_datetime_iso_match(match)
                if astz:
                    retval = retval.replace(tzinfo=astz)
                return retval

        raise ValidationError(string)

    def datetime_from_string(self, cls, string):
        serialize_as = self.get_cls_attrs(cls).serialize_as
        return self._datetime_dsmap[serialize_as](cls, string)

    def date_from_string(self, cls, string):
        try:
            d = datetime.strptime(string, self.get_cls_attrs(cls).format)
            return date(d.year, d.month, d.day)
        except ValueError as e:
            match = cls._offset_re.match(string)
            if match:
                return date(int(match.group('year')),
                            int(match.group('month')), int(match.group('day')))
            else:
                raise ValidationError(string,
                                         "%%r: %s" % repr(e).replace("%", "%%"))

    def duration_from_string(self, cls, string):
        duration = _duration_re.match(string).groupdict(0)
        if duration is None:
            raise ValidationError("time data '%s' does not match regex '%s'" %
                                                 (string, _duration_re.pattern))

        days = int(duration['days'])
        days += int(duration['months']) * 30
        days += int(duration['years']) * 365
        hours = int(duration['hours'])
        minutes = int(duration['minutes'])
        seconds = float(duration['seconds'])
        f, i = modf(seconds)
        seconds = i
        microseconds = int(1e6 * f)

        delta = timedelta(days=days, hours=hours, minutes=minutes,
            seconds=seconds, microseconds=microseconds)

        if duration['sign'] == "-":
            delta *= -1

        return delta

    def boolean_from_string(self, cls, string):
        return string.lower() in ('true', '1')

    def byte_array_from_string(self, cls, value, suggested_encoding=None):
        encoding = self.get_cls_attrs(cls).encoding
        if encoding is BINARY_ENCODING_USE_DEFAULT:
            encoding = suggested_encoding
        return binary_decoding_handlers[encoding](value)

    def file_from_string(self, cls, value, suggested_encoding=None):
        encoding = self.get_cls_attrs(cls).encoding
        if encoding is BINARY_ENCODING_USE_DEFAULT:
            encoding = suggested_encoding

        return File.Value(data=binary_decoding_handlers[encoding](value))

    def attachment_from_string(self, cls, value):
        return Attachment(data=value)

    def complex_model_base_from_string(self, cls, string, **_):
        raise TypeError("Only primitives can be deserialized from string.")

    def array_from_string(self, cls, string, **_):
        if self.get_cls_attrs(cls).serialize_as != 'sd-list':
            raise TypeError("Only primitives can be deserialized from string.")

        # sd-list being space-delimited list.
        retval = []
        inner_type, = cls._type_info.values()
        for s in string.split():
            retval.append(self.from_string(inner_type, s))

        return retval

    def xmlattribute_from_string(self, cls, value):
        return self.from_string(cls.type, value)

    def _datetime_from_string(self, cls, string):
        cls_attrs = self.get_cls_attrs(cls)
        date_format = cls_attrs.date_format
        if date_format is None:
            date_format = cls_attrs.out_format
        if date_format is None:
            date_format = cls_attrs.format

        if date_format is None:
            retval = self.datetime_from_string_iso(cls, string)
        else:
            astz = cls_attrs.as_timezone
            if six.PY2:
                # FIXME: perhaps it should encode to string's encoding instead
                # of utf8 all the time
                if isinstance(date_format, unicode):
                    date_format = date_format.encode('utf8')
                if isinstance(string, unicode):
                    string = string.encode('utf8')

            retval = datetime.strptime(string, date_format)

            if astz:
                retval = retval.astimezone(cls_attrs.as_time_zone)

        return retval


_uuid_deserialize = {
    None: lambda s: uuid.UUID(s),
    'hex': lambda s: uuid.UUID(hex=s),
    'urn': lambda s: uuid.UUID(hex=s),
    'bytes': lambda s: uuid.UUID(bytes=s),
    'bytes_le': lambda s: uuid.UUID(bytes_le=s),
    'fields': lambda s: uuid.UUID(fields=s),
    'int': lambda s: uuid.UUID(int=s),
    ('int', int): lambda s: uuid.UUID(int=s),
    ('int', str): lambda s: uuid.UUID(int=int(s)),
}

if six.PY2:
    _uuid_deserialize[('int', long)] = _uuid_deserialize[('int', int)]


def _parse_datetime_iso_match(date_match, tz=None):
    fields = date_match.groupdict()

    year = int(fields.get('year'))
    month = int(fields.get('month'))
    day = int(fields.get('day'))
    hour = int(fields.get('hr'))
    minute = int(fields.get('min'))
    second = int(fields.get('sec'))
    usecond = fields.get("sec_frac")
    if usecond is None:
        usecond = 0
    else:
        # we only get the most significant 6 digits because that's what
        # datetime can handle.
        usecond = min(999999, int(round(float(usecond) * 1e6)))

    return datetime(year, month, day, hour, minute, second, usecond, tz)


_dt_sec = lambda cls, val: \
        int(mktime(val.timetuple()))
_dt_sec_float = lambda cls, val: \
        mktime(val.timetuple()) + (val.microsecond / 1e6)

_dt_msec = lambda cls, val: \
        int(mktime(val.timetuple())) * 1000 + (val.microsecond // 1000)
_dt_msec_float = lambda cls, val: \
        mktime(val.timetuple()) * 1000 + (val.microsecond / 1000.0)

_dt_usec = lambda cls, val: \
        int(mktime(val.timetuple())) * 1000000 + val.microsecond

_datetime_smap = {
    'sec': _dt_sec,
    'secs': _dt_sec,
    'second': _dt_sec,
    'seconds': _dt_sec,

    'sec_float': _dt_sec_float,
    'secs_float': _dt_sec_float,
    'second_float': _dt_sec_float,
    'seconds_float': _dt_sec_float,

    'msec': _dt_msec,
    'msecs': _dt_msec,
    'msecond': _dt_msec,
    'mseconds': _dt_msec,
    'millisecond': _dt_msec,
    'milliseconds': _dt_msec,

    'msec_float': _dt_msec_float,
    'msecs_float': _dt_msec_float,
    'msecond_float': _dt_msec_float,
    'mseconds_float': _dt_msec_float,
    'millisecond_float': _dt_msec_float,
    'milliseconds_float': _dt_msec_float,

    'usec': _dt_usec,
    'usecs': _dt_usec,
    'usecond': _dt_usec,
    'useconds': _dt_usec,
    'microsecond': _dt_usec,
    'microseconds': _dt_usec,
}


def _file_to_iter(f):
    try:
        data = f.read(65536)
        while len(data) > 0:
            yield data
            data = f.read(65536)

    finally:
        f.close()
