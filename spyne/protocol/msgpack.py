
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

"""The ``spyne.protocol.msgpack`` module contains implementations for protocols
that use MessagePack as serializer.

Initially released in 2.8.0-rc.

"""

from __future__ import absolute_import

import logging
logger = logging.getLogger(__name__)

import msgpack

from spyne import ValidationError
from spyne.util import six
from spyne.model.fault import Fault
from spyne.model.primitive import Double
from spyne.model.primitive import Boolean
from spyne.model.primitive import Integer
from spyne.protocol.dictdoc import HierDictDocument


class MessagePackDecodeError(Fault):
    CODE = "Client.MessagePackDecodeError"

    def __init__(self, data=None):
        super(MessagePackDecodeError, self) \
                                .__init__(self.CODE, data)


NON_NUMBER_TYPES = tuple({list, dict, six.text_type, six.binary_type})


class MessagePackDocument(HierDictDocument):
    """An integration class for the msgpack protocol."""

    mime_type = 'application/x-msgpack'
    text_based = False

    type = set(HierDictDocument.type)
    type.add('msgpack')

    default_string_encoding = 'UTF-8'
    from_serstr = HierDictDocument.from_bytes
    to_serstr = HierDictDocument.to_bytes

    # flags to be used in tests
    _decimal_as_string = True
    _huge_numbers_as_string = True

    def __init__(self, app=None, validator=None, mime_type=None,
                                        ignore_uncap=False,
                                        # DictDocument specific
                                        ignore_wrappers=True,
                                        complex_as=dict,
                                        ordered=False,
                                        polymorphic=False,
                                        key_encoding='utf8',
                                        # MessagePackDocument specific
                                        mw_packer=msgpack.Packer,
                                        mw_unpacker=msgpack.Unpacker,
                                        use_list=False,
                                        raw=False,
                                        use_bin_type=True,
                                        **kwargs):
        super(MessagePackDocument, self).__init__(app, validator, mime_type,
                ignore_uncap, ignore_wrappers, complex_as, ordered, polymorphic,
                                                                   key_encoding)

        self.mw_packer = mw_packer
        self.mw_unpacker = mw_unpacker

        # unpacker
        if not raw:
            self.from_serstr = self.from_unicode

        if use_bin_type:
            self.from_serstr = self.from_unicode

        self.kwargs_packer = dict(kwargs)
        self.kwargs_unpacker = dict(kwargs)
        self.kwargs_packer['raw'] = self.kwargs_unpacker['raw'] = raw
        self.kwargs_packer['use_list'] = self.kwargs_unpacker['use_list'] \
                                                                      = use_list
        self.kwargs_packer['use_bin_type'] = use_bin_type

        self._from_bytes_handlers[Double] = self._ret_number
        self._from_bytes_handlers[Boolean] = self._ret_bool
        self._from_bytes_handlers[Integer] = self.integer_from_bytes

        self._from_unicode_handlers[Double] = self._ret_number
        self._from_unicode_handlers[Boolean] = self._ret_bool
        self._from_unicode_handlers[Integer] = self.integer_from_bytes

        self._to_bytes_handlers[Double] = self._ret_number
        self._to_bytes_handlers[Boolean] = self._ret_bool
        self._to_bytes_handlers[Integer] = self.integer_to_bytes

        self._to_unicode_handlers[Double] = self._ret_number
        self._to_unicode_handlers[Boolean] = self._ret_bool
        self._to_unicode_handlers[Integer] = self.integer_to_bytes

    def _ret(self, _, value):
        return value

    def _ret_number(self, _, value):
        if isinstance(value, NON_NUMBER_TYPES):
            raise ValidationError(value)
        if value in (True, False):
            return int(value)
        return value

    def _ret_bool(self, _, value):
        if value is None or value in (True, False):
            return value
        raise ValidationError(value)

    def get_class_name(self, cls):
        class_name = cls.get_type_name()
        if not six.PY2:
            if not isinstance(class_name, bytes):
                class_name = class_name.encode(self.default_string_encoding)

        return class_name

    def create_in_document(self, ctx, in_string_encoding=None):
        """Sets ``ctx.in_document``,  using ``ctx.in_string``.

        :param ctx: The MethodContext object
        :param in_string_encoding: MessagePack is a binary protocol. So this
            argument is ignored.
        """

        # handle mmap objects from in ctx.in_string as returned by
        # TwistedWebResource.handle_rpc.
        if isinstance(ctx.in_string, (list, tuple)) \
                               and len(ctx.in_string) == 1 \
                               and isinstance(ctx.in_string[0], memoryview):
            unpacker = self.mw_unpacker(**self.kwargs_unpacker)
            unpacker.feed(ctx.in_string[0])
            ctx.in_document = next(x for x in unpacker)

        else:
            try:
                ctx.in_document = msgpack.unpackb(b''.join(ctx.in_string))
            except ValueError as e:
                raise MessagePackDecodeError(' '.join(e.args))

    def gen_method_request_string(self, ctx):
        """Uses information in context object to return a method_request_string.

        Returns a string in the form of "{namespaces}method name".
        """

        mrs, = ctx.in_body_doc.keys()
        if not six.PY2 and isinstance(mrs, bytes):
            mrs = mrs.decode(self.key_encoding)

        return '{%s}%s' % (self.app.interface.get_tns(), mrs)

    def create_out_string(self, ctx, out_string_encoding='utf8'):
        ctx.out_string = (msgpack.packb(o) for o in ctx.out_document)

    def integer_from_bytes(self, cls, value):
        if isinstance(value, (six.text_type, six.binary_type)):
            return super(MessagePackDocument, self) \
                                                .integer_from_bytes(cls, value)
        return value

    def integer_to_bytes(self, cls, value, **_):
        # if it's inside the range msgpack can deal with
        if -1<<63 <= value < 1<<64:
            return value
        else:
            return super(MessagePackDocument, self).integer_to_bytes(cls, value)


class MessagePackRpc(MessagePackDocument):
    """An integration class for the msgpack-rpc protocol."""

    mime_type = 'application/x-msgpack'

    MSGPACK_REQUEST = 0
    MSGPACK_RESPONSE = 1
    MSGPACK_NOTIFY = 2
    MSGPACK_ERROR = 3

    def create_out_string(self, ctx, out_string_encoding='utf8'):
        ctx.out_string = (msgpack.packb(o) for o in ctx.out_document)

    def create_in_document(self, ctx, in_string_encoding=None):
        """Sets ``ctx.in_document``,  using ``ctx.in_string``.

        :param ctx: The MethodContext object
        :param in_string_encoding: MessagePack is a binary protocol. So this
            argument is ignored.
        """

        # TODO: Use feed api
        try:
            ctx.in_document = msgpack.unpackb(b''.join(ctx.in_string),
                                                         **self.kwargs_unpacker)


        except ValueError as e:
            raise MessagePackDecodeError(''.join(e.args))

        try:
            len(ctx.in_document)
        except TypeError:
            raise MessagePackDecodeError("Input must be a sequence.")

        if not (3 <= len(ctx.in_document) <= 4):
            raise MessagePackDecodeError("Length of input iterable must be "
                                                                "either 3 or 4")

    def decompose_incoming_envelope(self, ctx, message):
        # FIXME: For example: {0: 0, 1: 0, 2: "some_call", 3: [1,2,3]} will also
        # work. Is this a problem?

        # FIXME: Msgid is ignored. Is this a problem?
        msgparams = []
        if len(ctx.in_document) == 3:
            msgtype, msgid, msgname_or_error = ctx.in_document

        else:
            msgtype, msgid, msgname_or_error, msgparams = ctx.in_document

        if not six.PY2:
            if isinstance(msgname_or_error, bytes):
                msgname_or_error = msgname_or_error.decode(
                                                   self.default_string_encoding)

        if msgtype == MessagePackRpc.MSGPACK_REQUEST:
            assert message == MessagePackRpc.REQUEST

        elif msgtype == MessagePackRpc.MSGPACK_RESPONSE:
            assert message == MessagePackRpc.RESPONSE

        elif msgtype == MessagePackRpc.MSGPACK_NOTIFY:
            raise NotImplementedError()

        else:
            raise MessagePackDecodeError("Unknown message type %r" % msgtype)

        ctx.method_request_string = '{%s}%s' % (self.app.interface.get_tns(),
                                                               msgname_or_error)

        # MessagePackRpc does not seem to have Header support
        ctx.in_header_doc = None

        if isinstance(msgname_or_error, dict) and msgname_or_error:
            # we got an error
            ctx.in_error = msgname_or_error
        else:
            ctx.in_body_doc = msgparams

        # logger.debug('\theader : %r', ctx.in_header_doc)
        # logger.debug('\tbody   : %r', ctx.in_body_doc)

    def deserialize(self, ctx, message):
        assert message in (self.REQUEST, self.RESPONSE)

        self.event_manager.fire_event('before_deserialize', ctx)

        if ctx.descriptor is None:
            raise Fault("Client", "Method %r not found." %
                                                      ctx.method_request_string)

        # instantiate the result message
        if message is self.REQUEST:
            body_class = ctx.descriptor.in_message
        elif message is self.RESPONSE:
            body_class = ctx.descriptor.out_message
        else:
            raise Exception("what?")

        if ctx.in_error:
            ctx.in_error = Fault(**ctx.in_error)

        elif body_class:
            ctx.in_object = self._doc_to_object(ctx,
                                    body_class, ctx.in_body_doc, self.validator)

        else:
            ctx.in_object = []

        self.event_manager.fire_event('after_deserialize', ctx)

    def serialize(self, ctx, message):
        assert message in (self.REQUEST, self.RESPONSE)

        self.event_manager.fire_event('before_serialize', ctx)

        if ctx.out_error is not None:
            ctx.out_document = [
                [MessagePackRpc.MSGPACK_ERROR, 0,
                    Fault.to_dict(ctx.out_error.__class__, ctx.out_error, self)]
            ]
            return

        # get the result message
        if message is self.REQUEST:
            out_type = ctx.descriptor.in_message
            msgtype = MessagePackRpc.MSGPACK_REQUEST
            method_name_or_error = ctx.descriptor.operation_name

        elif message is self.RESPONSE:
            out_type = ctx.descriptor.out_message
            msgtype = MessagePackRpc.MSGPACK_RESPONSE
            method_name_or_error = None

        else:
            raise Exception("what?")

        if out_type is None:
            return

        out_type_info = out_type._type_info

        # instantiate the result message
        out_instance = out_type()

        # assign raw result to its wrapper, result_message
        for i, (k, v) in enumerate(out_type_info.items()):
            attrs = self.get_cls_attrs(v)
            out_instance._safe_set(k, ctx.out_object[i], v, attrs)

        # transform the results into a dict:
        if out_type.Attributes.max_occurs > 1:
            params = (self._to_dict_value(out_type, inst, set())
                                                       for inst in out_instance)
        else:
            params = self._to_dict_value(out_type, out_instance, set())

        ctx.out_document = [[msgtype, 0, method_name_or_error, params]]

        self.event_manager.fire_event('after_serialize', ctx)
