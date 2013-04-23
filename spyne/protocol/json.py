
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
"""

from __future__ import absolute_import

import logging
logger = logging.getLogger(__name__)

import decimal

try:
    import simplejson as json
    from simplejson.decoder import JSONDecodeError
except ImportError:
    import json
    JSONDecodeError = ValueError

from spyne.model.fault import Fault
from spyne.protocol.dictdoc import NumStr
from spyne.protocol.dictdoc import HierDictDocument

class JsonEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return str(o)

        try:
            return super(JsonEncoder, self).default(o)

        except TypeError:
            # if it's not a Decimal and json still can't serialize it,
            # it's possibly a generator. If not, additional hacks are welcome :)
            return list(o)


class JsonDocument(HierDictDocument):
    """An implementation of the json protocol that uses simplejson package when
    available, json package otherwise.
    """

    mime_type = 'application/json'

    type = set(HierDictDocument.type)
    type.add('json')

    def __init__(self, app=None, validator=None, mime_type=None,
                                        ignore_uncap=False,
                                        # DictDocument specific
                                        ignore_wrappers=True,
                                        complex_as=dict,
                                        ordered=False):

        HierDictDocument.__init__(self, app, validator, mime_type, ignore_uncap,
                                           ignore_wrappers, complex_as, ordered)

        self._numbers_as_string = True

    def create_in_document(self, ctx, in_string_encoding=None):
        """Sets ``ctx.in_document``  using ``ctx.in_string``."""

        if in_string_encoding is None:
            in_string_encoding = 'UTF-8'

        try:
            ctx.in_document = json.loads(
                            ''.join(ctx.in_string).decode(in_string_encoding),
                            parse_float=NumStr, parse_int=NumStr,
                        )

        except JSONDecodeError, e:
            raise Fault('Client.JsonDecodeError', repr(e))

    def create_out_string(self, ctx, out_string_encoding='utf8'):
        """Sets ``ctx.out_string`` using ``ctx.out_document``."""
        ctx.out_string = (json.dumps(o, cls=JsonEncoder)
                                                      for o in ctx.out_document)


JsonObject = JsonDocument
"""DEPRECATED. Use :class:`spyne.protocol.json.JsonDocument` instead"""
