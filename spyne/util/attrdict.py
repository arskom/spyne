
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


def TAttrDict(default=None):
    class AttrDict(object):
        def __init__(self, *args, **kwargs):
            self.__data = dict(*args, **kwargs)

        def __call__(self, **kwargs):
            retval = AttrDict(self.__data.items())
            for k,v in kwargs.items():
                setattr(retval, k, v)
            return retval

        def __setattr__(self, key, value):
            if key == "_AttrDict__data":
                return object.__setattr__(self, key, value)
            if key == 'items':
                raise ValueError("'items' is part of dict interface")
            self.__data[key] = value

        def __setitem__(self, key, value):
            self.__data[key] = value

        def __iter__(self):
            return iter(self.__data)

        def items(self):
            return self.__data.items()

        def get(self, key, *args):
            return self.__data.get(key, *args)

        def update(self, d):
            return self.__data.update(d)

        def __repr__(self):
            return "AttrDict(%s)" % ', '.join(['%s=%r' % (k, v)
                    for k,v in sorted(self.__data.items(), key=lambda x:x[0])])

        if default is None:
            def __getattr__(self, key):
                return self.__data[key]
            def __getitem__(self, key):
                return self.__data[key]
        else:
            def __getitem__(self, key):
                if key in self.__data:
                    return self.__data[key]
                else:
                    return default()
            def __getattr__(self, key):
                if key in ("_AttrDict__data", 'items', 'get', 'update'):
                    return object.__getattribute__(self, '__data')
                if key in self.__data:
                    return self.__data[key]
                else:
                    return default()

    return AttrDict

AttrDict = TAttrDict()
DefaultAttrDict = TAttrDict(lambda: None)


class AttrDictColl(object):
    AttrDictImpl = DefaultAttrDict
    def __init__(self, *args):
        for a in args:
            setattr(self, a, AttrDictColl.AttrDictImpl(NAME=a))
