
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

import tempfile
TEMPORARY_DIR = None

try:
    import simplejson as json
except ImportError:
    import json

try:
    from cStringIO import StringIO
except ImportError:
    try:
        from StringIO import StringIO
    except ImportError: # Python 3
        from io import StringIO

from rpclib.model.fault import Fault
from rpclib.model.complex import ComplexModelBase
from rpclib.model.primitive import DateTime
from rpclib.model.primitive import Decimal
from rpclib.protocol import ProtocolBase

def get_stream_factory(dir=None, delete=True):
    def stream_factory(total_content_length, filename, content_type,
                                                               content_length=None):
        if total_content_length >= 512 * 1024 or delete == False:
            if delete == False:
                retval = tempfile.NamedTemporaryFile('wb+', dir=dir, delete=delete) # You need python >= 2.6 for this.
            else:
                retval = tempfile.NamedTemporaryFile('wb+', dir=dir)
        else:
            retval = StringIO()

        return retval
    return stream_factory


class JsonObject(ProtocolBase):
    """An implementation of the json protocol that uses simplejson or json
    packages.
    """

    mime_type = 'application/json'

    def __init__(self, app=None, validator=None, skip_depth=0):
        """
        :param app: The Application definition.
        :param validator: Validator type. One of ('soft', None).
        :param skip_depth: Number of wrapper classes to ignore. This is
        typically one of (0, 1, 2) but higher numbers may also work for your.
        """

        ProtocolBase.__init__(self, app, validator)

        self.skip_depth = skip_depth

    def set_validator(self, validator):
        if validator == 'soft' or validator is self.SOFT_VALIDATION:
            self.validator = self.SOFT_VALIDATION
        elif validator is None:
            self.validator = None
        else:
            raise ValueError(validator)

    def create_in_document(self, ctx, in_string_encoding=None):
        """Sets ``ctx.in_document``,  using ``ctx.in_string``."""

        if in_string_encoding is None:
            in_string_encoding = 'UTF-8'

        ctx.in_document = json.loads(''.join(ctx.in_string) \
                                                    .decode(in_string_encoding))

    def decompose_incoming_envelope(self, ctx):
        """Sets ``ctx.in_body_doc``, ``ctx.in_header_doc`` and
        ``ctx.method_request_string`` using ``ctx.in_document``.
        """

        # set ctx.in_header
        ctx.transport.in_header_doc = None # use an rpc protocol if you want headers.

        # set ctx.in_body
        doc = ctx.in_document

        # get rid of ``skip_depth`` number of wrappers. 
        for _ in range(self.skip_depth):
            if len(doc) == 0:
                raise Fault("Client", "Empty request.")
            elif len(doc) > 1:
                raise Fault("Client", "Ambiguous request.")

            doc = doc[ doc.keys()[0] ]

        ctx.in_body_doc = doc

        if len(doc) == 0:
            raise Fault("Client", "Empty request")

        # set ctx.method_request_string
        ctx.method_request_string = '{%s}%s' % (self.app.interface.get_tns(),
                                                                doc.keys()[0])

        logger.debug('\theader : %r' % (ctx.in_header_doc))
        logger.debug('\tbody   : %r' % (ctx.in_body_doc))

    def dict_to_object(self, doc, inst_class):
        if doc is None:
            return

        inst = inst_class.get_deserialization_instance()

        # get all class attributes, including the ones coming from parent classes.
        flat_type_info = inst_class.get_flat_type_info(inst_class)
        from pprint import pformat

        print inst_class
        print pformat(flat_type_info)

        # initialize instance
        for k in flat_type_info:
            setattr(inst, k, None)

        # this is for validating cls.Attributes.{min,max}_occurs
        frequencies = {}

        # parse input to set incoming data to related attributes.
        for k,v in doc.items():
            freq = frequencies.get(k, 0)
            freq += 1
            frequencies[k] = freq

            print k, v, flat_type_info
            member = flat_type_info.get(k, None)
            if member is None:
                continue

            mo = member.Attributes.max_occurs
            if mo > 1:
                value = getattr(inst, k, None)
                if value is None:
                    value = []

                for a in v:
                    value.append(self.from_dict_value(member, a))

            else:
                value = self.from_dict_value(member, v)

            setattr(inst, k, value)

        if self.validator is self.SOFT_VALIDATION:
            for k, v in flat_type_info.items():
                val = frequencies.get(k, 0)
                if (val < v.Attributes.min_occurs or val > v.Attributes.max_occurs):
                    raise Fault('Client.ValidationError',
                        '%r member does not respect frequency constraints' % k)

        return inst

    def deserialize(self, ctx, message):
        self.event_manager.fire_event('before_deserialize', ctx)

        if ctx.descriptor is None:
            raise Fault("Client", "Method %r not found." %
                                                      ctx.method_request_string)

        if ctx.descriptor.in_message:
            # assign raw result to its wrapper, result_message
            result_message_class = ctx.descriptor.in_message
            value = ctx.in_body_doc.get(result_message_class.get_type_name(), None)
            result_message = self.dict_to_object(value, result_message_class)

            ctx.in_object = result_message

            self.event_manager.fire_event('after_deserialize', ctx)

        else:
            ctx.in_object = []

        print ctx.in_object

    def serialize(self, ctx, message):
        assert message in (self.REQUEST, self.RESPONSE)

        self.event_manager.fire_event('before_serialize', ctx)

        if ctx.out_error is not None:
            # FIXME: There's no way to alter soap response headers for the user.
            ctx.out_document = ctx.out_error.to_dict(ctx.out_error)

        else:
            # instantiate the result message
            if message is self.REQUEST:
                result_message_class = ctx.descriptor.in_message
            elif message is self.RESPONSE:
                result_message_class = ctx.descriptor.out_message

            result_message = result_message_class()

            # assign raw result to its wrapper, result_message
            out_type_info = result_message_class._type_info

            for i in range(len(out_type_info)):
                attr_name = result_message_class._type_info.keys()[i]
                setattr(result_message, attr_name, ctx.out_object[i])

            # transform the results into a dict:
            doc = {result_message_class.get_type_name():
                           self.to_dict(result_message_class, result_message)}

            out_type = result_message_class
            # get rid of ``skip_depth`` number of wrappers.
            for i in range(self.skip_depth):
                if i == 0:
                    doc = doc.values()[0]
                elif len(out_type._type_info) == 1:
                    doc = doc.values()[0]
                    out_type = out_type._type_info[0]
                else:
                    doc = doc.values()
                    break

            ctx.out_document = doc

        self.event_manager.fire_event('after_serialize', ctx)

    def create_out_string(self, ctx, out_string_encoding='utf8'):
        ctx.out_string = [json.dumps(ctx.out_document)]
        print ctx.out_string[0]

    def from_dict_value(self, cls, value):
        if issubclass(cls, ComplexModelBase):
            return self.dict_to_object(value, cls)
        else:
            return value

    def get_member_pairs(self, cls, inst):
        parent_cls = getattr(cls, '__extends__', None)
        if not (parent_cls is None):
            for r in self.get_member_pairs(parent_cls, inst):
                yield r

        for k, v in cls._type_info.items():
            mo = v.Attributes.max_occurs
            try:
                subvalue = getattr(inst, k, None)
            except: # to guard against e.g. sqlalchemy throwing NoSuchColumnError
                subvalue = None

            if mo > 1:
                if subvalue != None:
                    yield (k, [v.to_string(sv) for sv in subvalue])

            else:
                if issubclass(v, ComplexModelBase):
                    yield (k, self.to_dict(v, subvalue))
                elif issubclass(v, DateTime):
                    yield (k, v.to_string(subvalue))
                elif issubclass(v, Decimal):
                    if v.Attributes.format is None:
                        yield (k, subvalue)
                    else:
                        yield (k, v.to_string(subvalue))
                else:
                    yield (k, subvalue)


    def to_dict(self, cls, value):
        inst = cls.get_serialization_instance(value)

        return dict(self.get_member_pairs(cls, inst))
