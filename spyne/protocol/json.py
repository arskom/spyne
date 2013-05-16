
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

This module is EXPERIMENTAL. You may not recognize the code here next time you
look at it.

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

from itertools import chain

try:
    import simplejson as json
    from simplejson.decoder import JSONDecodeError
except ImportError:
    import json
    JSONDecodeError = ValueError

from spyne.error import ValidationError

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

        except TypeError, e:
            # if json can't serialize it, it's possibly a generator. If not,
            # additional hacks are welcome :)
            logger.exception(e)
            return list(o)


class JsonDocument(HierDictDocument):
    """An implementation of the json protocol that uses simplejson package when
    available, json package otherwise.
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
                        ignore_wrappers=True, complex_as=dict, ordered=False):

        HierDictDocument.__init__(self, app, validator, mime_type, ignore_uncap,
                                           ignore_wrappers, complex_as, ordered)

        self._from_string_handlers[Double] = lambda cls, val: val
        self._from_string_handlers[Boolean] = lambda cls, val: val
        self._from_string_handlers[Integer] = lambda cls, val: val

        self._to_string_handlers[Double] = lambda cls, val: val
        self._to_string_handlers[Boolean] = lambda cls, val: val
        self._to_string_handlers[Integer] = lambda cls, val: val

    def validate(self, cls, val):
        super(JsonDocument, self).validate(cls, val)

        if issubclass(cls, (DateTime, Date, Time)) and not (
                                    isinstance(val, basestring) and
                                                 cls.validate_string(cls, val)):
            raise ValidationError(val)



    def create_in_document(self, ctx, in_string_encoding=None):
        """Sets ``ctx.in_document``  using ``ctx.in_string``."""

        if in_string_encoding is None:
            in_string_encoding = 'UTF-8'

        try:
            ctx.in_document = json.loads(
                            ''.join(ctx.in_string).decode(in_string_encoding),
                        )

        except JSONDecodeError, e:
            raise Fault('Client.JsonDecodeError', repr(e))

    def create_out_string(self, ctx, out_string_encoding='utf8'):
        """Sets ``ctx.out_string`` using ``ctx.out_document``."""
        ctx.out_string = (json.dumps(o, cls=JsonEncoder)
                                                      for o in ctx.out_document)


class JsonP(JsonDocument):
    """The JsonP protocol puts the reponse document inside a designated
    javascript function call. The input protocol is identical to the
    JsonDocument protocol.

    :param callback_name: The name of the function call that will wrapp all
        response documents.

    For other params, see :class:`spyne.protocol.json.JsonDocument`.
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
