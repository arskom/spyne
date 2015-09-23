
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

import uuid
import errno

from os.path import isabs, join
from collections import deque
from datetime import timedelta, datetime
from decimal import Decimal as D
from mmap import mmap, ACCESS_READ
from time import mktime

try:
    from lxml import etree
    from lxml import html
except ImportError:
    etree = None
    html = None

from spyne.protocol._base import ProtocolMixin

from spyne.model import ModelBase, XmlAttribute, SimpleModel, Null, \
    ByteArray, File, ComplexModelBase, AnyXml, AnyHtml, Unicode, Decimal, \
    Double, Integer, Time, DateTime, Uuid, Duration, Boolean

from spyne.const.http import HTTP_400, HTTP_401, HTTP_404, HTTP_405, HTTP_413, \
    HTTP_500

from spyne.error import Fault, InternalError, ResourceNotFoundError, \
    RequestTooLongError, RequestNotAllowed, InvalidCredentialsError

from spyne.model.binary import binary_encoding_handlers, \
    BINARY_ENCODING_USE_DEFAULT

from spyne.util import six
from spyne.model.binary import Attachment  # DEPRECATED

from spyne.util.cdict import cdict


class OutProtocolBase(ProtocolMixin):
    """This is the abstract base class for all out protocol implementations.
    Child classes can implement only the required subset of the public methods.

    An output protocol must implement :func:`serialize` and
    :func:`create_out_string`.

    The OutProtocolBase class supports the following events:

    * ``before_serialize``:
      Called before after the serialization operation is attempted.

    * ``after_serialize``:
      Called after the serialization operation is finished.

    The arguments the constructor takes are as follows:

    :param app: The application this protocol belongs to.
    :param mime_type: The mime_type this protocol should set for transports
        that support this. This is a quick way to override the mime_type by
        default instead of subclassing the releavant protocol implementation.
    :param ignore_uncap: Silently ignore cases when the protocol is not capable
        of serializing return values instead of raising a TypeError.
    """

    def __init__(self, app=None, mime_type=None, ignore_uncap=False,
                                   ignore_wrappers=False, binary_encoding=None):

        super(OutProtocolBase, self).__init__(app=app, mime_type=mime_type,
                                                ignore_wrappers=ignore_wrappers)

        self.ignore_uncap = ignore_uncap
        self.message = None
        self.binary_encoding = binary_encoding

        if self.binary_encoding is None:
            self.binary_encoding = self.default_binary_encoding

        if mime_type is not None:
            self.mime_type = mime_type

        self._to_string_handlers = cdict({
            ModelBase: self.model_base_to_string,
            File: self.file_to_string,
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

        self._to_unicode_handlers = cdict({
            ModelBase: self.model_base_to_unicode,
            File: self.file_to_unicode,
            Time: self.time_to_string,
            Uuid: self.uuid_to_string,
            Null: self.null_to_string,
            Double: self.double_to_string,
            AnyXml: self.any_xml_to_unicode,
            Unicode: self.unicode_to_unicode,
            Boolean: self.boolean_to_string,
            Decimal: self.decimal_to_string,
            Integer: self.integer_to_string,
            AnyHtml: self.any_html_to_unicode,
            # FIXME: Would we need a to_unicode for localized dates?
            DateTime: self.datetime_to_string,
            Duration: self.duration_to_string,
            ByteArray: self.byte_array_to_unicode,
            XmlAttribute: self.xmlattribute_to_unicode,
            ComplexModelBase: self.complex_model_base_to_string,
        })

        self._to_string_iterable_handlers = cdict({
            File: self.file_to_string_iterable,
            ByteArray: self.byte_array_to_string_iterable,
            ModelBase: self.model_base_to_string_iterable,
            SimpleModel: self.simple_model_to_string_iterable,
            ComplexModelBase: self.complex_model_to_string_iterable,
        })


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

    def to_string(self, class_, value, *args, **kwargs):
        if value is None:
            return None

        handler = self._to_string_handlers[class_]
        retval = handler(class_, value, *args, **kwargs)
        if six.PY3 and isinstance(retval, six.text_type):
            retval = retval.encode('ascii')
        return retval

    def to_unicode(self, class_, value, *args, **kwargs):
        if value is None:
            return None

        handler = self._to_unicode_handlers[class_]
        return handler(class_, value, *args, **kwargs)

    def to_string_iterable(self, class_, value):
        if value is None:
            return []

        handler = self._to_string_iterable_handlers[class_]
        return handler(class_, value)

    def null_to_string(self, cls, value, **_):
        return ""

    def any_xml_to_string(self, cls, value, **_):
        return etree.tostring(value)

    def any_xml_to_unicode(self, cls, value, **_):
        return etree.tostring(value, encoding='unicode')

    def any_html_to_string(self, cls, value, **_):
        return html.tostring(value)

    def any_html_to_unicode(self, cls, value, **_):
        return html.tostring(value, encoding='unicode')

    def uuid_to_string(self, cls, value, suggested_encoding=None, **_):
        attr = self.get_cls_attrs(cls)
        ser_as = attr.serialize_as
        encoding = attr.encoding

        if encoding is None:
            encoding = suggested_encoding

        retval = _uuid_serialize[ser_as](value)
        if ser_as in ('bytes', 'bytes_le'):
            retval = binary_encoding_handlers[encoding]((retval,))
        return retval

    def unicode_to_string(self, cls, value, **_):
        retval = value

        cls_attrs = self.get_cls_attrs(cls)

        if cls_attrs.encoding is not None and isinstance(value, six.text_type):
            retval = value.encode(cls_attrs.encoding)

        if cls_attrs.str_format is not None:
            return cls_attrs.str_format.format(value)
        elif cls_attrs.format is not None:
            return cls_attrs.format % retval

        return retval

    def unicode_to_unicode(self, cls, value, **_):  # :)))
        # value can be many things, but definetly not an int
        if isinstance(value, six.integer_types):
            logger.warning("Returning an int where a str is expected! "
                                                       "Silenty fixing this...")
            value = str(value)

        retval = value

        cls_attrs = self.get_cls_attrs(cls)

        if cls_attrs.encoding is not None and \
                                             isinstance(value, six.binary_type):
            retval = value.decode(cls_attrs.encoding)

        if cls_attrs.str_format is not None:
            return cls_attrs.str_format.format(value)
        elif cls_attrs.format is not None:
            return cls_attrs.format % retval

        return retval

    def decimal_to_string(self, cls, value, **_):
        D(value)  # sanity check
        cls_attrs = self.get_cls_attrs(cls)

        if cls_attrs.str_format is not None:
            return cls_attrs.str_format.format(value)
        elif cls_attrs.format is not None:
            return cls_attrs.format % value

        return str(value)

    def double_to_string(self, cls, value, **_):
        float(value) # sanity check
        cls_attrs = self.get_cls_attrs(cls)

        if cls_attrs.str_format is not None:
            return cls_attrs.str_format.format(value)
        elif cls_attrs.format is not None:
            return cls_attrs.format % value

        return repr(value)

    def integer_to_string(self, cls, value, **_):
        int(value)  # sanity check
        cls_attrs = self.get_cls_attrs(cls)

        if cls_attrs.str_format is not None:
            return cls_attrs.str_format.format(value)
        elif cls_attrs.format is not None:
            return cls_attrs.format % value

        return str(value)

    def time_to_string(self, cls, value, **_):
        """Returns ISO formatted dates."""
        return value.isoformat()

    def datetime_to_string(self, cls, val):
        sa = self.get_cls_attrs(cls).serialize_as

        if sa is None:
            return self._datetime_to_string(cls, val)

        return _datetime_smap[sa](cls, val)

    def duration_to_string(self, cls, value, **_):
        if value.days < 0:
            value = -value
            negative = True
        else:
            negative = False

        tot_sec = _total_seconds(value)
        seconds = value.seconds % 60
        minutes = value.seconds / 60
        hours = minutes / 60
        minutes %= 60
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

    def boolean_to_string(self, cls, value, **_):
        return str(bool(value)).lower()

    def byte_array_to_string(self, cls, value, suggested_encoding=None, **_):
        encoding = self.get_cls_attrs(cls).encoding
        if encoding is BINARY_ENCODING_USE_DEFAULT:
            encoding = suggested_encoding
        return binary_encoding_handlers[encoding](value)

    def byte_array_to_unicode(self, cls, value, suggested_encoding=None, **_):
        encoding = self.get_cls_attrs(cls).encoding
        if encoding is BINARY_ENCODING_USE_DEFAULT:
            encoding = suggested_encoding
        if encoding is None:
            raise ValueError("Arbitrary binary data can't be serialized to "
                             "unicode")
        return binary_encoding_handlers[encoding](value)

    def byte_array_to_string_iterable(self, cls, value, **_):
        return value

    def file_to_string(self, cls, value, suggested_encoding=None):
        """
        :param cls: A :class:`spyne.model.File` subclass
        :param value: Either a sequence of byte chunks or a
            :class:`spyne.model.File.Value` instance.
        """

        encoding = self.get_cls_attrs(cls).encoding
        if encoding is BINARY_ENCODING_USE_DEFAULT:
            encoding = suggested_encoding

        if isinstance(value, File.Value):
            if value.data is not None:
                return binary_encoding_handlers[encoding](value.data)

            if value.handle is not None:
                assert isinstance(value.handle, file)

                fileno = value.handle.fileno()
                data = mmap(fileno, 0, access=ACCESS_READ)

                return binary_encoding_handlers[encoding](data)

            assert False

        return binary_encoding_handlers[encoding](value)

    def file_to_unicode(self, cls, value, suggested_encoding=None):
        """
        :param cls: A :class:`spyne.model.File` subclass
        :param value: Either a sequence of byte chunks or a
            :class:`spyne.model.File.Value` instance.
        """

        cls_attrs = self.get_cls_attrs(cls)
        encoding = cls_attrs.encoding
        if encoding is BINARY_ENCODING_USE_DEFAULT:
            encoding = suggested_encoding

        if encoding is None and cls_attrs.type is File.BINARY:
            raise ValueError("Arbitrary binary data can't be serialized to "
                             "unicode.")

        return self.file_to_string(cls, value, suggested_encoding)

    def file_to_string_iterable(self, cls, value, **_):
        if value.data is not None:
            if isinstance(value.data, (list, tuple)) and \
                    isinstance(value.data[0], mmap):
                return _file_to_iter(value.data[0])
            else:
                return iter(value.data)

        if value.handle is not None:
            f = value.handle
            f.seek(0)
            return _file_to_iter(f)

        assert value.path is not None, "You need to write data to " \
                 "persistent storage first if you want to read it back."

        try:
            path = value.path
            if not isabs(value.path):
                path = join(value.store, value.path)
            return _file_to_iter(open(path, 'rb'))

        except IOError as e:
            if e.errno == errno.ENOENT:
                raise ResourceNotFoundError(value.path)
            else:
                raise InternalError("Error accessing requested file")

    def simple_model_to_string_iterable(self, cls, value, **kwargs):
        retval = self.to_string(cls, value, **kwargs)
        if retval is None:
            return ('',)
        return (retval,)

    def complex_model_to_string_iterable(self, cls, value, **_):
        if self.ignore_uncap:
            return tuple()
        raise TypeError("This protocol can only serialize primitives.")

    def attachment_to_string(self, cls, value, **_):
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

    def complex_model_base_to_string(self, cls, value, **_):
        raise TypeError("Only primitives can be serialized to string.")

    def xmlattribute_to_string(self, cls, string, **kwargs):
        return self.to_string(cls.type, string, **kwargs)

    def xmlattribute_to_unicode(self, cls, string, **kwargs):
        return self.to_unicode(cls.type, string, **kwargs)

    def model_base_to_string_iterable(self, cls, value, **kwargs):
        return cls.to_string_iterable(value, **kwargs)

    def model_base_to_string(self, cls, value, **kwargs):
        return cls.to_string(value, **kwargs)

    def model_base_to_unicode(self, cls, value, **kwargs):
        return cls.to_unicode(value, **kwargs)

    def _datetime_to_string(self, cls, value, **_):
        cls_attrs = self.get_cls_attrs(cls)
        if cls_attrs.as_timezone is not None and value.tzinfo is not None:
            value = value.astimezone(cls_attrs.as_timezone)
        if not cls_attrs.timezone:
            value = value.replace(tzinfo=None)

        # FIXME: this should be date_format, all other aliases are to be
        # deprecated
        date_format = cls_attrs.date_format
        if date_format is None:
            date_format = cls_attrs.out_format
        if date_format is None:
            date_format = cls_attrs.format

        if date_format is None:
            retval = value.isoformat()
        elif six.PY2 and isinstance(date_format, unicode):
            retval = value.strftime(date_format.encode('utf8')).decode('utf8')
        else:
            retval = value.strftime(date_format)

        # FIXME: must deprecate string_format, this should have been str_format
        string_format = cls_attrs.string_format
        if string_format is None:
            string_format = cls_attrs.str_format
        if string_format is not None:
            return string_format.format(value)

        # FIXME: must deprecate interp_format, this should have been just format
        format = cls_attrs.interp_format
        if format is not None:
            return format.format(value)

        return retval


_uuid_serialize = {
    None: str,
    'hex': lambda u: u.hex,
    'urn': lambda u: u.urn,
    'bytes': lambda u: u.bytes,
    'bytes_le': lambda u: u.bytes_le,
    'fields': lambda u: u.fields,
    'int': lambda u: u.int,
}

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



if hasattr(timedelta, 'total_seconds'):
    def _total_seconds(td):
        return td.total_seconds()

else:
    def _total_seconds(td):
        return (td.microseconds + (td.seconds + td.days * 24 * 3600) *1e6) / 1e6


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
        usecond = int(round(float(usecond) * 1e6))

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


META_ATTR = ['nullable', 'default_factory']
