
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
from spyne.model._base import PushBase
from spyne.model._base import Null
from spyne.model._base import SimpleModel

# store_as values
from spyne.model._base import xml
from spyne.model._base import json
from spyne.model._base import table
from spyne.model._base import msgpack

# Boolean
from spyne.model.primitive import Boolean

# Any* types
from spyne.model.primitive import AnyXml
from spyne.model.primitive import AnyDict
from spyne.model.primitive import AnyHtml

# Unicode children
from spyne.model.primitive import Unicode
from spyne.model.primitive import String
from spyne.model.primitive import AnyUri
from spyne.model.primitive import ImageUri
from spyne.model.primitive import Uuid
from spyne.model.primitive import NormalizedString
from spyne.model.primitive import Token
from spyne.model.primitive import Name
from spyne.model.primitive import NCName
from spyne.model.primitive import ID
from spyne.model.primitive import Language


from spyne.model.primitive import ID

from spyne.model.primitive import Point
from spyne.model.primitive import Line
from spyne.model.primitive import LineString
from spyne.model.primitive import Polygon
from spyne.model.primitive import MultiPoint
from spyne.model.primitive import MultiLine
from spyne.model.primitive import MultiLineString
from spyne.model.primitive import MultiPolygon

# Date/Time types
from spyne.model.primitive import Date
from spyne.model.primitive import DateTime
from spyne.model.primitive import Duration
from spyne.model.primitive import Time

# Numbers
from spyne.model.primitive import Decimal

from spyne.model.primitive import Double
from spyne.model.primitive import Float

from spyne.model.primitive import Integer8
from spyne.model.primitive import Byte
from spyne.model.primitive import Integer16
from spyne.model.primitive import Short
from spyne.model.primitive import Integer32
from spyne.model.primitive import Int
from spyne.model.primitive import Integer64
from spyne.model.primitive import Long
from spyne.model.primitive import Integer

from spyne.model.primitive import UnsignedInteger8
from spyne.model.primitive import UnsignedByte
from spyne.model.primitive import UnsignedInteger16
from spyne.model.primitive import UnsignedShort
from spyne.model.primitive import UnsignedInteger32
from spyne.model.primitive import UnsignedInt
from spyne.model.primitive import UnsignedInteger64
from spyne.model.primitive import UnsignedLong
from spyne.model.primitive import NonNegativeInteger # Xml Schema calls it so
from spyne.model.primitive import UnsignedInteger

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
