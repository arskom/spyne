
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

"""The ```spyne.const.suffix``` module contains  various suffixes that Spyne
uses when automatically generating complex types."""

ARRAY_SUFFIX = 'Array'
"""The suffix for Array wrapper objects"""

RESPONSE_SUFFIX = 'Response'
"""The suffix for function response objects"""

RESULT_SUFFIX = 'Result'
"""The suffix for function response wrapper objects"""

TYPE_SUFFIX = 'Type'
"""The suffix for primitives with unnamed constraints."""


def set_array_suffix(what):
    """Sets the array suffix to its argument."""

    global ARRAY_SUFFIX
    ARRAY_SUFFIX = what


def set_response_suffix(what):
    """Sets the response suffix to its argument."""

    global RESPONSE_SUFFIX
    RESPONSE_SUFFIX = what


def set_result_suffix(what):
    """Sets the result suffix to its argument."""

    global RESULT_SUFFIX
    RESULT_SUFFIX = what


def set_type_suffix(what):
    """Sets the type suffix to its argument."""

    global TYPE_SUFFIX
    TYPE_SUFFIX = what
