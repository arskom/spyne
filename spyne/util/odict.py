
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
This module contains an ordered dictionary implementation.

We need this in Python 2.7 because collections.OrderedDict does not support
reordering by assignment to keys().

We need this in Python 3.x because keys() returns KeyView which which doesn't
support `__getitem__` -- i.e. getting nth variable from the ordered dict.
"""


class odict(dict):
    """Sort of an ordered dictionary implementation."""

    def __init__(self, data=[]):
        if isinstance(data, self.__class__):
            self.__list = list(data.__list)
            super(odict, self).__init__(data)

        else:
            self.__list = []
            super(odict, self).__init__()
            self.update(data)

    def __getitem__(self, key):
        if isinstance(key, int):
            return super(odict, self).__getitem__(self.__list[key])
        else:
            return super(odict, self).__getitem__(key)

    def __setitem__(self, key, val):
        if isinstance(key, int):
            super(odict, self).__setitem__(self.__list[key], val)

        else:
            if not (key in self):
                self.__list.append(key)
            super(odict, self).__setitem__(key, val)

        assert len(self.__list) == super(odict, self).__len__(), (
            repr(self.__list), super(odict, self).__repr__())

    def __repr__(self):
        return "{%s}" % ','.join(["%r: %r" % (k, v) for k, v in self.items()])

    def __str__(self):
        return repr(self)

    def __len__(self):
        assert len(self.__list) == super(odict, self).__len__()
        return len(self.__list)

    def __iter__(self):
        return iter(self.__list)

    def __delitem__(self, key):
        if not isinstance(key, int):
            key = self.__list.index(key) # ouch.

        super(odict, self).__delitem__(self.__list[key])
        del self.__list[key]

    def __add__(self, other):
        self.update(other)
        return self

    def items(self):
        retval = []
        for k in self.__list:
            retval.append( (k, super(odict, self).__getitem__(k)) )
        return retval

    def iteritems(self):
        for k in self.__list:
            yield k, super(odict, self).__getitem__(k)

    def keys(self):
        return self.__list

    def update(self, data):
        if isinstance(data, (dict, odict)):
            data = data.items()

        for k, v in data:
            self[k] = v

    def values(self):
        retval = []
        for l in self.__list:
            retval.append(super(odict, self).__getitem__(l))
        return retval

    def itervalues(self):
        for l in self.__list:
            yield self[l]

    def get(self, key, default=None):
        if key in self:
            return self[key]
        return default

    def append(self, t):
        k, v = t
        self[k] = v

    def insert(self, index, item):
        k,v = item
        if k in self:
            del self.__list[self.__list.index(k)]
        self.__list.insert(index, k)
        super(odict, self).__setitem__(k, v)
