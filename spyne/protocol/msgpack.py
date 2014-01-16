
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

This module is EXPERIMENTAL. You may not recognize the code here next time you
look at it.
"""

from __future__ import absolute_import

import logging
logger = logging.getLogger(__name__)

from spyne.util import six

import msgpack

from spyne.model.fault import Fault
from spyne.protocol.dictdoc import HierDictDocument
from spyne.protocol._model import integer_to_string
from spyne.protocol._model import integer_from_string
from spyne.model.primitive import Double
from spyne.model.primitive import Boolean
from spyne.model.primitive import Integer


class MessagePackDecodeError(Fault):
    def __init__(self, data=None):
        super(MessagePackDecodeError, self).__init__("Client.MessagePackDecodeError", data)


def _integer_from_string(cls, value):
    if isinstance(value, six.string_types):
        return integer_from_string(cls, value)
    else:
        return value

def _integer_to_string(cls, value):
    if -1<<63 <= value < 1<<64: # if it's inside the range msgpack can deal with
        return value
    else:
        return integer_to_string(cls, value)

class MessagePackDocument(HierDictDocument):
    """An integration class for the msgpack protocol."""

    mime_type = 'application/x-msgpack'

    type = set(HierDictDocument.type)
    type.add('msgpack')

    # flags to be used in tests
    _decimal_as_string = True
    _huge_numbers_as_string = True

    def __init__(self, app=None, validator=None, mime_type=None,
                                        ignore_uncap=False,
                                        # DictDocument specific
                                        ignore_wrappers=True,
                                        complex_as=dict,
                                        ordered=False):

        super(MessagePackDocument, self).__init__(app, validator, mime_type, ignore_uncap,
                                           ignore_wrappers, complex_as, ordered)

        self._from_string_handlers[Double] = lambda cls, val: val
        self._from_string_handlers[Boolean] = lambda cls, val: val
        self._from_string_handlers[Integer] = _integer_from_string

        self._to_string_handlers[Double] = lambda cls, val: val
        self._to_string_handlers[Boolean] = lambda cls, val: val
        self._to_string_handlers[Integer] = _integer_to_string

    def create_in_document(self, ctx, in_string_encoding=None):
        """Sets ``ctx.in_document``,  using ``ctx.in_string``.

        :param ctx: The MethodContext object
        :param in_string_encoding: MessagePack is a binary protocol. So this
            argument is ignored.
        """

        try:
            ctx.in_document = msgpack.unpackb(''.join(ctx.in_string))
        except ValueError as e:
            raise MessagePackDecodeError(''.join(e.args))

        if not isinstance(ctx.in_document, dict):
            logger.debug("reqobj: %r", ctx.in_document)
            raise MessagePackDecodeError("Request object must be a dictionary")

    def create_out_string(self, ctx, out_string_encoding='utf8'):
        ctx.out_string = (msgpack.packb(o) for o in ctx.out_document)


class MessagePackRpc(MessagePackDocument):
    """An integration class for the msgpack-rpc protocol."""

    mime_type = 'application/x-msgpack'

    MSGPACK_REQUEST = 0
    MSGPACK_RESPONSE = 1
    MSGPACK_NOTIFY = 2

    def create_in_document(self, ctx, in_string_encoding=None):
        """Sets ``ctx.in_document``,  using ``ctx.in_string``.

        :param ctx: The MethodContext object
        :param in_string_encoding: MessagePack is a binary protocol. So this
            argument is ignored.
        """

        # TODO: Use feed api
        try:
            ctx.in_document = msgpack.unpackb(''.join(ctx.in_string))
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
            msgtype, msgid, msgname = ctx.in_document

        elif len(ctx.in_document) == 4:
            msgtype, msgid, msgname, msgparams = ctx.in_document

        if msgtype == MessagePackRpc.MSGPACK_REQUEST:
            assert message == MessagePackRpc.REQUEST

        elif msgtype == MessagePackRpc.MSGPACK_RESPONSE:
            assert message == MessagePackRpc.RESPONSE

        elif msgtype == MessagePackRpc.MSGPACK_NOTIFY:
            raise NotImplementedError()

        else:
            raise MessagePackDecodeError("Unknown message type %r" % msgtype)

        ctx.method_request_string = '{%s}%s' % (self.app.interface.get_tns(),
                                                                        msgname)

        ctx.in_header_doc = None # MessagePackRpc does not seem to have Header support
        ctx.in_body_doc = msgparams

        logger.debug('\theader : %r' % (ctx.in_header_doc))
        logger.debug('\tbody   : %r' % (ctx.in_body_doc))

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

        if body_class:
            ctx.in_object = body_class.get_serialization_instance(
                                                                ctx.in_body_doc)

        else:
            ctx.in_object = []

        self.event_manager.fire_event('after_deserialize', ctx)

    def serialize(self, ctx, message):
        assert message in (self.REQUEST, self.RESPONSE)

        self.event_manager.fire_event('before_serialize', ctx)

        if ctx.out_error is not None:
            ctx.out_document = [MessagePackRpc.MSGPACK_RESPONSE, 0,
                         Fault.to_dict(ctx.out_error.__class__,  ctx.out_error)]

        else:
            # get the result message
            if message is self.REQUEST:
                out_type = ctx.descriptor.in_message
            elif message is self.RESPONSE:
                out_type = ctx.descriptor.out_message
            else:
                raise Exception("what?")

            if out_type is None:
                return

            out_type_info = out_type._type_info

            # instantiate the result message
            out_instance = out_type()

            # assign raw result to its wrapper, result_message
            for i in range(len(out_type_info)):
                attr_name = out_type_info.keys()[i]
                setattr(out_instance, attr_name, ctx.out_object[i])

            # transform the results into a dict:
            if out_type.Attributes.max_occurs > 1:
                ctx.out_document = [[MessagePackRpc.MSGPACK_RESPONSE, 0, None,
                        (self._to_value(out_type, inst)
                                                      for inst in out_instance)
                    ]]
            else:
                ctx.out_document = [[MessagePackRpc.MSGPACK_RESPONSE, 0, None,
                                        self._to_value(out_type, out_instance),
                                   ]]

            self.event_manager.fire_event('after_serialize', ctx)
