
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

from __future__ import print_function, unicode_literals

import logging
logger = logging.getLogger(__name__)

import re
import uuid
import errno

from os.path import isabs, join, abspath
from collections import deque
from datetime import datetime
from decimal import Decimal as D
from mmap import mmap, ACCESS_READ
from time import mktime, strftime

try:
    from lxml import etree
    from lxml import html
except ImportError:
    etree = None
    html = None

from spyne.protocol._base import ProtocolMixin
from spyne.model import ModelBase, XmlAttribute, SimpleModel, Null, \
    ByteArray, File, ComplexModelBase, AnyXml, AnyHtml, Unicode, Decimal, \
    Double, Integer, Time, DateTime, Uuid, Duration, Boolean, AnyDict, \
    AnyUri, PushBase, Date
from spyne.model.relational import FileData

from spyne.const.http import HTTP_400, HTTP_401, HTTP_404, HTTP_405, HTTP_413, \
    HTTP_500
from spyne.error import Fault, InternalError, ResourceNotFoundError, \
    RequestTooLongError, RequestNotAllowed, InvalidCredentialsError
from spyne.model.binary import binary_encoding_handlers, \
    BINARY_ENCODING_USE_DEFAULT

from spyne.util import six
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
             ignore_wrappers=False, binary_encoding=None, string_encoding=None):

        super(OutProtocolBase, self).__init__(app=app, mime_type=mime_type,
            ignore_wrappers=ignore_wrappers,
               binary_encoding=binary_encoding, string_encoding=string_encoding)

        self.ignore_uncap = ignore_uncap
        self.message = None

        if mime_type is not None:
            self.mime_type = mime_type

        self._to_bytes_handlers = cdict({
            ModelBase: self.model_base_to_bytes,
            File: self.file_to_bytes,
            Time: self.time_to_bytes,
            Uuid: self.uuid_to_bytes,
            Null: self.null_to_bytes,
            Date: self.date_to_bytes,
            Double: self.double_to_bytes,
            AnyXml: self.any_xml_to_bytes,
            Unicode: self.unicode_to_bytes,
            Boolean: self.boolean_to_bytes,
            Decimal: self.decimal_to_bytes,
            Integer: self.integer_to_bytes,
            AnyHtml: self.any_html_to_bytes,
            DateTime: self.datetime_to_bytes,
            Duration: self.duration_to_bytes,
            ByteArray: self.byte_array_to_bytes,
            XmlAttribute: self.xmlattribute_to_bytes,
            ComplexModelBase: self.complex_model_base_to_bytes,
        })

        self._to_unicode_handlers = cdict({
            ModelBase: self.model_base_to_unicode,
            File: self.file_to_unicode,
            Time: self.time_to_unicode,
            Date: self.date_to_unicode,
            Uuid: self.uuid_to_unicode,
            Null: self.null_to_unicode,
            Double: self.double_to_unicode,
            AnyXml: self.any_xml_to_unicode,
            AnyUri: self.any_uri_to_unicode,
            AnyDict: self.any_dict_to_unicode,
            AnyHtml: self.any_html_to_unicode,
            Unicode: self.unicode_to_unicode,
            Boolean: self.boolean_to_unicode,
            Decimal: self.decimal_to_unicode,
            Integer: self.integer_to_unicode,
            # FIXME: Would we need a to_unicode for localized dates?
            DateTime: self.datetime_to_unicode,
            Duration: self.duration_to_unicode,
            ByteArray: self.byte_array_to_unicode,
            XmlAttribute: self.xmlattribute_to_unicode,
            ComplexModelBase: self.complex_model_base_to_unicode,
        })

        self._to_bytes_iterable_handlers = cdict({
            File: self.file_to_bytes_iterable,
            ByteArray: self.byte_array_to_bytes_iterable,
            ModelBase: self.model_base_to_bytes_iterable,
            SimpleModel: self.simple_model_to_bytes_iterable,
            ComplexModelBase: self.complex_model_to_bytes_iterable,
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

    def to_bytes(self, cls, value, *args, **kwargs):
        if value is None:
            return None

        handler = self._to_bytes_handlers[cls]
        retval = handler(cls, value, *args, **kwargs)

        # enable this only for testing. we're not as strict for performance
        # reasons
        # assert isinstance(retval, six.binary_type), \
        #                 "AssertionError: %r %r %r handler: %r" % \
        #                       (type(retval), six.binary_type, retval, handler)
        return retval

    def to_unicode(self, cls, value, *args, **kwargs):
        if value is None:
            return None

        handler = self._to_unicode_handlers[cls]
        retval = handler(cls, value, *args, **kwargs)

        # enable this only for testing. we're not as strict for performance
        # reasons as well as not to take the joy of dealing with duck typing
        # from the user
        # assert isinstance(retval, six.text_type), \
        #                  "AssertionError: %r %r handler: %r" % \
        #                                        (type(retval), retval, handler)

        return retval

    def to_bytes_iterable(self, cls, value):
        if value is None:
            return []

        if isinstance(value, PushBase):
            return value

        handler = self._to_bytes_iterable_handlers[cls]
        return handler(cls, value)

    def null_to_bytes(self, cls, value, **_):
        return b""

    def null_to_unicode(self, cls, value, **_):
        return u""

    def any_xml_to_bytes(self, cls, value, **_):
        return etree.tostring(value)

    def any_xml_to_unicode(self, cls, value, **_):
        return etree.tostring(value, encoding='unicode')

    def any_dict_to_unicode(self, cls, value, **_):
        return repr(value)

    def any_html_to_bytes(self, cls, value, **_):
        return html.tostring(value)

    def any_html_to_unicode(self, cls, value, **_):
        return html.tostring(value, encoding='unicode')

    def uuid_to_bytes(self, cls, value, suggested_encoding=None, **_):
        ser_as = self.get_cls_attrs(cls).serialize_as
        retval = self.uuid_to_unicode(cls, value,
                                     suggested_encoding=suggested_encoding, **_)

        if ser_as in ('bytes', 'bytes_le', 'fields', 'int', six.binary_type):
            return retval

        return retval.encode('ascii')

    def uuid_to_unicode(self, cls, value, suggested_encoding=None, **_):
        attr = self.get_cls_attrs(cls)
        ser_as = attr.serialize_as
        encoding = attr.encoding

        if encoding is None:
            encoding = suggested_encoding

        retval = _uuid_serialize[ser_as](value)
        if ser_as in ('bytes', 'bytes_le'):
            retval = binary_encoding_handlers[encoding]((retval,))
        return retval

    def unicode_to_bytes(self, cls, value, **_):
        retval = value

        cls_attrs = self.get_cls_attrs(cls)

        if isinstance(value, six.text_type):
            if cls_attrs.encoding is not None:
                retval = value.encode(cls_attrs.encoding)
            elif self.default_string_encoding is not None:
                retval = value.encode(self.default_string_encoding)
            elif not six.PY2:
                logger.warning("You need to set either an encoding for %r "
                               "or a default_string_encoding for %r", cls, self)

        if cls_attrs.str_format is not None:
            return cls_attrs.str_format.format(value)
        elif cls_attrs.format is not None:
            return cls_attrs.format % retval

        return retval

    def any_uri_to_unicode(self, cls, value, **_):
        return self.unicode_to_unicode(cls, value, **_)

    def unicode_to_unicode(self, cls, value, **_):  # :)))
        cls_attrs = self.get_cls_attrs(cls)

        retval = value

        if isinstance(value, six.binary_type):
            if cls_attrs.encoding is not None:
                retval = value.decode(cls_attrs.encoding)

            if self.default_string_encoding is not None:
                retval = value.decode(self.default_string_encoding)

            elif not six.PY2:
                logger.warning("You need to set either an encoding for %r "
                               "or a default_string_encoding for %r", cls, self)

        if cls_attrs.str_format is not None:
            return cls_attrs.str_format.format(value)
        elif cls_attrs.format is not None:
            return cls_attrs.format % retval

        return retval

    def decimal_to_bytes(self, cls, value, **_):
        return self.decimal_to_unicode(cls, value, **_).encode('utf8')

    def decimal_to_unicode(self, cls, value, **_):
        D(value)  # sanity check
        cls_attrs = self.get_cls_attrs(cls)

        if cls_attrs.str_format is not None:
            return cls_attrs.str_format.format(value)
        elif cls_attrs.format is not None:
            return cls_attrs.format % value

        return str(value)

    def double_to_bytes(self, cls, value, **_):
        return self.double_to_unicode(cls, value, **_).encode('utf8')

    def double_to_unicode(self, cls, value, **_):
        float(value) # sanity check
        cls_attrs = self.get_cls_attrs(cls)

        if cls_attrs.str_format is not None:
            return cls_attrs.str_format.format(value)
        elif cls_attrs.format is not None:
            return cls_attrs.format % value

        return repr(value)

    def integer_to_bytes(self, cls, value, **_):
        return self.integer_to_unicode(cls, value, **_).encode('utf8')

    def integer_to_unicode(self, cls, value, **_):
        int(value)  # sanity check
        cls_attrs = self.get_cls_attrs(cls)

        if cls_attrs.str_format is not None:
            return cls_attrs.str_format.format(value)
        elif cls_attrs.format is not None:
            return cls_attrs.format % value

        return str(value)

    def time_to_bytes(self, cls, value, **kwargs):
        return self.time_to_unicode(cls, value, **kwargs)

    def time_to_unicode(self, cls, value, **_):
        """Returns ISO formatted times."""
        if isinstance(value, datetime):
            value = value.time()
        return value.isoformat()

    def date_to_bytes(self, cls, val, **_):
        return self.date_to_unicode(cls, val, **_).encode("utf8")

    def date_to_unicode(self, cls, val, **_):
        if isinstance(val, datetime):
            val = val.date()

        sa = self.get_cls_attrs(cls).serialize_as

        if sa is None or sa in (str, 'str'):
            return self._date_to_bytes(cls, val)

        return _datetime_smap[sa](cls, val)

    def datetime_to_bytes(self, cls, val, **_):
        retval = self.datetime_to_unicode(cls, val, **_)
        sa = self.get_cls_attrs(cls).serialize_as
        if sa is None or sa in (six.text_type, str, 'str'):
            return retval.encode('ascii')
        return retval

    def datetime_to_unicode(self, cls, val, **_):
        sa = self.get_cls_attrs(cls).serialize_as

        if sa is None or sa in (six.text_type, str, 'str'):
            return self._datetime_to_unicode(cls, val)

        return _datetime_smap[sa](cls, val)

    def duration_to_bytes(self, cls, value, **_):
        return self.duration_to_unicode(cls, value, **_).encode("utf8")

    def duration_to_unicode(self, cls, value, **_):
        if value.days < 0:
            value = -value
            negative = True
        else:
            negative = False

        tot_sec = int(value.total_seconds())
        seconds = value.seconds % 60
        minutes = value.seconds // 60
        hours = minutes // 60
        minutes %= 60
        seconds = float(seconds)
        useconds = value.microseconds

        retval = deque()
        if negative:
            retval.append("-P")
        else:
            retval.append("P")
        if value.days != 0:
            retval.append("%iD" % value.days)

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

    def boolean_to_bytes(self, cls, value, **_):
        return str(bool(value)).lower().encode('ascii')

    def boolean_to_unicode(self, cls, value, **_):
        return str(bool(value)).lower()

    def byte_array_to_bytes(self, cls, value, suggested_encoding=None, **_):
        cls_attrs = self.get_cls_attrs(cls)

        encoding = cls_attrs.encoding
        if encoding is BINARY_ENCODING_USE_DEFAULT:
            if suggested_encoding is None:
                encoding = self.binary_encoding
            else:
                encoding = suggested_encoding

        if encoding is None and isinstance(value, (list, tuple)) \
                             and len(value) == 1 and isinstance(value[0], mmap):
            return value[0]

        encoder = binary_encoding_handlers[encoding]
        logger.debug("Using binary encoder %r for encoding %r",
                                                              encoder, encoding)
        retval = encoder(value)
        if encoding is not None and isinstance(retval, six.text_type):
            retval = retval.encode('ascii')

        return retval

    def byte_array_to_unicode(self, cls, value, suggested_encoding=None, **_):
        encoding = self.get_cls_attrs(cls).encoding
        if encoding is BINARY_ENCODING_USE_DEFAULT:
            if suggested_encoding is None:
                encoding = self.binary_encoding
            else:
                encoding = suggested_encoding

        if encoding is None:
            raise ValueError("Arbitrary binary data can't be serialized to "
                                                                      "unicode")

        retval = binary_encoding_handlers[encoding](value)
        if not isinstance(retval, six.text_type):
            retval = retval.decode('ascii')

        return retval

    def byte_array_to_bytes_iterable(self, cls, value, **_):
        return value

    def file_to_bytes(self, cls, value, suggested_encoding=None):
        """
        :param cls: A :class:`spyne.model.File` subclass
        :param value: Either a sequence of byte chunks or a
            :class:`spyne.model.File.Value` instance.
        """

        encoding = self.get_cls_attrs(cls).encoding
        if encoding is BINARY_ENCODING_USE_DEFAULT:
            if suggested_encoding is None:
                encoding = self.binary_encoding
            else:
                encoding = suggested_encoding

        if isinstance(value, File.Value):
            if value.data is not None:
                return binary_encoding_handlers[encoding](value.data)

            if value.handle is not None:
                # maybe we should have used the sweeping except: here.
                if hasattr(value.handle, 'fileno'):
                    if six.PY2:
                        fileno = value.handle.fileno()
                        data = (mmap(fileno, 0, access=ACCESS_READ),)
                    else:
                        import io
                        try:
                            fileno = value.handle.fileno()
                            data = mmap(fileno, 0, access=ACCESS_READ)
                        except io.UnsupportedOperation:
                            data = (value.handle.read(),)
                else:
                    data = (value.handle.read(),)

                return binary_encoding_handlers[encoding](data)

            if value.path is not None:
                handle = open(value.path, 'rb')
                fileno = handle.fileno()
                data = mmap(fileno, 0, access=ACCESS_READ)

                return binary_encoding_handlers[encoding](data)

            assert False, "Unhandled file type"

        if isinstance(value, FileData):
            try:
                return binary_encoding_handlers[encoding](value.data)
            except Exception as e:
                logger.error("Error encoding value to binary. Error: %r, Value: %r",
                                                                           e, value)
                raise

        try:
            return binary_encoding_handlers[encoding](value)
        except Exception as e:
            logger.error("Error encoding value to binary. Error: %r, Value: %r",
                                                                       e, value)
            raise

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

        if encoding is None and cls_attrs.mode is File.TEXT:
            raise ValueError("Arbitrary binary data can't be serialized to "
                             "unicode.")

        retval = self.file_to_bytes(cls, value, suggested_encoding)
        if not isinstance(retval, six.text_type):
            retval = retval.decode('ascii')
        return retval

    def file_to_bytes_iterable(self, cls, value, **_):
        if value.data is not None:
            if isinstance(value.data, (list, tuple)) and \
                                                isinstance(value.data[0], mmap):
                return _file_to_iter(value.data[0])
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
                assert abspath(path).startswith(value.store), \
                                                 "No relative paths are allowed"
            return _file_to_iter(open(path, 'rb'))

        except IOError as e:
            if e.errno == errno.ENOENT:
                raise ResourceNotFoundError(value.path)
            else:
                raise InternalError("Error accessing requested file")

    def simple_model_to_bytes_iterable(self, cls, value, **kwargs):
        retval = self.to_bytes(cls, value, **kwargs)
        if retval is None:
            return (b'',)
        return (retval,)

    def complex_model_to_bytes_iterable(self, cls, value, **_):
        if self.ignore_uncap:
            return tuple()
        raise TypeError("This protocol can only serialize primitives.")

    def complex_model_base_to_bytes(self, cls, value, **_):
        raise TypeError("Only primitives can be serialized to string.")

    def complex_model_base_to_unicode(self, cls, value, **_):
        raise TypeError("Only primitives can be serialized to string.")

    def xmlattribute_to_bytes(self, cls, string, **kwargs):
        return self.to_bytes(cls.type, string, **kwargs)

    def xmlattribute_to_unicode(self, cls, string, **kwargs):
        return self.to_unicode(cls.type, string, **kwargs)

    def model_base_to_bytes_iterable(self, cls, value, **kwargs):
        return cls.to_bytes_iterable(value, **kwargs)

    def model_base_to_bytes(self, cls, value, **kwargs):
        return cls.to_bytes(value, **kwargs)

    def model_base_to_unicode(self, cls, value, **kwargs):
        return cls.to_unicode(value, **kwargs)

    def _datetime_to_unicode(self, cls, value, **_):
        """Returns ISO formatted datetimes."""

        cls_attrs = self.get_cls_attrs(cls)

        if cls_attrs.as_timezone is not None and value.tzinfo is not None:
            value = value.astimezone(cls_attrs.as_timezone)

        if not cls_attrs.timezone:
            value = value.replace(tzinfo=None)

        dt_format = self._get_datetime_format(cls_attrs)

        if dt_format is None:
            retval = value.isoformat()

        elif six.PY2 and isinstance(dt_format, unicode):
            retval = self.strftime(value, dt_format.encode('utf8')).decode('utf8')

        else:
            retval = self.strftime(value, dt_format)

        # FIXME: must deprecate string_format, this should have been str_format
        str_format = cls_attrs.string_format
        if str_format is None:
            str_format = cls_attrs.str_format
        if str_format is not None:
            return str_format.format(value)

        # FIXME: must deprecate interp_format, this should have been just format
        interp_format = cls_attrs.interp_format
        if interp_format is not None:
            return interp_format.format(value)

        return retval

    def _date_to_bytes(self, cls, value, **_):
        cls_attrs = self.get_cls_attrs(cls)

        date_format = cls_attrs.date_format
        if date_format is None:
            retval = value.isoformat()

        elif six.PY2 and isinstance(date_format, unicode):
            date_format = date_format.encode('utf8')
            retval = self.strftime(value, date_format).decode('utf8')

        else:
            retval = self.strftime(value, date_format)

        str_format = cls_attrs.str_format
        if str_format is not None:
            return str_format.format(value)

        format = cls_attrs.format
        if format is not None:
            return format.format(value)

        return retval

    # Format a datetime through its full proleptic Gregorian date range.
    # http://code.activestate.com/recipes/
    #                306860-proleptic-gregorian-dates-and-strftime-before-1900/
    # http://stackoverflow.com/a/32206673
    #
    # >>> strftime(datetime.date(1850, 8, 2), "%Y/%M/%d was a %A")
    # '1850/00/02 was a Friday'
    # >>>


    # remove the unsupposed "%s" command.  But don't
    # do it if there's an even number of %s before the s
    # because those are all escaped.  Can't simply
    # remove the s because the result of
    #  %sY
    # should be %Y if %s isn't supported, not the
    # 4 digit year.
    _illegal_s = re.compile(r"((^|[^%])(%%)*%s)")

    @staticmethod
    def _findall_datetime(text, substr):
         # Also finds overlaps
         sites = []
         i = 0
         while 1:
             j = text.find(substr, i)
             if j == -1:
                 break
             sites.append(j)
             i=j+1
         return sites

    # Every 28 years the calendar repeats, except through century leap
    # years where it's 6 years.  But only if you're using the Gregorian
    # calendar.  ;)

    @classmethod
    def strftime(cls, dt, fmt):
        if cls._illegal_s.search(fmt):
            raise TypeError("This strftime implementation does not handle %s")
        if dt.year > 1900:
            return dt.strftime(fmt)

        year = dt.year
        # For every non-leap year century, advance by
        # 6 years to get into the 28-year repeat cycle
        delta = 2000 - year
        off = 6*(delta // 100 + delta // 400)
        year += off

        # Move to around the year 2000
        year += ((2000 - year) // 28) * 28
        timetuple = dt.timetuple()
        s1 = strftime(fmt, (year,) + timetuple[1:])
        sites1 = cls._findall_datetime(s1, str(year))

        s2 = strftime(fmt, (year+28,) + timetuple[1:])
        sites2 = cls._findall_datetime(s2, str(year+28))

        sites = []
        for site in sites1:
            if site in sites2:
                sites.append(site)

        s = s1
        syear = "%4d" % (dt.year,)
        for site in sites:
            s = s[:site] + syear + s[site+4:]
        return s


_uuid_serialize = {
    None: str,
    str: str,
    'str': str,

    'hex': lambda u: u.hex,
    'urn': lambda u: u.urn,
    'bytes': lambda u: u.bytes,
    'bytes_le': lambda u: u.bytes_le,
    'fields': lambda u: u.fields,

    int: lambda u: u.int,
    'int': lambda u: u.int,
}

_uuid_deserialize = {
    None: uuid.UUID,
    str: uuid.UUID,
    'str': uuid.UUID,

    'hex': lambda s: uuid.UUID(hex=s),
    'urn': lambda s: uuid.UUID(hex=s),
    'bytes': lambda s: uuid.UUID(bytes=s),
    'bytes_le': lambda s: uuid.UUID(bytes_le=s),
    'fields': lambda s: uuid.UUID(fields=s),

    int: lambda s: uuid.UUID(int=s),
    'int': lambda s: uuid.UUID(int=s),

    (int, int): lambda s: uuid.UUID(int=s),
    ('int', int): lambda s: uuid.UUID(int=s),

    (int, str): lambda s: uuid.UUID(int=int(s)),
    ('int', str): lambda s: uuid.UUID(int=int(s)),
}

if six.PY2:
    _uuid_deserialize[('int', long)] = _uuid_deserialize[('int', int)]
    _uuid_deserialize[(int, long)] = _uuid_deserialize[('int', int)]


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
        data = f.read(8192)
        while len(data) > 0:
            yield data
            data = f.read(8192)

    finally:
        f.close()


META_ATTR = ['nullable', 'default_factory']
