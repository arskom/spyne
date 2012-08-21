
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

"""The ``spyne.model`` package contains data types that spyne is able to
distinguish. These are mere type markers, they are not of much use without
protocols.
"""

from spyne.model._base import ModelBase
from spyne.model._base import Null
from spyne.model._base import SimpleModel

from spyne.model._base import nillable_dict
from spyne.model._base import nillable_string
from spyne.model._base import nillable_iterable
