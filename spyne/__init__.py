
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

__version__ = '2.9.4'

from spyne._base import AuxMethodContext
from spyne._base import TransportContext
from spyne._base import EventContext
from spyne._base import MethodContext
from spyne._base import MethodDescriptor
from spyne._base import EventManager

import sys

if not hasattr(sys, "version_info") or sys.version_info < (2, 5):
    raise RuntimeError("Spyne requires Python 2.5 or later.")

del sys
