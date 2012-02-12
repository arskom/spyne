
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

"""This module contains the HttpRpc protocol implementation. This is not exactly
Rest, because it ignores Http verbs.
"""

import logging
logger = logging.getLogger(__name__)

try:
    from urlparse import parse_qs
except ImportError: # Python 3
    from urllib.parse import parse_qs

from rpclib.error import ValidationError
from rpclib.model.binary import ByteArray
from rpclib.model.fault import Fault
from rpclib.protocol import ProtocolBase

from werkzeug.formparser import parse_form_data

STREAM_READ_BLOCK_SIZE = 16384

def yield_stream(istr):
    data = istr.read(STREAM_READ_BLOCK_SIZE)
    while len(data) > 0:
        yield data
        data = istr.read(STREAM_READ_BLOCK_SIZE)

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

        if ctx.transport.req_env['REQUEST_METHOD'].lower() in ('post', 'put', 'patch'):
            stream, form, files = parse_form_data(ctx.transport.req_env)

            for k, v in form.lists():
                val = ctx.in_body_doc.get(k, [])
                val.extend(v)
                ctx.in_body_doc[k] = val

            for k, v in files.items():
                val = ctx.in_body_doc.get(k, [])
                val.append(yield_stream(v.stream))
                ctx.in_body_doc[k] = val

                # FIXME: some proper variable matching is needed here.
                k2 = k + "_name"
                val = ctx.in_body_doc.get(k2, [])
                val.append(v.filename)
                ctx.in_body_doc[k2] = val

                k2 = k + "_type"
                val = ctx.in_body_doc.get(k2, [])
                val.append(v.headers.get('Content-Type','application/octet-stream'))
                ctx.in_body_doc[k2] = val

        logger.debug('\theader : %r' % (ctx.in_header_doc))
        logger.debug('\tbody   : %r' % (ctx.in_body_doc))

    def dict_to_object(self, doc, inst_class):
        simple_type_info = inst_class.get_simple_type_info(inst_class)
        inst = inst_class.get_deserialization_instance()

        # this is for validating cls.Attributes.{min,max}_occurs
        frequencies = {}

        for k, v in doc.items():
            member = simple_type_info.get(k, None)
            if member is None:
                logger.debug("discarding field %r" % k)
                continue

            mo = member.type.Attributes.max_occurs
            value = getattr(inst, k, None)
            if value is None:
                value = []
            elif mo == 1:
                raise Fault('Client.ValidationError',
                        '"%s" member must occur at most %d times' % (k, max_o))

            for v2 in v:
                if (self.validator is self.SOFT_VALIDATION and not
                            member.type.validate_string(member.type, v2)):
                    raise ValidationError(v2)

                if member.type is ByteArray or \
                        getattr(member.type, '_is_clone_of', None) is ByteArray:
                    if isinstance(v2, str) or isinstance(v2, unicode):
                        native_v2 = member.type.from_string(v2)
                    else:
                        native_v2 = v2
                else:
                    native_v2 = member.type.from_string(v2)

                if (self.validator is self.SOFT_VALIDATION and not
                            member.type.validate_native(member.type, native_v2)):
                    raise ValidationError(v2)

                value.append(native_v2)

                # set frequencies of parents.
                if not (member.path[:-1] in frequencies):
                    for i in range(1,len(member.path)):
                        logger.debug("\tset freq %r = 1" % (member.path[:i],))
                        frequencies[member.path[:i]] = 1

                freq = frequencies.get(member.path, 0)
                freq += 1
                frequencies[member.path] = freq
                logger.debug("\tset freq %r = %d" % (member.path, freq))

            if mo == 1:
                value = value[0]

            cinst = inst
            ctype_info = inst_class.get_flat_type_info(inst_class)
            pkey = member.path[0]
            for i in range(len(member.path) - 1):
                pkey = member.path[i]
                if not (ctype_info[pkey].Attributes.max_occurs in (0,1)):
                    raise Exception("HttpRpc deserializer does not support "
                                    "non-primitives with max_occurs > 1")

                ninst = getattr(cinst, pkey, None)
                if ninst is None:
                    ninst = ctype_info[pkey].get_deserialization_instance()
                    setattr(cinst, pkey, ninst)
                cinst = ninst

                ctype_info = ctype_info[pkey]._type_info

            if isinstance(cinst, list):
                cinst.extend(value)
                logger.debug("\tset array   %r(%r) = %r" %
                                                    (member.path, pkey, value))
            else:
                setattr(cinst, member.path[-1], value)
                logger.debug("\tset default %r(%r) = %r" %
                                                    (member.path, pkey, value))

        if self.validator is self.SOFT_VALIDATION:
            sti = simple_type_info.values()
            sti.sort(key=lambda x: (len(x.path), x.path))
            pfrag = None
            for s in sti:
                if len(s.path) > 1 and pfrag != s.path[:-1]:
                    pfrag = s.path[:-1]
                    ctype_info = inst_class.get_flat_type_info(inst_class)
                    for i in range(len(pfrag)):
                        f = pfrag[i]
                        ntype_info = ctype_info[f]

                        min_o = ctype_info[f].Attributes.min_occurs
                        max_o = ctype_info[f].Attributes.max_occurs
                        val = frequencies.get(pfrag[:i+1], 0)
                        if val < min_o:
                            raise Fault('Client.ValidationError',
                                '"%s" member must occur at least %d times'
                                              % ('_'.join(pfrag[:i+1]), min_o))

                        if max_o != 'unbounded' and val > max_o:
                            raise Fault('Client.ValidationError',
                                '"%s" member must occur at most %d times'
                                             % ('_'.join(pfrag[:i+1]), max_o))

                        ctype_info = ntype_info.get_flat_type_info(ntype_info)

                val = frequencies.get(s.path, 0)
                min_o = s.type.Attributes.min_occurs
                max_o = s.type.Attributes.max_occurs
                if val < min_o:
                    raise Fault('Client.ValidationError',
                                '"%s" member must occur at least %d times'
                                                    % ('_'.join(s.path), min_o))
                if max_o != 'unbounded' and val > max_o:
                    raise Fault('Client.ValidationError',
                                '"%s" member must occur at most %d times'
                                                    % ('_'.join(s.path), max_o))

        return inst

    def deserialize(self, ctx, message):
        assert message in (self.REQUEST,)

        self.event_manager.fire_event('before_deserialize', ctx)

        ctx.in_header = self.dict_to_object(ctx.in_header_doc,
                                                    ctx.descriptor.in_header)
        ctx.in_object = self.dict_to_object(ctx.in_body_doc,
                                                    ctx.descriptor.in_message)

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
            ctx.transport.mime_type = 'text/plain'
            ctx.out_document = ctx.out_error.to_string_iterable(ctx.out_error)

        self.event_manager.fire_event('serialize', ctx)

    def create_out_string(self, ctx, out_string_encoding='utf8'):
        ctx.out_string = ctx.out_document

    def get_call_handles(self, ctx):
        retval = super(HttpRpc, self).get_call_handles(ctx)

        if len(retval) == 0:
            pass

        return retval
