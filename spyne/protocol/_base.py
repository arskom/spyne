
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

import logging
logger = logging.getLogger(__name__)

import pytz
import uuid

from copy import copy
from collections import deque
from datetime import timedelta, time, datetime, date
from math import modf
from decimal import Decimal as D, InvalidOperation
from pytz import FixedOffset

try:
    from lxml import etree
    from lxml import html
except ImportError:
    etree = None
    html = None

from spyne import EventManager

from spyne.const.http import HTTP_400
from spyne.const.http import HTTP_401
from spyne.const.http import HTTP_404
from spyne.const.http import HTTP_405
from spyne.const.http import HTTP_413
from spyne.const.http import HTTP_500

from spyne.error import Fault
from spyne.error import ResourceNotFoundError
from spyne.error import RequestTooLongError
from spyne.error import RequestNotAllowed
from spyne.error import InvalidCredentialsError
from spyne.error import ValidationError

from spyne.model.binary import Attachment
from spyne.model.binary import binary_encoding_handlers
from spyne.model.binary import binary_decoding_handlers
from spyne.model.binary import BINARY_ENCODING_USE_DEFAULT
from spyne.model.primitive import _time_re
from spyne.model.primitive import _duration_re

from spyne.model import ModelBase, XmlAttribute
from spyne.model import SimpleModel
from spyne.model import Null
from spyne.model import ByteArray
from spyne.model import File
from spyne.model import ComplexModelBase
from spyne.model import AnyXml
from spyne.model import AnyHtml
from spyne.model import Unicode
from spyne.model import String
from spyne.model import Decimal
from spyne.model import Double
from spyne.model import Integer
from spyne.model import Time
from spyne.model import DateTime
from spyne.model import Uuid
from spyne.model import Date
from spyne.model import Duration
from spyne.model import Boolean
from spyne.model.binary import Attachment # DEPRECATED
from spyne.util import DefaultAttrDict, memoize_id, six

from spyne.util.cdict import cdict


class ProtocolBase(object):
    """This is the abstract base class for all protocol implementations. Child
    classes can implement only the required subset of the public methods.

    An output protocol must implement :func:`serialize` and
    :func:`create_out_string`.

    An input protocol must implement :func:`create_in_document`,
    :func:`decompose_incoming_envelope` and :func:`deserialize`.

    The ProtocolBase class supports the following events:

    * ``before_deserialize``:
      Called before the deserialization operation is attempted.

    * ``after_deserialize``:
      Called after the deserialization operation is finished.

    * ``before_serialize``:
      Called before after the serialization operation is attempted.

    * ``after_serialize``:
      Called after the serialization operation is finished.

    The arguments the constructor takes are as follows:

    :param app: The application this protocol belongs to.
    :param validator: The type of validation this protocol should do on
        incoming data.
    :param mime_type: The mime_type this protocol should set for transports
        that support this. This is a quick way to override the mime_type by
        default instead of subclassing the releavant protocol implementation.
    :param ignore_uncap: Silently ignore cases when the protocol is not capable
        of serializing return values instead of raising a TypeError.
    """

    mime_type = 'application/octet-stream'

    SOFT_VALIDATION = type("Soft", (object,), {})
    REQUEST = type("Request", (object,), {})
    RESPONSE = type("Response", (object,), {})

    type = set()
    """Set that contains keywords about a protocol."""

    default_binary_encoding = None

    def __init__(self, app=None, validator=None, mime_type=None,
                                       ignore_uncap=False, ignore_wrappers=False):
        self.__app = None
        self.set_app(app)

        self.validator = None
        self.set_validator(validator)

        self.event_manager = EventManager(self)
        self.ignore_uncap = ignore_uncap
        self.ignore_wrappers = ignore_wrappers
        self.message = None

        if mime_type is not None:
            self.mime_type = mime_type

        self._to_string_handlers = cdict({
            ModelBase: self.model_base_to_string,
            Time: self.time_to_string,
            Uuid: self.uuid_to_string,
            Null: self.null_to_string,
            Double: self.double_to_string,
            AnyXml: self.any_xml_to_string,
            Unicode: self.unicode_to_string,
            Boolean: self.boolean_to_string,
            Decimal: self.decimal_to_string,
            Integer: self.integer_to_string,
            AnyHtml: self.any_html_to_string,
            DateTime: self.datetime_to_string,
            Duration: self.duration_to_string,
            ByteArray: self.byte_array_to_string,
            Attachment: self.attachment_to_string,
            XmlAttribute: self.xmlattribute_to_string,
            ComplexModelBase: self.complex_model_base_to_string,
        })

        self._to_string_iterable_handlers = cdict({
            File: self.file_to_string_iterable,
            ByteArray: self.byte_array_to_string_iterable,
            ModelBase: self.model_base_to_string_iterable,
            SimpleModel: self.simple_model_to_string_iterable,
            ComplexModelBase: self.complex_model_to_string_iterable,
        })

        self._from_string_handlers = cdict({
            Null: self.null_from_string,
            Time: self.time_from_string,
            Date: self.date_from_string,
            Uuid: self.uuid_from_string,
            File: self.file_from_string,
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
            ModelBase: self.model_base_from_string,
            Attachment: self.attachment_from_string,
            ComplexModelBase: self.complex_model_base_from_string
        })

    @property
    def app(self):
        return self.__app

    def set_app(self, value):
        assert self.__app is None, "One protocol instance should belong to one " \
                                   "application instance. It currently belongs " \
                                   "to: %r" % self.__app
        self.__app = value

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

    def serialize(self, ctx, message):
        """Serializes ``ctx.out_object``.

        If ctx.out_stream is not None,  ``ctx.out_document`` and
        ``ctx.out_string`` are skipped and the response is written directly to
        ``ctx.out_stream``.

        :param ctx: :class:`MethodContext` instance.
        :param message: One of ``(ProtocolBase.REQUEST, ProtocolBase.RESPONSE)``.
        """

    def create_out_string(self, ctx, out_string_encoding=None):
        """Uses ctx.out_document to set ctx.out_string"""

    def validate_document(self, payload):
        """Method to be overriden to perform any sort of custom input
        validation on the parsed input document.
        """

    def generate_method_contexts(self, ctx):
        """Generates MethodContext instances for every callable assigned to the
        given method handle.

        The first element in the returned list is always the primary method
        context whereas the rest are all auxiliary method contexts.
        """

        call_handles = self.get_call_handles(ctx)
        if len(call_handles) == 0:
            raise ResourceNotFoundError(ctx.method_request_string)

        retval = []
        for d in call_handles:
            assert d is not None

            c = copy(ctx)
            c.descriptor = d
            retval.append(c)

        return retval

    def get_call_handles(self, ctx):
        """Method to be overriden to perform any sort of custom method mapping
        using any data in the method context. Returns a list of contexts.
        Can return multiple contexts if a method_request_string matches more
        than one function. (This is called the fanout mode.)
        """

        name = ctx.method_request_string
        if not name.startswith("{"):
            name = '{%s}%s' % (self.app.interface.get_tns(), name)

        call_handles = self.app.interface.service_method_map.get(name, [])

        return call_handles

    def fault_to_http_response_code(self, fault):
        """Special function to convert native Python exceptions to Http response
        codes.
        """

        if isinstance(fault, RequestTooLongError):
            return HTTP_413
        if isinstance(fault, ResourceNotFoundError):
            return HTTP_404
        if isinstance(fault, RequestNotAllowed):
            return HTTP_405
        if isinstance(fault, InvalidCredentialsError):
            return HTTP_401
        if isinstance(fault, Fault) and (fault.faultcode.startswith('Client.')
                                                or fault.faultcode == 'Client'):
            return HTTP_400

        return HTTP_500

    def set_validator(self, validator):
        """You must override this function if you want your protocol to support
        validation."""

        assert validator is None

        self.validator = None

    def from_string(self, class_, string, *args, **kwargs):
        if string is None:
            return None

        handler = self._from_string_handlers[class_]
        return handler(class_, string, *args, **kwargs)

    def to_string(self, class_, value, *args, **kwargs):
        if value is None:
            return None

        handler = self._to_string_handlers[class_]
        return handler(class_, value, *args, **kwargs)

    def to_string_iterable(self, class_, value):
        if value is None:
            return []

        handler = self._to_string_iterable_handlers[class_]
        return handler(self, class_, value)

    @memoize_id
    def get_cls_attrs(self, cls):
        attr = DefaultAttrDict([(k, getattr(cls.Attributes, k))
                        for k in dir(cls.Attributes) if not k.startswith('__')])
        if cls.Attributes.prot_attrs:
            attr.update(cls.Attributes.prot_attrs.get(self.__class__, {}))
            attr.update(cls.Attributes.prot_attrs.get(self, {}))
        return attr

    def null_to_string(self, cls, value):
        return ""

    def null_from_string(self, cls, value):
        return None

    def any_xml_to_string(self, cls, value):
        return etree.tostring(value)

    def any_xml_from_string(self, cls, string):
        try:
            return etree.fromstring(string)
        except etree.XMLSyntaxError as e:
            raise ValidationError(string, "%%r: %r" % e)

    def any_html_to_string(self, cls, value):
        return html.tostring(value)

    def any_html_from_string(self, cls, string):
        return html.fromstring(string)

    def uuid_to_string(self, cls, value):
        return _uuid_serialize[cls.Attributes.serialize_as](value)

    def uuid_from_string(self, cls, string):
        return _uuid_deserialize[cls.Attributes.serialize_as](string)

    def unicode_to_string(self, cls, value):
        retval = value
        if cls.Attributes.encoding is not None and isinstance(value, six.text_type):
            retval = value.encode(cls.Attributes.encoding)
        if cls.Attributes.format is None:
            return retval
        else:
            return cls.Attributes.format % retval

    def unicode_from_string(self, cls, value):
        retval = value
        if isinstance(value, str):
            if cls.Attributes.encoding is None:
                retval = six.text_type(value, errors=cls.Attributes.unicode_errors)
            else:
                retval = six.text_type(value, cls.Attributes.encoding,
                                              errors=cls.Attributes.unicode_errors)
        return retval

    def string_from_string(self, cls, value):
        retval = value
        if isinstance(value, six.text_type):
            if cls.Attributes.encoding is None:
                raise Exception("You need to define an encoding to convert the "
                                "incoming unicode values to.")
            else:
                retval = value.encode(cls.Attributes.encoding)

        return retval

    def decimal_to_string(self, cls, value):
        D(value)
        if cls.Attributes.str_format is not None:
            return cls.Attributes.str_format.format(value)
        elif cls.Attributes.format is not None:
            return cls.Attributes.format % value
        else:
            return str(value)

    def decimal_from_string(self, cls, string):
        if cls.Attributes.max_str_len is not None and len(string) > \
                                                     cls.Attributes.max_str_len:
            raise ValidationError(string, "Decimal %%r longer than %d characters"
                                                   % cls.Attributes.max_str_len)

        try:
            return D(string)
        except InvalidOperation as e:
            raise ValidationError(string, "%%r: %r" % e)

    def double_to_string(self, cls, value):
        float(value) # sanity check

        if cls.Attributes.format is None:
            return repr(value)
        else:
            return cls.Attributes.format % value

    def double_from_string(self, cls, string):
        try:
            return float(string)
        except (TypeError, ValueError) as e:
            raise ValidationError(string, "%%r: %r" % e)

    def integer_to_string(self, cls, value):
        int(value) # sanity check

        if cls.Attributes.format is None:
            return str(value)
        else:
            return cls.Attributes.format % value

    def integer_from_string(cls, string):
        if cls.Attributes.max_str_len is not None and len(string) > \
                                                     cls.Attributes.max_str_len:
            raise ValidationError(string,
                                    "Integer %%r longer than %d characters"
                                                   % cls.Attributes.max_str_len)

        try:
            return int(string)
        except ValueError:
            raise ValidationError(string, "Could not cast %r to integer")

    def time_to_string(self, cls, value):
        """Returns ISO formatted dates."""

        return value.isoformat()

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
            microsec = int(round(float(microsec) * 1e6))

        return time(int(fields['hr']), int(fields['min']),
                                                   int(fields['sec']), microsec)

    def datetime_to_string(self, cls, val):
        return _datetime_smap[cls.Attributes.serialize_as](cls, val)

    def date_from_string_iso(self, cls, string):
        """This is used by protocols like SOAP who need ISO8601-formatted dates
        no matter what.
        """
        try:
            return date(*(time.strptime(string, '%Y-%m-%d')[0:3]))
        except ValueError:
            match = cls._offset_re.match(string)
            if match:
                return date(int(match.group('year')), int(match.group('month')), int(match.group('day')))
            else:
                raise ValidationError(string)

    def model_base_from_string(self, cls, value):
        return cls.from_string(value)

    def datetime_from_string(self, cls, string):
        return _datetime_dsmap[cls.Attributes.serialize_as](cls, string)

    def date_from_string(self, cls, string):
        try:
            d = datetime.strptime(string, cls.Attributes.format)
            return date(d.year, d.month, d.day)
        except ValueError as e:
            match = cls._offset_re.match(string)
            if match:
                return date(int(match.group('year')),
                                int(match.group('month')), int(match.group('day')))
            else:
                raise ValidationError(string, "%%r: %s" % repr(e).replace("%", "%%"))

    def duration_to_string(self, cls, value):
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

    def boolean_to_string(self, cls, value):
        return str(bool(value)).lower()

    def boolean_from_string(self, cls, string):
        return (string.lower() in ['true', '1'])

    def byte_array_from_string(self, cls, value, suggested_encoding=None):
        encoding = cls.Attributes.encoding
        if encoding is BINARY_ENCODING_USE_DEFAULT:
            encoding = suggested_encoding
        return binary_decoding_handlers[encoding](value)

    def byte_array_to_string(self, cls, value, suggested_encoding=None):
        encoding = cls.Attributes.encoding
        if encoding is BINARY_ENCODING_USE_DEFAULT:
            encoding = suggested_encoding
        return binary_encoding_handlers[encoding](value)

    def byte_array_to_string_iterable(self, cls, value):
        return value

    def file_from_string(self, cls, value, suggested_encoding=None):
        encoding = cls.Attributes.encoding
        if encoding is BINARY_ENCODING_USE_DEFAULT:
            encoding = suggested_encoding

        return File.Value(data=binary_decoding_handlers[encoding](value))

    def file_to_string_iterable(self, cls, value):
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

    def simple_model_to_string_iterable(self, cls, value):
        retval = self.to_string(cls, value)
        if retval is None:
            return ('',)
        return (retval,)

    def complex_model_to_string_iterable(self, cls, value):
        if self.ignore_uncap:
            return tuple()
        raise TypeError("HttpRpc protocol can only serialize primitives.")

    def attachment_to_string(self, cls, value):
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

    def attachment_from_string(self, cls, value):
        return Attachment(data=value)

    def complex_model_base_to_string(self, cls, value):
        raise TypeError("Only primitives can be serialized to string.")

    def complex_model_base_from_string(self, cls, string):
        raise TypeError("Only primitives can be deserialized from string.")

    def xmlattribute_to_string(self, cls, string):
        return self.to_string(cls.type, string)

    def xmlattribute_from_string(self, cls, value):
        return self.from_string(cls.type, value)

    def model_base_to_string_iterable(self, cls, value):
        return cls.to_string_iterable(value)

    def model_base_to_string(self, cls, value):
        return cls.to_string(value)

_uuid_serialize = {
    None: str,
    'hex': lambda u:u.hex,
    'urn': lambda u:u.urn,
    'bytes': lambda u:u.bytes,
    'bytes_le': lambda u:u.bytes_le,
    'fields': lambda u:u.fields,
    'int': lambda u:u.int,
}

if six.PY3:
    long = int

_uuid_deserialize = {
    None: lambda s: uuid.UUID(s),
    'hex': lambda s: uuid.UUID(hex=s),
    'urn': lambda s: uuid.UUID(hex=s),
    'bytes': lambda s: uuid.UUID(bytes=s),
    'bytes_le': lambda s: uuid.UUID(bytes_le=s),
    'fields': lambda s: uuid.UUID(fields=s),
    'int': lambda s: _uuid_deserialize[('int', type(s))](s),
    ('int', int): lambda s: uuid.UUID(int=s),
    ('int', long): lambda s: uuid.UUID(int=s),
    ('int', str): lambda s: uuid.UUID(int=int(s)),
}


if hasattr(timedelta, 'total_seconds'):
    def _total_seconds(td):
        return td.total_seconds()

else:
    def _total_seconds(td):
        return (td.microseconds + (td.seconds + td.days * 24 * 3600) *1e6) / 1e6


def _datetime_from_string(cls, string):
    attrs = cls.Attributes
    format = attrs.format

    if format is None:
        retval = datetime_from_string_iso(cls, string)
    else:
        astz = cls.Attributes.as_timezone

        retval = datetime.strptime(string, format)
        if astz:
            retval = retval.astimezone(cls.Attributes.as_time_zone)

    return retval

_datetime_dsmap = {
    None: _datetime_from_string,
    'sec': lambda c, s: datetime.fromtimestamp(s),
    'sec_float': lambda c, s: datetime.fromtimestamp(s),
    'msec': lambda c, s: datetime.fromtimestamp(s//1000),
    'msec_float': lambda c, s: datetime.fromtimestamp(s/1000),
    'usec': lambda c, s: datetime.fromtimestamp(s/1e6),
}


def _parse_datetime_iso_match(date_match, tz=None):
    fields = date_match.groupdict()

    year = int(fields.get('year'))
    month =  int(fields.get('month'))
    day = int(fields.get('day'))
    hour = int(fields.get('hr'))
    min = int(fields.get('min'))
    sec = int(fields.get('sec'))
    usec = fields.get("sec_frac")
    if usec is None:
        usec = 0
    else:
        # we only get the most significant 6 digits because that's what
        # datetime can handle.
        usec = int(round(float(usec) * 1e6))

    return datetime(year, month, day, hour, min, sec, usec, tz)

def datetime_from_string_iso(cls, string):
    astz = cls.Attributes.as_timezone

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
            tz_hr, tz_min = [int(match.group(x)) for x in ("tz_hr", "tz_min")]
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


def _datetime_to_string(cls, value):
    if cls.Attributes.as_timezone is not None and value.tzinfo is not None:
        value = value.astimezone(cls.Attributes.as_timezone)
    if not cls.Attributes.timezone:
        value = value.replace(tzinfo=None)

    format = cls.Attributes.format
    if format is None:
        ret_str = value.isoformat()
    else:
        ret_str = datetime.strftime(value, format)

    string_format = cls.Attributes.string_format
    if string_format is None:
        return ret_str
    else:
        return string_format % ret_str


_dt_sec = lambda cls, val: \
        int(time.mktime(val.timetuple()))
_dt_sec_float = lambda cls, val: \
        time.mktime(val.timetuple()) + (val.microsecond / 1e6)

_dt_msec = lambda cls, val: \
        int(time.mktime(val.timetuple())) * 1000 + (val.microsecond // 1000)
_dt_msec_float = lambda cls, val: \
        time.mktime(val.timetuple()) * 1000 + (val.microsecond / 1000.0)

_dt_usec = lambda cls, val: \
        int(time.mktime(val.timetuple())) * 1000000 + val.microsecond

_datetime_smap = {
    None: _datetime_to_string,

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
    data = f.read(65536)
    while len(data) > 0:
        yield data
        data = f.read(65536)

    f.close()
