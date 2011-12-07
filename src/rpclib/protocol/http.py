
#
# rpclib - Copyright (C) Rpclib contributors.
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

"""This module contains the HttpRpc protocol implementation."""

from rpclib.error import Fault
from rpclib.error import ValidationError
import logging
logger = logging.getLogger(__name__)

try:
    from urlparse import parse_qs
except ImportError: # Python 3
    from urllib.parse import parse_qs

from rpclib.protocol import ProtocolBase

# this is not exactly ReST, because it ignores http verbs.

def _get_http_headers(req_env):
    retval = {}

    for k,v in req_env.iteritems():
        if k.startswith("HTTP_"):
            retval[k[5:].lower()]= v

    return retval

class HttpRpc(ProtocolBase):
    """The so-called ReST-minus-the-verbs HttpRpc protocol implementation.
    It only works with the http server (wsgi) transport.

    It only parses GET requests where the whole data is in the 'QUERY_STRING'.
    """

    def check_validator(self):
        assert self.validator in ('soft', None)

    def create_in_document(self, ctx, in_string_encoding=None):
        assert ctx.transport.type == 'wsgi', ("This protocol only works with "
                                              "the wsgi api.")

        ctx.in_document = ctx.transport.req_env

    def decompose_incoming_envelope(self, ctx):
        ctx.method_request_string = '{%s}%s' % (self.app.interface.get_tns(),
                              ctx.in_document['PATH_INFO'].split('/')[-1])

        logger.debug("\033[92mMethod name: %r\033[0m" % ctx.method_request_string)

        self.app.in_protocol.set_method_descriptor(ctx)
        ctx.in_header_doc = _get_http_headers(ctx.in_document)
        ctx.in_body_doc = parse_qs(ctx.in_document['QUERY_STRING'])

        logger.debug(repr(ctx.in_body_doc))

    def deserialize(self, ctx, message):
        assert message in ('request',)

        self.event_manager.fire_event('before_deserialize', ctx)

        body_class = ctx.descriptor.in_message
        flat_type_info = body_class.get_flat_type_info(body_class)

        if ctx.in_body_doc is not None and len(ctx.in_body_doc) > 0:
            inst = body_class.get_deserialization_instance()

            # this is for validating cls.Attributes.{min,max}_occurs
            frequencies = {}

            for k, v in ctx.in_body_doc.items():
                member = flat_type_info.get(k, None)
                if member is None:
                    continue

                mo = member.Attributes.max_occurs
                if mo == 'unbounded' or mo > 1:
                    value = getattr(inst, k, None)
                    if value is None:
                        value = []

                    for v2 in v:
                        if self.validator == 'soft' and not member.validate_string(member, v2):
                            raise ValidationError(v2)
                        native_v2 = member.from_string(v2)
                        if self.validator == 'soft' and not member.validate_native(member, native_v2):
                            raise ValidationError(v2)

                        value.append(native_v2)
                        freq = frequencies.get(k,0)
                        freq+=1
                        frequencies[k] = freq

                    setattr(inst, k, value)

                else:
                    v,  = v
                    if self.validator == 'soft' and not member.validate_string(member, v):
                        raise ValidationError(v)
                    native_v = member.from_string(v)
                    if self.validator == 'soft' and not member.validate_native(member, native_v):
                        raise ValidationError(native_v)

                    if native_v is None:
                        setattr(inst, k, member.Attributes.default)
                    else:
                        setattr(inst, k, native_v)

                    freq = frequencies.get(k, 0)
                    freq += 1
                    frequencies[k] = freq

            if self.validator == 'soft':
                for k,c in flat_type_info.items():
                    val = frequencies.get(k, 0)
                    if val < c.Attributes.min_occurs \
                            or  (c.Attributes.max_occurs != 'unbounded'
                                            and val > c.Attributes.max_occurs ):
                        raise Fault('Client.ValidationError',
                            '%r member does not respect frequency constraints' % k)

            ctx.in_object = inst
        else:
            ctx.in_object = [None] * len(flat_type_info)

        self.event_manager.fire_event('after_deserialize', ctx)

    def serialize(self, ctx, message):
        assert message in ('response',)

        if ctx.out_error is None:
            result_message_class = ctx.descriptor.out_message

            # assign raw result to its wrapper, result_message
            out_type_info = result_message_class.get_flat_type_info(result_message_class)
            if len(out_type_info) == 1:
                out_class = out_type_info.values()[0]
                if ctx.out_object is None:
                    ctx.out_document = ['']
                else:
                    ctx.out_document = out_class.to_string_iterable(ctx.out_object[0])
            else:
                raise ValueError("HttpRpc protocol can only serialize primitives.")
        else:
            ctx.out_document = ctx.out_error.to_string_iterable(ctx.out_error)

        self.event_manager.fire_event('serialize', ctx)

    def create_out_string(self, ctx, out_string_encoding='utf8'):
        ctx.out_string = ctx.out_document
