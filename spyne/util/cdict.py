
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

"""cdict (ClassDict) is a funny kind of dict that tries to return the values for
the base classes of a key when the entry for the key is not found. It is not a
generalized dictionary that can handle any type of key -- it relies on
spyne.model api to look for classes.

>>> from spyne.util.cdict import cdict
>>> class A(object):
...     pass
...
>>> class B(A):
...     pass
...
>>> class C(object):
...     pass
...
>>> class D:
...     pass
...
>>> d=cdict({A: "fun", object: "base"})
>>> print d[A]
fun
>>> print d
{<class '__main__.A'>: 'fun', <type 'object'>: 'base'}
>>> print d[B]
fun
>>> print d
{<class '__main__.A'>: 'fun', <class '__main__.B'>: 'fun', <type 'object'>: 'base'}
>>> print d[C]
base
>>> print d
{<class '__main__.A'>: 'fun', <class '__main__.B'>: 'fun', <class '__main__.C'>: 'base', <type 'object'>: 'base'}
>>> print d[D]
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/home/plq/src/github/plq/spyne/src/spyne/util/cdict.py", line 77, in __getitem__
    raise e
KeyError: <class __main__.D at 0x8d92c0>
>>>
"""

import logging
logger = logging.getLogger(__name__)

class cdict(dict):
    def __getitem__(self, cls):
        try:
            return dict.__getitem__(self, cls)

        except KeyError as e:
            if not hasattr(cls, '__bases__'):
                cls = cls.__class__

            for b in cls.__bases__:
                try:
                    retval = self[b]
                    self[cls] = retval
                    return retval
                except KeyError:
                    pass
            raise e

    def get(self, k, d=None):
        try:
            return self[k]

        except KeyError:
            return d
