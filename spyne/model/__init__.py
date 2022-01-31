
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

"""The ``spyne.model`` package contains data types that Spyne is able to
distinguish. These are just type markers, they are not of much use without
protocols.
"""

from spyne.model._base import Ignored
from spyne.model._base import ModelBase
from spyne.model._base import PushBase
from spyne.model._base import Null
from spyne.model._base import SimpleModel

# Primitives
from spyne.model.primitive import *

# store_as values
# it's sad that xml the pssm and xml the module conflict. that's why we need
# this after import of primitive package
from spyne.model._base import xml
from spyne.model._base import json
from spyne.model._base import jsonb
from spyne.model._base import table
from spyne.model._base import msgpack

# Classes
from spyne.model.complex import ComplexModelMeta
from spyne.model.complex import ComplexModelBase
from spyne.model.complex import ComplexModel
from spyne.model.complex import TTableModelBase
from spyne.model.complex import TTableModel

# Iterables
from spyne.model.complex import Array
from spyne.model.complex import Iterable
from spyne.model.complex import PushBase

# Modifiers
from spyne.model.complex import Mandatory
from spyne.model.complex import XmlAttribute
from spyne.model.complex import XmlData

# Markers
from spyne.model.complex import SelfReference

# Binary
from spyne.model.binary import File
from spyne.model.binary import ByteArray

# Enum
from spyne.model.enum import Enum

# Fault
from spyne.model.fault import Fault
