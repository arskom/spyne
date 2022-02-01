
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

This module is EXPERIMENTAL. You may not recognize the code here next time you
look at it.
"""

from __future__ import print_function

import logging
logger = logging.getLogger(__name__)

import re
import pytz
import tempfile

from spyne import BODY_STYLE_WRAPPED, MethodDescriptor, PushBase
from spyne.util import six, coroutine, Break
from spyne.util.six import string_types, BytesIO
from spyne.error import ResourceNotFoundError
from spyne.model.binary import BINARY_ENCODING_URLSAFE_BASE64, File
from spyne.model.primitive import DateTime
from spyne.protocol.dictdoc import SimpleDictDocument


TEMPORARY_DIR = None
STREAM_READ_BLOCK_SIZE = 0x4000
SWAP_DATA_TO_FILE_THRESHOLD = 512 * 1024


_OctalPatt = re.compile(r"\\[0-3][0-7][0-7]")
_QuotePatt = re.compile(r"[\\].")
_nulljoin = ''.join


# this is twisted's _idnaBytes. it's not possible to import twisted at this
# stage so here we are
def _host_to_bytes(text):
    try:
        import idna
    except ImportError:
        return text.encode("idna")
    else:
        return idna.encode(text)


def _unquote_cookie(str):
    """Handle double quotes and escaping in cookie values.
    This method is copied verbatim from the Python 3.5 standard
    library (http.cookies._unquote) so we don't have to depend on
    non-public interfaces.
    """
    # If there aren't any doublequotes,
    # then there can't be any special characters.  See RFC 2109.
    if str is None or len(str) < 2:
        return str
    if str[0] != '"' or str[-1] != '"':
        return str

    # We have to assume that we must decode this string.
    # Down to work.

    # Remove the "s
    str = str[1:-1]

    # Check for special sequences.  Examples:
    #    \012 --> \n
    #    \"   --> "
    #
    i = 0
    n = len(str)
    res = []
    while 0 <= i < n:
        o_match = _OctalPatt.search(str, i)
        q_match = _QuotePatt.search(str, i)
        if not o_match and not q_match:              # Neither matched
            res.append(str[i:])
            break
        # else:
        j = k = -1
        if o_match:
            j = o_match.start(0)
        if q_match:
            k = q_match.start(0)
        if q_match and (not o_match or k < j):     # QuotePatt matched
            res.append(str[i:k])
            res.append(str[k+1])
            i = k + 2
        else:                                      # OctalPatt matched
            res.append(str[i:j])
            res.append(chr(int(str[j+1:j+4], 8)))
            i = j + 4
    return _nulljoin(res)


def _parse_cookie(cookie):
    """Parse a ``Cookie`` HTTP header into a dict of name/value pairs.
    This function attempts to mimic browser cookie parsing behavior;
    it specifically does not follow any of the cookie-related RFCs
    (because browsers don't either).
    The algorithm used is identical to that used by Django version 1.9.10.
    """

    retval = {}

    for chunk in cookie.split(';'):
        if '=' in chunk:
            key, val = chunk.split('=', 1)
        else:
            # Assume an empty name per
            # https://bugzilla.mozilla.org/show_bug.cgi?id=169091
            key, val = '', chunk

        key, val = key.strip(), val.strip()
        if key or val:
            # unquote using Python's algorithm.
            retval[key] = _unquote_cookie(val)

    return retval


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
            retval = BytesIO()

        return retval

    return stream_factory

_weekday = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_month = ['w00t', "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
             "Oct", "Nov", "Dec"]

def _header_to_bytes(prot, val, cls):
    if issubclass(cls, DateTime):
        if val.tzinfo is not None:
            val = val.astimezone(pytz.utc)
        else:
            val = val.replace(tzinfo=pytz.utc)

        return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (
                            _weekday[val.weekday()], val.day, _month[val.month],
                            val.year, val.hour, val.minute, val.second)
    else:
        # because wsgi_ref wants header values in unicode.
        return prot.to_unicode(cls, val)


class HttpRpc(SimpleDictDocument):
    """The so-called HttpRpc protocol implementation. It only works with Http
    (wsgi and twisted) transports.

    :param app: An :class:'spyne.application.Application` instance.
    :param validator: Validation method to use. One of (None, 'soft')
    :param mime_type: Default mime type to set. Default is
        'application/octet-stream'
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
    default_string_encoding = 'UTF-8'

    type = set(SimpleDictDocument.type)
    type.add('http')

    def __init__(self, app=None, validator=None, mime_type=None,
                    tmp_dir=None, tmp_delete_on_close=True, ignore_uncap=False,
                        parse_cookie=True, hier_delim=".", strict_arrays=False):
        super(HttpRpc, self).__init__(app, validator, mime_type,
                               ignore_uncap=ignore_uncap, hier_delim=hier_delim,
                                                    strict_arrays=strict_arrays)

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
        ctx.transport.request_encoding = in_string_encoding

    def decompose_incoming_envelope(self, ctx, message_type):
        assert message_type == SimpleDictDocument.REQUEST

        ctx.transport.itself.decompose_incoming_envelope(
                                                        self, ctx, message_type)

        if self.parse_cookie:
            cookies = ctx.in_header_doc.get('cookie', None)
            if cookies is None:
                cookies = ctx.in_header_doc.get('Cookie', None)

            if cookies is not None:
                for cookie_string in cookies:
                    logger.debug("Loading cookie string %r", cookie_string)
                    cookie = _parse_cookie(cookie_string)
                    for k, v in cookie.items():
                        l = ctx.in_header_doc.get(k, [])
                        l.append(v)
                        ctx.in_header_doc[k] = l

        logger.debug('\theader : %r' % (ctx.in_header_doc))
        logger.debug('\tbody   : %r' % (ctx.in_body_doc))

    def deserialize(self, ctx, message):
        assert message in (self.REQUEST,)

        self.event_manager.fire_event('before_deserialize', ctx)

        if ctx.descriptor is None:
            raise ResourceNotFoundError(ctx.method_request_string)

        req_enc = getattr(ctx.transport, 'request_encoding', None)
        if req_enc is None:
            req_enc = ctx.in_protocol.default_string_encoding

        if ctx.descriptor.in_header is not None:
            # HttpRpc supports only one header class
            in_header_class = ctx.descriptor.in_header[0]
            ctx.in_header = self.simple_dict_to_object(ctx, ctx.in_header_doc,
                            in_header_class, self.validator, req_enc=req_enc)

        if ctx.descriptor.in_message is not None:
            ctx.in_object = self.simple_dict_to_object(ctx, ctx.in_body_doc,
                    ctx.descriptor.in_message, self.validator, req_enc=req_enc)

        self.event_manager.fire_event('after_deserialize', ctx)

    def serialize(self, ctx, message):
        retval = None

        assert message in (self.RESPONSE,)

        if ctx.out_document is not None:
            return

        if ctx.out_error is not None:
            ctx.transport.mime_type = 'text/plain'
            ctx.out_document = ctx.out_error.to_bytes_iterable(ctx.out_error)

        else:
            retval = self._handle_rpc(ctx)

        self.event_manager.fire_event('serialize', ctx)

        return retval

    @coroutine
    def _handle_rpc_nonempty(self, ctx):
        result_class = ctx.descriptor.out_message

        out_class = None
        out_object = None

        if ctx.descriptor.body_style is BODY_STYLE_WRAPPED:
            fti = result_class.get_flat_type_info(result_class)

            if len(fti) > 1 and not self.ignore_uncap:
                raise TypeError("HttpRpc protocol can only serialize "
                                "functions with a single return type.")

            if len(fti) == 1:
                out_class, = fti.values()
                out_object, = ctx.out_object

        else:
            out_class = result_class
            out_object, = ctx.out_object

        if out_class is not None:
            if issubclass(out_class, File) and not \
                        isinstance(out_object, (list, tuple, string_types)) \
                        and out_object.type is not None:
                ctx.transport.set_mime_type(str(out_object.type))

            ret = self.to_bytes_iterable(out_class, out_object)

            if not isinstance(ret, PushBase):
                ctx.out_document = ret

            else:
                ctx.transport.itself.set_out_document_push(ctx)
                while True:
                    sv = yield
                    ctx.out_document.send(sv)

    def _handle_rpc(self, ctx):
        retval = None

        # assign raw result to its wrapper, result_message
        if ctx.out_object is None or len(ctx.out_object) < 1:
            ctx.out_document = ['']

        else:
            retval = self._handle_rpc_nonempty(ctx)

        header_class = ctx.descriptor.out_header
        if header_class is not None:
            # HttpRpc supports only one header class
            header_class = header_class[0]

        # header
        if ctx.out_header is not None:
            out_header = ctx.out_header
            if isinstance(ctx.out_header, (list, tuple)):
                out_header = ctx.out_header[0]

            ctx.out_header_doc = self.object_to_simple_dict(header_class,
                out_header, subinst_eater=_header_to_bytes)

        return retval

    def create_out_string(self, ctx, out_string_encoding='utf8'):
        if ctx.out_string is not None:
            return

        ctx.out_string = ctx.out_document

    def boolean_from_bytes(self, cls, string):
        return string.lower() in ('true', '1', 'checked', 'on')

    def integer_from_bytes(self, cls, string):
        if string == '':
            return None

        return super(HttpRpc, self).integer_from_bytes(cls, string)


_fragment_pattern_re = re.compile('<([A-Za-z0-9_]+)>')
_full_pattern_re = re.compile('{([A-Za-z0-9_]+)}')


_fragment_pattern_b_re = re.compile(b'<([A-Za-z0-9_]+)>')
_full_pattern_b_re = re.compile(b'{([A-Za-z0-9_]+)}')


class HttpPattern(object):
    """Experimental. Stay away.

    :param address: Address pattern
    :param verb: HTTP Verb pattern
    :param host: HTTP "Host:" header pattern
    """

    URL_ENCODING = 'utf8'
    HOST_ENCODING = 'idna'
    VERB_ENCODING = 'latin1'  # actually ascii but latin1 is what pep 333 needs

    @classmethod
    def _compile_url_pattern(cls, pattern_s):
        """where <> placeholders don't contain slashes."""

        if pattern_s is None:
            return None, None

        if not six.PY2:
            assert isinstance(pattern_s, six.text_type)
        pattern = _fragment_pattern_re.sub(r'(?P<\1>[^/]*)', pattern_s)
        pattern = _full_pattern_re.sub(r'(?P<\1>[^/]*)', pattern)

        pattern_b = pattern_s.encode(cls.URL_ENCODING)
        pattern_b = _fragment_pattern_b_re.sub(b'(?P<\\1>[^/]*)', pattern_b)
        pattern_b = _full_pattern_b_re.sub(b'(?P<\\1>[^/]*)', pattern_b)

        return re.compile(pattern), re.compile(pattern_b)

    @classmethod
    def _compile_host_pattern(cls, pattern):
        """where <> placeholders don't contain dots."""

        if pattern is None:
            return None, None

        pattern = _fragment_pattern_re.sub(r'(?P<\1>[^\.]*)', pattern)
        pattern = _full_pattern_re.sub(r'(?P<\1>.*)', pattern)

        pattern_b = pattern.encode(cls.HOST_ENCODING)
        pattern_b = _fragment_pattern_b_re.sub(b'(?P<\\1>[^\.]*)', pattern_b)
        pattern_b = _full_pattern_b_re.sub(b'(?P<\\1>.*)', pattern_b)

        return re.compile(pattern), re.compile(pattern_b)

    @classmethod
    def _compile_verb_pattern(cls, pattern):
        """where <> placeholders are same as {} ones."""

        if pattern is None:
            return None, None

        pattern = _fragment_pattern_re.sub(r'(?P<\1>.*)', pattern)
        pattern = _full_pattern_re.sub(r'(?P<\1>.*)', pattern)

        pattern_b = pattern.encode(cls.VERB_ENCODING)
        pattern_b = _fragment_pattern_b_re.sub(b'(?P<\\1>.*)', pattern_b)
        pattern_b = _full_pattern_b_re.sub(b'(?P<\\1>.*)', pattern_b)

        return re.compile(pattern), re.compile(pattern_b)

    def __init__(self, address=None, verb=None, host=None, endpoint=None):
        host = _host_to_bytes(host) if isinstance(host, str) else host

        self.address = address
        self.host = host
        self.verb = verb

        self.endpoint = endpoint
        if self.endpoint is not None:
            assert isinstance(self.endpoint, MethodDescriptor)

    def hello(self, descriptor):
        if self.address is None:
            self.address = descriptor.name

    @property
    def address(self):
        return self.__address

    @address.setter
    def address(self, what):
        if what is not None and not what.startswith('/'):
            what = '/{}'.format(what)

        self.__address = what
        self.address_re, self.address_b_re = self._compile_url_pattern(what)

    @property
    def host(self):
        return self.__host

    @host.setter
    def host(self, what):
        self.__host = what
        self.host_re, self.host_b_re = self._compile_host_pattern(what)

    @property
    def verb(self):
        return self.__verb

    @verb.setter
    def verb(self, what):
        self.__verb = what
        self.verb_re, self.verb_b_re = self._compile_verb_pattern(what)

    def as_werkzeug_rule(self):
        from werkzeug.routing import Rule
        from spyne.util.invregexp import invregexp

        methods = None
        if self.verb is not None:
            methods = invregexp(self.verb)

        host = self.host
        if host is None:
            host = '<__ignored>'  # for some reason, this is necessary when
                                  # host_matching is enabled.

        return Rule(self.address, host=host, endpoint=self.endpoint.name,
                                                                methods=methods)

    def __repr__(self):
        return "HttpPattern(address=%r, host=%r, verb=%r, endpoint=%r)" % (
                    self.address, self.host, self.verb,
                    None if self.endpoint is None else self.endpoint.name)
