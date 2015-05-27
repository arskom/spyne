
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


"""
The ``spyne.model.primitive`` package contains types with values that fit
in a single field.

See :mod:`spyne.protocol._model` for {to,from}_string implementations.
"""


from __future__ import absolute_import

from spyne.model import SimpleModel
from spyne.model.primitive import NATIVE_MAP
from spyne.model._base import apply_pssm, msgpack, xml, json


def re_match_with_span(attr, value):
    if attr.pattern is None:
        return True

    m = attr._pattern_re.match(value)
    return (m is not None) and (m.span() == (0, len(value)))


class AnyXml(SimpleModel):
    """An xml node that can contain any number of sub nodes. It's represented by
    an ElementTree object."""

    __type_name__ = 'anyType'

    class Attributes(SimpleModel.Attributes):
        namespace = None
        """Xml-Schema specific namespace attribute"""

        process_contents = None
        """Xml-Schema specific processContents attribute"""


# EXPERIMENTAL
class Any(SimpleModel):
    pass


# EXPERIMENTAL
class AnyHtml(SimpleModel):
    __type_name__ = 'string'


class AnyDict(SimpleModel):
    """A dict instance that can contain other dicts, iterables or primitive
    types. Its serialization is protocol-dependent.
    """

    __type_name__ = 'anyType'
    Value = dict

    class Attributes(SimpleModel.Attributes):
        store_as = None
        """Method for serializing to persistent storage. One of 'xml', 'json' or
        'msgpack'. It makes sense to specify this only when this object is
        child of a `ComplexModel` sublass."""

    @classmethod
    def customize(cls, **kwargs):
        """Duplicates cls and overwrites the values in ``cls.Attributes`` with
        ``**kwargs`` and returns the new class."""

        store_as = apply_pssm(kwargs.get('store_as', None),
                                {'json': json, 'xml': xml, 'msgpack': msgpack})
        if store_as is not None:
            kwargs['store_as'] = store_as

        return super(AnyDict, cls).customize(**kwargs)


class Boolean(SimpleModel):
    """Life is simple here. Just true or false."""

    __type_name__ = 'boolean'


NATIVE_MAP.update({
    bool: Boolean,
})
