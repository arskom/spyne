
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

import logging
logger = logging.getLogger(__name__)

try:
    from urlparse import parse_qs
except ImportError: # Python 3
    from urllib.parse import parse_qs

from rpclib.model.fault import Fault
from rpclib.error import ValidationError
from rpclib.protocol import ProtocolBase

# this is not exactly ReST, because it ignores http verbs.

def _get_http_headers(req_env):
    retval = {}

    for k, v in req_env.items():
        if k.startswith("HTTP_"):
            retval[k[5:].lower()]= [v]

    return retval

class HttpRpc(ProtocolBase):
    """The so-called REST-minus-the-verbs HttpRpc protocol implementation.
    It only works with the http server (wsgi) transport.

    It only parses requests where the whole data is in the 'QUERY_STRING', i.e.
    the part after '?' character in a URI string.
    """

    def set_validator(self, validator):
        if validator == 'soft' or validator is self.SOFT_VALIDATION:
            self.validator = self.SOFT_VALIDATION
        elif validator is None:
            self.validator = None
        else:
            raise ValueError(validator)

    def create_in_document(self, ctx, in_string_encoding=None):
        assert ctx.transport.type == 'wsgi', ("This protocol only works with "
                                              "the wsgi api.")

        ctx.in_document = ctx.transport.req_env

    def decompose_incoming_envelope(self, ctx):
        ctx.method_request_string = '{%s}%s' % (self.app.interface.get_tns(),
                              ctx.in_document['PATH_INFO'].split('/')[-1])
        logger.debug("\033[92mMethod name: %r\033[0m" % ctx.method_request_string)

        ctx.in_header_doc = _get_http_headers(ctx.in_document)
        ctx.in_body_doc = parse_qs(ctx.in_document['QUERY_STRING'])

        logger.debug('header : %r' % (ctx.in_header_doc))
        logger.debug('body   : %r' % (ctx.in_body_doc))

    def dict_to_object(self, doc, inst_class):
        simple_type_info = inst_class.get_simple_type_info(inst_class)
        inst = inst_class.get_deserialization_instance()

        # this is for validating cls.Attributes.{min,max}_occurs
        frequencies = {}

        for k, v in doc.items():
            member = simple_type_info.get(k, None)
            if member is None:
                continue

            mo = member.type.Attributes.max_occurs
            value = getattr(inst, k, None)
            if value is None:
                value = []

            for v2 in v:
                if (self.validator is self.SOFT_VALIDATION and not
                            member.type.validate_string(member.type, v2)):
                    raise ValidationError(v2)
                native_v2 = member.type.from_string(v2)
                if (self.validator is self.SOFT_VALIDATION and not
                            member.type.validate_native(member.type, native_v2)):
                    raise ValidationError(v2)

                value.append(native_v2)

                freq = frequencies.get(member.path, 0)
                freq += 1
                frequencies[member.path] = freq
                print "! ", member.path, native_v2
                for i in range(1,len(member.path)):
                    frequencies[member.path[:i]] = 1
                    print "!!", member.path[:i]

            if mo == 1:
                value = value[0]

            cinst = inst
            ctype_info = inst_class.get_flat_type_info(inst_class)
            for i in range(len(member.path) - 1):
                pkey = member.path[i]
                if not (ctype_info[pkey].Attributes.max_occurs in (0,1)):
                    raise Exception("HttpRpc deserializer does not support "
                                    "non-primitives with max_occurs > 1")

                ninst = getattr(cinst, pkey, None)
                if ninst is None:
                    ninst = ctype_info[pkey].get_serialization_instance([])
                    setattr(cinst, pkey, ninst)
                cinst = ninst

                ctype_info = ctype_info[pkey]._type_info

            print cinst, member.path[-1], value
            setattr(cinst, member.path[-1], value)

        print
        if self.validator is self.SOFT_VALIDATION:
            sti = simple_type_info.values()
            sti.sort(key=lambda x: (len(x.path), x.path))
            pfrag = None
            for s in sti:
                if len(s.path) > 1 and pfrag != s.path[:-1]:
                    pfrag = s.path[:-1]
                    print pfrag, frequencies.get(pfrag,0)

                key = s.path
                val = frequencies.get(key, 0)
                print s.path,val
                if val < s.type.Attributes.min_occurs \
                        or  (s.type.Attributes.max_occurs != 'unbounded'
                                        and val > s.type.Attributes.max_occurs):
                    raise Fault('Client.ValidationError',
                                '%r member does not respect frequency '
                                'constraints' % k)

        return inst

    def deserialize(self, ctx, message):
        assert message in (self.REQUEST,)

        self.event_manager.fire_event('before_deserialize', ctx)

        if ctx.in_header_doc is not None:
            ctx.in_header = self.dict_to_object(ctx.in_header_doc,
                                                    ctx.descriptor.in_header)

        if ctx.in_body_doc is not None:
            ctx.in_object = self.dict_to_object(ctx.in_body_doc,
                                                    ctx.descriptor.in_message)
        else:
            ctx.in_object = [None] * len(
                        ctx.descriptor.in_message.get_flat_type_info(
                                                    ctx.descriptor.in_message))

        self.event_manager.fire_event('after_deserialize', ctx)

    def serialize(self, ctx, message):
        assert message in (self.RESPONSE,)

        if ctx.out_error is None:
            result_message_class = ctx.descriptor.out_message

            # assign raw result to its wrapper, result_message
            out_type_info = result_message_class.get_flat_type_info(result_message_class)
            if len(out_type_info) == 1:
                out_class = out_type_info.values()[0]
                if ctx.out_object is None:
                    ctx.out_document = ['']
                else:
                    if hasattr(out_class, 'to_string_iterable'):
                        ctx.out_document = out_class.to_string_iterable(ctx.out_object[0])
                    else:
                        raise ValueError("HttpRpc protocol can only serialize primitives. %r" % out_class)
            else:
                raise ValueError("HttpRpc protocol can only serialize simple return values.")
        else:
            ctx.out_document = ctx.out_error.to_string_iterable(ctx.out_error)

        self.event_manager.fire_event('serialize', ctx)

    def create_out_string(self, ctx, out_string_encoding='utf8'):
        ctx.out_string = ctx.out_document
