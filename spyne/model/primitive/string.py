
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

from spyne.model._base import SimpleModel
from spyne.model.primitive import NATIVE_MAP
from spyne.model.primitive._base import re_match_with_span
from spyne.util import six


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
        """Same as ``pattern``, but, will be compiled with UNICODE.
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


if six.PY3:
    NATIVE_MAP.update({
        str: Unicode,
    })

else:
    NATIVE_MAP.update({
        str: String,
        unicode: Unicode,
    })
