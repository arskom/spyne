
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

# adapted from: https://gist.github.com/KrzysztofCiba/4579691

##
# @file TypedList.py
# @author Krzysztof.Ciba@NOSPAMgmail.com
# @date 2012/07/19 08:21:22
# @brief Definition of TypedList class.


class tlist(list):
    """
    .. class:: tlist

    A list-like class holding only objects of specified type(s).
    """

    def __init__(self, iterable=None, types=None):
        iterable = list() if not iterable else iterable

        # make sure it is iterable
        iter(iterable)

        types = types if isinstance(types, tuple) else (types,)
        for item in types:
            if not isinstance(item, type):
                raise TypeError("%s is not a type" % repr(item))

        self._types = types
        for i in iterable:
            self._type_check(i)
        list.__init__(self, iterable)

    def types(self):
        return self._types

    def _type_check(self, val):
        if not self._types:
            return

        if not isinstance(val, self._types):
            raise TypeError(
                "Wrong type %s, this list can hold only instances of %s"
                                                % (type(val), str(self._types)))

    def __iadd__(self, other):
        map(self._type_check, other)
        list.__iadd__(self, other)
        return self

    def __add__(self, other):
        iterable = [item for item in self] + [item for item in other]
        return tlist(iterable, self._types)

    def __radd__(self, other):
        iterable = [item for item in other] + [item for item in self]
        if isinstance(other, tlist):
            return self.__class__(iterable, other.types())
        return tlist(iterable, self._types)

    def __setitem__(self, key, value):
        itervalue = (value,)
        if isinstance(key, slice):
            iter(value)
            itervalue = value
        map(self._type_check, itervalue)
        list.__setitem__(self, key, value)

    def __setslice__(self, i, j, iterable):
        iter(iterable)
        map(self._type_check, iterable)
        list.__setslice__(self, i, j, iterable)

    def append(self, val):
        self._type_check(val)
        list.append(self, val)

    def extend(self, iterable):
        iter(iterable)
        map(self._type_check, iterable)
        list.extend(self, iterable)

    def insert(self, i, val):
        self._type_check(val)
        list.insert(self, i, val)
