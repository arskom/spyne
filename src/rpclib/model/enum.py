
#
# rpclib - Copyright (C) Rpclib contributors.
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

"""This module contains Enum object and its helper objects."""

from rpclib.model import SimpleModel

# adapted from: http://code.activestate.com/recipes/413486/

class EnumBase(SimpleModel):
    __namespace__ = None

    @staticmethod
    def resolve_namespace(cls, default_ns):
        if cls.__namespace__ is None:
            cls.__namespace__ = default_ns

    @staticmethod
    def validate_string(cls, value):
        return (    SimpleModel.validate_string(cls, value)
                and value in cls.__values__
            )

def Enum(*values, **kwargs):
    type_name = kwargs.get('type_name', None)
    docstr = kwargs.get('__doc__', '')
    if type_name is None:
        raise Exception("Please specify 'type_name' as a keyword argument")

    assert len(values) > 0, "Empty enums are meaningless"

    maximum = len(values) # to make __invert__ work

    class EnumValue(object):
        __slots__ = ('__value')

        def __init__(self, value):
            self.__value = value

        def __hash__(self):
            return hash(self.__value)

        def __cmp__(self, other):
            assert isinstance(self, type(other)), \
                             "Only values from the same enum are comparable"

            return cmp(self.__value, other.__value)

        def __invert__(self):
            return values[maximum - self.__value]

        def __nonzero__(self):
            return bool(self.__value)

        def __bool__(self):
            return bool(self.__value)

        def __repr__(self):
            return str(values[self.__value])

    class EnumType(EnumBase):
        __doc__ = docstr
        __type_name__ = type_name
        __values__ = values

        def __iter__(self):
            return iter(values)

        def __len__(self):
            return len(values)

        def __getitem__(self, i):
            return values[i]

        def __repr__(self):
            return 'Enum' + str(enumerate(values))

        def __str__(self):
            return 'enum ' + str(values)

    for i, v in enumerate(values):
        setattr(EnumType, v, EnumValue(i))

    return EnumType
