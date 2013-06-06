
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

from spyne.protocol.dictdoc import HierDictDocument
from spyne.protocol.json import json

from spyne.model.primitive import Double
from spyne.model.primitive import Boolean
from spyne.model.primitive import Decimal
from spyne.model.primitive import Integer


class _UtilProtocol(HierDictDocument):
    def __init__(self, app=None, validator=None, mime_type=None,
                                        ignore_uncap=False,
                                        # DictDocument specific
                                        ignore_wrappers=True,
                                        complex_as=dict,
                                        ordered=False):

        HierDictDocument.__init__(self, app, validator, mime_type, ignore_uncap,
                                           ignore_wrappers, complex_as, ordered)

        self._from_string_handlers[Double] = lambda cls, val: val
        self._from_string_handlers[Boolean] = lambda cls, val: val
        self._from_string_handlers[Decimal] = lambda cls, val: val
        self._from_string_handlers[Integer] = lambda cls, val: val

        self._to_string_handlers[Double] = lambda cls, val: val
        self._to_string_handlers[Boolean] = lambda cls, val: val
        self._to_string_handlers[Decimal] = lambda cls, val: val
        self._to_string_handlers[Integer] = lambda cls, val: val


def get_dict_as_object(d, cls, ignore_wrappers=True, complex_as=list):
    return _UtilProtocol(ignore_wrappers=ignore_wrappers,
                                   complex_as=complex_as)._doc_to_object(cls, d)


def get_object_as_dict(o, cls, ignore_wrappers=True, complex_as=dict):
    return _UtilProtocol(ignore_wrappers=ignore_wrappers,
                                   complex_as=complex_as)._object_to_doc(cls, o)


def get_object_as_json(o, cls, ignore_wrappers=True, complex_as=list):
    d = get_object_as_dict(o, cls, ignore_wrappers, complex_as)
    return json.dumps(d)
