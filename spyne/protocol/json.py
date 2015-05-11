
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

"""The ``spyne.protocol.json`` package contains the Json-related protocols.
Currently, only :class:`spyne.protocol.json.JsonDocument` is supported.

Initially released in 2.8.0-rc.

Missing Types
=============

The JSON standard does not define every type that Spyne supports. These include
Date/Time types as well as arbitrary-length integers and arbitrary-precision
decimals. Integers are parsed to ``int``\s or ``long``\s seamlessly but
``Decimal``\s are only parsed correctly when they come off as strings.

While it's possible to e.g. (de)serialize floats to ``Decimal``\s by adding
hooks to ``parse_float`` [#]_ (and convert later as necessary), such
customizations apply to the whole incoming document which pretty much messes up
``AnyDict`` serialization and deserialization.

It also wasn't possible to work with ``object_pairs_hook`` as Spyne's parsing
is always "from outside to inside" whereas ``object_pairs_hook`` is passed
``dict``\s basically in any order "from inside to outside".

.. [#] http://docs.python.org/2/library/json.html#json.loads
"""

from __future__ import absolute_import

import logging
logger = logging.getLogger(__name__)

from spyne.util import six

from itertools import chain

try:
    import simplejson as json
    from simplejson.decoder import JSONDecodeError
except ImportError:
    import json
    JSONDecodeError = ValueError

from spyne.error import ValidationError
from spyne.error import ResourceNotFoundError

from spyne.model.binary import BINARY_ENCODING_BASE64
from spyne.model.primitive import Date
from spyne.model.primitive import Time
from spyne.model.primitive import DateTime
from spyne.model.primitive import Double
from spyne.model.primitive import Integer
from spyne.model.primitive import Boolean
from spyne.model.fault import Fault
from spyne.protocol.dictdoc import HierDictDocument


class JsonEncoder(json.JSONEncoder):
    def default(self, o):
        try:
            return super(JsonEncoder, self).default(o)

        except TypeError as e:
            # if json can't serialize it, it's possibly a generator. If not,
            # additional hacks are welcome :)
            if logger.level == logging.DEBUG:
                logger.exception(e)
            return list(o)


class JsonDocument(HierDictDocument):
    """An implementation of the json protocol that uses simplejson package when
    available, json package otherwise.

    :param ignore_wrappers: Does not serialize wrapper objects.
    :param complex_as: One of (list, dict). When list, the complex objects are
        serialized to a list of values instead of a dict of key/value pairs.
    """

    mime_type = 'application/json'

    type = set(HierDictDocument.type)
    type.add('json')

    default_binary_encoding = BINARY_ENCODING_BASE64

    # flags used just for tests
    _decimal_as_string = True

    def __init__(self, app=None, validator=None, mime_type=None,
                        ignore_uncap=False,
                        # DictDocument specific
                        ignore_wrappers=True, complex_as=dict, ordered=False,
                        default_string_encoding=None, polymorphic=False,
                        **kwargs):

        super(JsonDocument, self).__init__(app, validator, mime_type, ignore_uncap,
                               ignore_wrappers, complex_as, ordered, polymorphic)

        # this is needed when we're overriding a regular instance attribute
        # with a property.
        self.__message = HierDictDocument.__getattribute__(self, 'message')

        self._from_unicode_handlers[Double] = self._ret
        self._from_unicode_handlers[Boolean] = self._ret
        self._from_unicode_handlers[Integer] = self._ret

        self._to_unicode_handlers[Double] = self._ret
        self._to_unicode_handlers[Boolean] = self._ret
        self._to_unicode_handlers[Integer] = self._ret

        self.default_string_encoding = default_string_encoding
        self.kwargs = kwargs

    def _ret(self, cls, value):
        return value

    def validate(self, key, cls, val):
        super(JsonDocument, self).validate(key, cls, val)

        if issubclass(cls, (DateTime, Date, Time)) and not (
                                    isinstance(val, six.string_types) and
                                                 cls.validate_string(cls, val)):
            raise ValidationError(key, val)

    @property
    def message(self):
        return self.__message

    @message.setter
    def message(self, val):
        if val is self.RESPONSE and not ('cls' in self.kwargs):
            self.kwargs['cls'] = JsonEncoder
        self.__message = val

    def create_in_document(self, ctx, in_string_encoding=None):
        """Sets ``ctx.in_document``  using ``ctx.in_string``."""

        try:
            in_string = b''.join(ctx.in_string)
            if not isinstance(in_string, six.text_type):
                if in_string_encoding is None:
                    in_string_encoding = self.default_string_encoding
                if in_string_encoding is not None:
                    in_string = in_string.decode(in_string_encoding)
            ctx.in_document = json.loads(in_string, **self.kwargs)

        except JSONDecodeError as e:
            raise Fault('Client.JsonDecodeError', repr(e))

    def create_out_string(self, ctx, out_string_encoding='utf8'):
        """Sets ``ctx.out_string`` using ``ctx.out_document``."""
        ctx.out_string = (json.dumps(o, **self.kwargs).encode(out_string_encoding) for o in ctx.out_document)


class JsonP(JsonDocument):
    """The JsonP protocol puts the reponse document inside a designated
    javascript function call. The input protocol is identical to the
    JsonDocument protocol.

    :param callback_name: The name of the function call that will wrapp all
        response documents.

    For other arguents, see :class:`spyne.protocol.json.JsonDocument`.
    """

    type = set(HierDictDocument.type)
    type.add('jsonp')

    def __init__(self, callback_name, *args, **kwargs):
        super(JsonP, self).__init__(*args, **kwargs)
        self.callback_name = callback_name

    def create_out_string(self, ctx):
        super(JsonP, self).create_out_string(ctx)

        ctx.out_string = chain(
                [self.callback_name, '('],
                    ctx.out_string,
                [');'],
            )

class _SpyneJsonRpc1(JsonDocument):
    version = 1
    VERSION = 'ver'
    BODY = 'body'
    HEAD = 'head'
    FAULT = 'fault'

    def decompose_incoming_envelope(self, ctx, message=JsonDocument.REQUEST):
        indoc = ctx.in_document
        if not isinstance(indoc, dict):
            raise ValidationError("Invalid Request")

        ver = indoc.get(self.VERSION)
        if ver is None:
            raise ValidationError("Missing Version")

        body = indoc.get(self.BODY)
        err = indoc.get(self.FAULT)
        if body is None and err is None:
            raise ValidationError("Missing request")

        ctx.protocol.error = False
        if err is not None:
            ctx.in_body_doc = err
            ctx.protocol.error = True
        else:
            if not isinstance(body, dict):
                raise ValidationError("Missing request body")
            if not len(body) == 1:
                raise ValidationError("Need len(body) == 1")

            ctx.in_header_doc = indoc.get(self.HEAD)
            if not isinstance(ctx.in_header_doc, list):
                ctx.in_header_doc = [ctx.in_header_doc]

            (ctx.method_request_string,ctx.in_body_doc), = body.items()

    def deserialize(self, ctx, message):
        assert message in (self.REQUEST, self.RESPONSE)

        self.event_manager.fire_event('before_deserialize', ctx)

        if ctx.descriptor is None:
            raise ResourceNotFoundError(ctx.method_request_string)

        if ctx.protocol.error:
            ctx.in_object = None
            ctx.in_error = self._doc_to_object(Fault, ctx.in_body_doc)

        else:
            if message is self.REQUEST:
                header_class = ctx.descriptor.in_header
                body_class = ctx.descriptor.in_message

            elif message is self.RESPONSE:
                header_class = ctx.descriptor.out_header
                body_class = ctx.descriptor.out_message

            # decode header objects
            if (ctx.in_header_doc is not None and header_class is not None):
                headers = [None] * len(header_class)
                for i, (header_doc, head_class) in enumerate(
                                          zip(ctx.in_header_doc, header_class)):
                    if header_doc is not None and i < len(header_doc):
                        headers[i] = self._doc_to_object(head_class, header_doc)

                if len(headers) == 1:
                    ctx.in_header = headers[0]
                else:
                    ctx.in_header = headers
            # decode method arguments
            if ctx.in_body_doc is None:
                ctx.in_object = [None] * len(body_class._type_info)
            else:
                ctx.in_object = self._doc_to_object(body_class, ctx.in_body_doc)

        self.event_manager.fire_event('after_deserialize', ctx)

    def serialize(self, ctx, message):
        assert message in (self.REQUEST, self.RESPONSE)

        self.event_manager.fire_event('before_serialize', ctx)

        # construct the soap response, and serialize it
        nsmap = self.app.interface.nsmap
        ctx.out_document = {
            "ver": self.version,
        }
        if ctx.out_error is not None:
            ctx.out_document[self.FAULT] = Fault.to_dict(Fault, ctx.out_error)

        else:
            if message is self.REQUEST:
                header_message_class = ctx.descriptor.in_header
                body_message_class = ctx.descriptor.in_message

            elif message is self.RESPONSE:
                header_message_class = ctx.descriptor.out_header
                body_message_class = ctx.descriptor.out_message

            # assign raw result to its wrapper, result_message
            out_type_info = body_message_class._type_info
            out_object = body_message_class()

            keys = iter(out_type_info)
            values = iter(ctx.out_object)
            while True:
                try:
                    k = next(keys)
                except StopIteration:
                    break
                try:
                    v = next(values)
                except StopIteration:
                    v = None

                setattr(out_object, k, v)

            ctx.out_document[self.BODY] = ctx.out_body_doc = \
                            self._object_to_doc(body_message_class, out_object)

            # header
            if ctx.out_header is not None and header_message_class is not None:
                if isinstance(ctx.out_header, (list, tuple)):
                    out_headers = ctx.out_header
                else:
                    out_headers = (ctx.out_header,)

                ctx.out_header_doc = out_header_doc = []

                for header_class, out_header in zip(header_message_class,
                                                                   out_headers):
                    out_header_doc.append(self._object_to_doc(header_class,
                                                                    out_header))

                if len(out_header_doc) > 1:
                    ctx.out_document[self.HEAD] = out_header_doc
                else:
                    ctx.out_document[self.HEAD] = out_header_doc[0]

        self.event_manager.fire_event('after_serialize', ctx)


_json_rpc_flavours = {
    'spyne': _SpyneJsonRpc1
}

def JsonRpc(flavour, *args, **kwargs):
    assert flavour in _json_rpc_flavours, "Unknown JsonRpc flavour. " \
                             "Accepted ones are: %r" % tuple(_json_rpc_flavours)

    return _json_rpc_flavours[flavour](*args, **kwargs)
