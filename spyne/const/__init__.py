

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

"""The ``spyne.const`` package contains miscellanous constant values needed
in various parts of Spyne."""


MAX_STRING_FIELD_LENGTH = 64
"""Maximum length of a string field for :func:`spyne.util.log_repr`"""

MAX_ARRAY_ELEMENT_NUM = 2
"""Maximum number of array elements for :func:`spyne.util.log_repr`"""

MAX_DICT_ELEMENT_NUM = 2
"""Maximum number of dict elements for :func:`spyne.util.log_repr`"""

MAX_FIELD_NUM = 10
"""Maximum number of complex model fields for :func:`spyne.util.log_repr`"""

ARRAY_PREFIX = ''
"""The prefix for Array wrapper objects. You may want to set this to 'ArrayOf'
and the ARRAY_SUFFIX to '' for compatibility with some SOAP deployments."""

ARRAY_SUFFIX = 'Array'
"""The suffix for Array wrapper objects."""

REQUEST_SUFFIX = ''
"""The suffix for function response objects."""

RESPONSE_SUFFIX = 'Response'
"""The suffix for function response objects."""

RESULT_SUFFIX = 'Result'
"""The suffix for function response wrapper objects."""

TYPE_SUFFIX = 'Type'
"""The suffix for primitives with unnamed constraints."""

PARENT_SUFFIX = 'Parent'
"""The suffix for parent classes of primitives with unnamed constraints."""

MANDATORY_PREFIX = 'Mandatory'
"""The prefix for types created with the :func:`spyne.model.Mandatory`."""

MANDATORY_SUFFIX = ''
"""The suffix for types created with the :func:`spyne.model.Mandatory`."""

DEFAULT_DECLARE_ORDER = 'random'
"""Order of complex type attrs of :class:`spyne.model.complex.ComplexModel`."""

MIN_GC_INTERVAL = 1.0
"""Minimum time in seconds between gc.collect() calls."""

DEFAULT_LOCALE = 'en_US'
"""Locale code to use for the translation subsystem when locale information is
missing in an incoming request."""

WARN_ON_DUPLICATE_FAULTCODE = True
"""Warn about duplicate faultcodes in all Fault subclasses globally. Only works
when CODE class attribute is set for every Fault subclass."""


def add_request_suffix(string):
    """Concatenates REQUEST_SUFFIX to end of string"""
    return string + REQUEST_SUFFIX
