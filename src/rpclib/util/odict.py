
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

"""This module contains a sort of an ordered dictionary implementation."""

class odict(object):
    """Sort of an ordered dictionary implementation."""

    class Empty(object):
        pass

    def __init__(self, data=[]):
        if isinstance(data, self.__class__):
            self.__list = list(data.__list)
            self.__dict = dict(data.__dict)

        else:
            self.__list = []
            self.__dict = {}

            self.update(data)

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.__dict[self.__list[key]]
        else:
            return self.__dict[key]

    def __setitem__(self, key, val):
        if isinstance(key, int):
            self.__dict[self.__list[key]] = val

        else:
            if not (key in self.__dict):
                self.__list.append(key)
            self.__dict[key] = val

        assert len(self.__list) == len(self.__dict), (repr(self.__list),
                                                              repr(self.__dict))

    def __contains__(self, what):
        return (what in self.__dict)

    def __repr__(self):
        return "{%s}" % ','.join(["%r: %r" % (k, v) for k, v in self.items()])

    def __str__(self):
        return repr(self)

    def __len__(self):
        assert len(self.__list) == len(self.__dict)

        return len(self.__list)

    def __iter__(self):
        return iter(self.__list)

    def __delitem__(self, key):
        if not isinstance(key, int):
            key = self.__list.index(key) # ouch.

        del self.__dict[self.__list[key]]
        del self.__list[key]

    def items(self):
        retval = []
        for k in self.__list:
            retval.append( (k, self.__dict[k]) )
        return retval

    def iteritems(self):
        for k in self.__list:
            yield k, self.__dict[k]

    def keys(self):
        return self.__list

    def update(self, data):
        if isinstance(data, dict):
            data = data.items()

        for k, v in data:
            self[k] = v

    def values(self):
        retval = []
        for l in self.__list:
            retval.append( self.__dict[l] )
        return retval

    def itervalues(self):
        for l in self.__list:
            yield self.__dict[l]

    def get(self, key, default=Empty):
        if key in self.__dict:
            return self[key]

        else:
            if default is odict.Empty:
                raise KeyError(key)
            else:
                return default

    def append(self, t):
        k, v = t
        self[k] = v
