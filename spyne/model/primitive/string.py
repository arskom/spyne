
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

import sys
import decimal
import uuid

from spyne.model.primitive import NATIVE_MAP
from spyne.util import six
from spyne.model._base import SimpleModel
from spyne.model.primitive._base import re_match_with_span


UUID_PATTERN = "%(x)s{8}-%(x)s{4}-%(x)s{4}-%(x)s{4}-%(x)s{12}" % \
                                                            {'x': '[a-fA-F0-9]'}

LTREE_PATTERN = u"\w+(\\.\w+)*"

# Actual ltree max size is 65536 but it's advised to keep it under 2048.
LTREE_OPTIMAL_SIZE = 2048


class Unicode(SimpleModel):
    """The type to represent human-readable data. Its native format is `unicode`
    or `str` with given encoding.
    """

    __type_name__ = 'string'
    Value = six.text_type

    class Attributes(SimpleModel.Attributes):
        """Customizable attributes of the :class:`spyne.model.primitive.Unicode`
        type."""

        min_len = 0
        """Minimum length of string. Can be set to any positive integer"""

        max_len = decimal.Decimal('inf')
        """Maximum length of string. Can be set to ``decimal.Decimal('inf')`` to
        accept strings of arbitrary length. You may also need to adjust
        :const:`spyne.server.wsgi.MAX_CONTENT_LENGTH`."""

        pattern = None
        """A regular expression that matches the whole string. See here for more
        info: http://www.regular-expressions.info/xml.html"""

        unicode_pattern = None
        """Same as ``pattern``, but, will be compiled with ``re.UNICODE``.
        See: https://docs.python.org/2/library/re.html#re.UNICODE"""

        encoding = None
        """The encoding of `str` objects this class may have to deal with."""

        unicode_errors = 'strict'
        """The argument to the ``unicode`` builtin; one of 'strict', 'replace'
        or 'ignore'."""

        format = None
        """A regular python string formatting string. See here:
        http://docs.python.org/library/stdtypes.html#string-formatting"""

    def __new__(cls, *args, **kwargs):
        assert len(args) <= 1

        if len(args) == 1:
            kwargs['max_len'] = args[0]

        retval = SimpleModel.__new__(cls,  ** kwargs)

        return retval

    @staticmethod
    def is_default(cls):
        return (    SimpleModel.is_default(cls)
                and cls.Attributes.min_len == Unicode.Attributes.min_len
                and cls.Attributes.max_len == Unicode.Attributes.max_len
                and cls.Attributes.pattern == Unicode.Attributes.pattern
            )

    @staticmethod
    def validate_string(cls, value):
        return (     SimpleModel.validate_string(cls, value)
            and (value is None or (
                cls.Attributes.min_len <= len(value) <= cls.Attributes.max_len
            )))

    @staticmethod
    def validate_native(cls, value):
        return (SimpleModel.validate_native(cls, value)
            and (value is None or (
                re_match_with_span(cls.Attributes, value)
            )))


class String(Unicode):
    pass

if sys.version > '3':
    String = Unicode


class AnyUri(Unicode):
    """A special kind of String type designed to hold an uri."""

    __type_name__ = 'anyURI'

    class Attributes(String.Attributes):
        text = None
        """The text shown in link. This is an object-wide constant."""

    class Value(object):
        """A special object that is just a better way of carrying the
        information carried with a link.

        :param href: The uri string.
        :param text: The text data that goes with the link. This is a
            ``str`` or a ``unicode`` instance.
        :param content: The structured data that goes with the link. This is an
            `lxml.etree.Element` instance.
        """

        def __init__(self, href, text=None, content=None):
            self.href = href
            self.text = text
            self.content = content


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


class Ltree(Unicode(LTREE_OPTIMAL_SIZE, unicode_pattern=LTREE_PATTERN)):
    """A special kind of String type designed to hold the Ltree type from
    Postgresql."""

    __namespace__ = 'http://spyne.io/schema'
    __type_name__ = 'ltreeString'


if six.PY3:
    NATIVE_MAP.update({
        str: Unicode,
    })

else:
    NATIVE_MAP.update({
        str: String,
        unicode: Unicode,
    })
