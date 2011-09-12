
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

"""cdict (ClassDict) is a funny kind of dict that tries to return the values for
the base classes of a key when the entry for the key is not found. It is not a
generalized dictionary that can handle any type of key -- it relies on
rpclib.model api to look for classes.
"""

import logging
logger = logging.getLogger(__name__)

class cdict(dict):
    def __getitem__(self, cls):
        try:
            return dict.__getitem__(self, cls)

        except KeyError, e:
            try:
                return dict.__getitem__(self, cls._is_clone_of)
            except AttributeError:
                pass
            except KeyError:
                pass

            for b in cls.__bases__:
                try:
                    return self[b]
                except KeyError:
                    pass
            raise
