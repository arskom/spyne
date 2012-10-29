
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

import tempfile

TEMPORARY_DIR = None
STREAM_READ_BLOCK_SIZE = 0x4000
SWAP_DATA_TO_FILE_THRESHOLD = 512 * 1024

try:
    from cStringIO import StringIO
except ImportError:
    try:
        from StringIO import StringIO
    except ImportError: # Python 3
        from io import StringIO

from spyne.protocol.dictobj import DictDocument

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


class HttpRpc(DictDocument):
    """The so-called ReST-ish HttpRpc protocol implementation. It only works
    with Http (wsgi and twisted) transports.
    """

    mime_type = 'text/plain'
    allowed_http_verbs = None

    def __init__(self, app=None, validator=None, mime_type=None, tmp_dir=None,
                                                      tmp_delete_on_close=True):
        DictDocument.__init__(self, app, validator, mime_type)

        self.tmp_dir = tmp_dir
        self.tmp_delete_on_close = tmp_delete_on_close

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
            ("This protocol only works with an http transport, not: %s, (in %r)"
                                          % (ctx.transport.type, ctx.transport))

        ctx.in_document = ctx.transport.req

    def decompose_incoming_envelope(self, ctx, message):
        assert message == DictDocument.REQUEST

        ctx.transport.itself.decompose_incoming_envelope(self, ctx, message)

        logger.debug('\theader : %r' % (ctx.in_header_doc))
        logger.debug('\tbody   : %r' % (ctx.in_body_doc))

    def deserialize(self, ctx, message):
        assert message in (self.REQUEST,)

        self.event_manager.fire_event('before_deserialize', ctx)

        if ctx.descriptor.in_header:
            ctx.in_header = self.flat_dict_to_object(ctx.in_header_doc,
                                      ctx.descriptor.in_header, self.validator)
        if ctx.descriptor.in_message:
            ctx.in_object = self.flat_dict_to_object(ctx.in_body_doc,
                                      ctx.descriptor.in_message, self.validator)

        self.event_manager.fire_event('after_deserialize', ctx)

    def serialize(self, ctx, message):
        assert message in (self.RESPONSE,)

        if ctx.out_error is None:
            result_message_class = ctx.descriptor.out_message

            # assign raw result to its wrapper, result_message
            out_type_info = result_message_class.get_flat_type_info(
                                                           result_message_class)
            if len(out_type_info) == 1:
                out_class = out_type_info.values()[0]
                if ctx.out_object is None:
                    ctx.out_document = ['']
                else:
                    try:
                        ctx.out_document = out_class.to_string_iterable(
                                                              ctx.out_object[0])
                    except AttributeError:
                        raise ValueError("HttpRpc protocol can only serialize "
                                         "primitives, not %r" % out_class)
            elif len(out_type_info) == 0:
                pass

            else:
                raise ValueError("HttpRpc protocol can only serialize simple "
                                 "return values.")
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

        return Rule(self.address, host=self.host, endpoint=self.endpoint,
                                                                methods=methods)
