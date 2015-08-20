
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

"""The typed dict module"""


from itertools import chain


class tdict(dict):
    def __init__(self, kt=None, vt=None, data=None):
        """This is a typed dict implementation that optionally enforces given
        types on contained values on assignment."""

        self._kt = kt
        self._vt = vt

        if kt is None and vt is None:
            self.check = self._check_noop
        elif kt is None:
            self.check = self._check_v
        elif vt is None:
            self.check = self._check_k
        else:
            self.check = self._check_kv

        if data is not None:
            self.update(data)

    def _check_noop(self, *_):
        pass

    def _check_k(self, key, _):
        if not isinstance(key, self._kt):
            raise TypeError(repr(key))

    def _check_v(self, _, value):
        if not isinstance(value, self._vt):
            raise TypeError(repr(value))

    def _check_kv(self, key, value):
        if not isinstance(key, self._kt):
            raise TypeError(repr(key))
        if not isinstance(value, self._vt):
            raise TypeError(repr(value))

    def __setitem__(self, key, value):
        self.check(key, value)
        super(tdict, self).__setitem__(key, value)

    def update(self, E=None, **F):
        try:
            it = chain(E.items(), F.items())
        except AttributeError:
            it = chain(E, F)

        for k, v in it:
            self[k] = v

    def setdefault(self, k, d=None):
        self._check_k(k, d) if self._kt is None else None
        self._check_v(k, d) if self._vt is None else None

        super(tdict, self).setdefault(k, d)

    @classmethod
    def fromkeys(cls, S, v=None):
        kt = vt = None

        if len(S) > 0:
            kt, = set((type(s) for s in S))

        if v is not None:
            vt = type(v)

        retval = tdict(kt, vt)

        for s in S:
            retval[s] = v

        return retval

    def repr(self):
        return "tdict(kt=%s, vt=%s, data=%s)" % \
                             (self._kt, self._vt, super(tdict, self).__repr__())
