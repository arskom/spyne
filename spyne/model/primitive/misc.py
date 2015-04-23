
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

import uuid
from spyne.util import six

from spyne.model._base import SimpleModel
from spyne.model.primitive._base import re_match_with_span
from spyne.model.primitive.string import Unicode, AnyUri


UUID_PATTERN = "%(x)s{8}-%(x)s{4}-%(x)s{4}-%(x)s{4}-%(x)s{12}" % \
                                                            {'x': '[a-fA-F0-9]'}


class ImageUri(AnyUri):
    """A special kind of String that holds the uri of an image."""


def _uuid_validate_string(cls, value):
    return (     SimpleModel.validate_string(cls, value)
        and (value is None or (
            cls.Attributes.min_len <= len(value) <= cls.Attributes.max_len
            and re_match_with_span(cls.Attributes, value)
        )))


def _Tuuid_validate(key):
    from uuid import UUID

    def _uvalid(cls, v):
        try:
            UUID(**{key:v})
        except ValueError:
            return False
        return True
    return _uvalid


_uuid_validate = {
    None: _uuid_validate_string,
    'hex': _Tuuid_validate('hex'),
    'urn': _Tuuid_validate('urn'),
    six.binary_type: _Tuuid_validate('bytes'),
    'bytes': _Tuuid_validate('bytes'),
    'bytes_le': _Tuuid_validate('bytes_le'),
    'fields': _Tuuid_validate('fields'),
    int: _Tuuid_validate('int'),
    'int': _Tuuid_validate('int'),
}


class Uuid(Unicode(pattern=UUID_PATTERN)):
    """Unicode subclass for Universially-Unique Identifiers."""

    __namespace__ = 'http://spyne.io/schema'
    __type_name__ = 'uuid'
    Value = uuid.UUID

    class Attributes(Unicode(pattern=UUID_PATTERN).Attributes):
        serialize_as = None

    @staticmethod
    def validate_string(cls, value):
        return _uuid_validate[cls.Attributes.serialize_as](cls, value)

    @staticmethod
    def validate_native(cls, value):
        return SimpleModel.validate_native(cls, value)
