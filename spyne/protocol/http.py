
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

"""The ``spyne.protocol.http`` module contains the HttpRpc protocol
implementation.
"""

import logging
logger = logging.getLogger(__name__)

import pytz
import tempfile

from Cookie import SimpleCookie

from spyne.error import ResourceNotFoundError
from spyne.model.binary import BINARY_ENCODING_URLSAFE_BASE64
from spyne.model.binary import ByteArray
from spyne.model.primitive import DateTime
from spyne.protocol.dictdoc import FlatDictDocument

try:
    from cStringIO import StringIO
except ImportError:
    try:
        from StringIO import StringIO
    except ImportError: # Python 3
        from io import StringIO


TEMPORARY_DIR = None
STREAM_READ_BLOCK_SIZE = 0x4000
SWAP_DATA_TO_FILE_THRESHOLD = 512 * 1024


def get_stream_factory(dir=None, delete=True):
    def stream_factory(total_content_length, filename, content_type,
                                                           content_length=None):
        if total_content_length >= SWAP_DATA_TO_FILE_THRESHOLD or \
                                                                delete == False:
            if delete == False:
                # You need python >= 2.6 for this.
                retval = tempfile.NamedTemporaryFile('wb+', dir=dir,
                                                                  delete=delete)
            else:
                retval = tempfile.NamedTemporaryFile('wb+', dir=dir)
        else:
            retval = StringIO()

        return retval

    return stream_factory

_weekday = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_month = ['w00t', "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
             "Oct", "Nov", "Dec"]

def to_string(prot, val, cls):
    if issubclass(cls, DateTime):
        if val.tzinfo is not None:
            val = val.astimezone(pytz.utc)
        else:
            val = val.replace(tzinfo=pytz.utc)

        return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (
                            _weekday[val.weekday()], val.day, _month[val.month],
                            val.year, val.hour, val.minute, val.second)
    elif issubclass(cls, ByteArray):
        return prot.to_string(cls, val,
                                suggested_encoding=prot.default_binary_encoding)

    else:
        return prot.to_string(cls, val)


class HttpRpc(FlatDictDocument):
    """The so-called ReST-ish HttpRpc protocol implementation. It only works
    with Http (wsgi and twisted) transports.

    :param app: An :class:'spyne.application.Application` instance.
    :param validator: Validation method to use. One of (None, 'soft')
    :param mime_type: Default mime type to set. Default is 'application/octet-stream'
    :param tmp_dir: Temporary directory to store partial file uploads. Default
        is to use the OS default.
    :param tmp_delete_on_close: The ``delete`` argument to the
        :class:`tempfile.NamedTemporaryFile`.
        See: http://docs.python.org/2/library/tempfile.html#tempfile.NamedTemporaryFile.
    :param ignore_uncap: As HttpRpc can't serialize complex models, it throws a
        server exception when the return type of the user function is Complex.
        Passing ``True`` to this argument prevents that by ignoring the return
        value.
    """

    mime_type = 'text/plain'
    default_binary_encoding = BINARY_ENCODING_URLSAFE_BASE64

    type = set(FlatDictDocument.type)
    type.add('http')

    def __init__(self, app=None, validator=None, mime_type=None,
                    tmp_dir=None, tmp_delete_on_close=True, ignore_uncap=False,
                                                            parse_cookie=False):
        FlatDictDocument.__init__(self, app, validator, mime_type,
                                                      ignore_uncap=ignore_uncap)

        self.tmp_dir = tmp_dir
        self.tmp_delete_on_close = tmp_delete_on_close
        self.parse_cookie = parse_cookie

    def get_tmp_delete_on_close(self):
        return self.__tmp_delete_on_close

    def set_tmp_delete_on_close(self, val):
        self.__tmp_delete_on_close = val
        self.stream_factory = get_stream_factory(self.tmp_dir,
                                                     self.__tmp_delete_on_close)

    tmp_delete_on_close = property(get_tmp_delete_on_close,
                                                        set_tmp_delete_on_close)

    def set_validator(self, validator):
        if validator == 'soft' or validator is self.SOFT_VALIDATION:
            self.validator = self.SOFT_VALIDATION
        elif validator is None:
            self.validator = None
        else:
            raise ValueError(validator)

    def create_in_document(self, ctx, in_string_encoding=None):
        assert ctx.transport.type.endswith('http'), \
            ("This protocol only works with an http transport, not %r, (in %r)"
                                          % (ctx.transport.type, ctx.transport))

        ctx.in_document = ctx.transport.req

    def decompose_incoming_envelope(self, ctx, message):
        assert message == FlatDictDocument.REQUEST

        ctx.transport.itself.decompose_incoming_envelope(self, ctx, message)

        if self.parse_cookie:
            cookies = ctx.in_header_doc.get('cookie', [])
            for cookie_string in cookies:
                cookie = SimpleCookie()
                cookie.load(cookie_string)
                for k,v in cookie.items():
                    l = ctx.in_header_doc.get(k, [])
                    l.append(v.coded_value)
                    ctx.in_header_doc[k] = l

        logger.debug('\theader : %r' % (ctx.in_header_doc))
        logger.debug('\tbody   : %r' % (ctx.in_body_doc))

    def deserialize(self, ctx, message):
        assert message in (self.REQUEST,)

        self.event_manager.fire_event('before_deserialize', ctx)

        if ctx.descriptor is None:
            raise ResourceNotFoundError(ctx.method_request_string)

        if ctx.descriptor.in_header is not None:
            # HttpRpc supports only one header class
            in_header_class = ctx.descriptor.in_header[0]
            ctx.in_header = self.flat_dict_to_object(ctx.in_header_doc,
                                                in_header_class, self.validator)

        if ctx.descriptor.in_message is not None:
            ctx.in_object = self.flat_dict_to_object(ctx.in_body_doc,
                                      ctx.descriptor.in_message, self.validator)

        self.event_manager.fire_event('after_deserialize', ctx)

    def serialize(self, ctx, message):
        assert message in (self.RESPONSE,)

        if ctx.out_error is None:
            result_class = ctx.descriptor.out_message
            header_class = ctx.descriptor.out_header
            if header_class is not None:
                # HttpRpc supports only one header class
                header_class = header_class[0]

            # assign raw result to its wrapper, result_message
            out_type_info = result_class.get_flat_type_info(result_class)
            if len(out_type_info) == 1:
                out_class = out_type_info.values()[0]
                if ctx.out_object is None:
                    ctx.out_document = ['']

                else:
                    try:
                        ctx.out_document = self.to_string_iterable(out_class,
                                                              ctx.out_object[0])
                    except (AttributeError, TypeError), e:
                        logger.exception(e)
                        if not self.ignore_uncap:
                            raise TypeError("HttpRpc protocol can only "
                                     "serialize primitives, not %r" % out_class)

            elif len(out_type_info) == 0:
                pass

            else:
                raise TypeError("HttpRpc protocol can only serialize simple "
                                "return types.")

            # header
            if ctx.out_header is not None:
                out_header = ctx.out_header
                if isinstance(ctx.out_header, (list, tuple)):
                    out_header = ctx.out_header[0]

                ctx.out_header_doc = self.object_to_flat_dict(header_class,
                                          out_header, subvalue_eater=to_string)

        else:
            ctx.transport.mime_type = 'text/plain'
            ctx.out_document = ctx.out_error.to_string_iterable(ctx.out_error)

        self.event_manager.fire_event('serialize', ctx)

    def create_out_string(self, ctx, out_string_encoding='utf8'):
        ctx.out_string = ctx.out_document


class HttpPattern(object):
    """Experimental. Stay away.

    :param address: Address pattern
    :param verb: HTTP Verb pattern
    :param host: HTTP "Host:" header pattern
    """

    def __init__(self, address, verb=None, host=None, endpoint=None):
        self.address = address
        self.host = host
        self.verb = verb
        self.endpoint = endpoint

    def as_werkzeug_rule(self):
        from werkzeug.routing import Rule
        from spyne.util.invregexp import invregexp

        methods = None
        if self.verb is not None:
            methods = invregexp(self.verb)

        host = self.host
        if host is None:
            host = '<__ignored>'  # this is necessary when host_matching is enabled.

        return Rule(self.address, host=host, endpoint=self.endpoint,
                                                                methods=methods)
