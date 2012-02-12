
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

__version__ = '2.6.0-beta'

from rpclib._base import TransportContext
from rpclib._base import EventContext
from rpclib._base import MethodContext
from rpclib._base import MethodDescriptor
from rpclib._base import EventManager

import sys

if sys.version > '3':
    def _bytes_join(val, joiner=''):
        return bytes(joiner).join(val)
else:
    def _bytes_join(val, joiner=''):
        return joiner.join(val)
