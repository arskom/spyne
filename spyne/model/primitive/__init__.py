
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

NATIVE_MAP = {}
string_encoding = 'UTF-8'  # ???

from spyne.model.primitive._base import Any
from spyne.model.primitive._base import AnyDict
from spyne.model.primitive._base import AnyHtml
from spyne.model.primitive._base import AnyXml
from spyne.model.primitive._base import Boolean

from spyne.model.primitive.string import Unicode
from spyne.model.primitive.string import String
from spyne.model.primitive.string import AnyUri
from spyne.model.primitive.string import Uuid
from spyne.model.primitive.string import ImageUri
from spyne.model.primitive.string import Ltree

from spyne.model.primitive.xml import ID
from spyne.model.primitive.xml import Token
from spyne.model.primitive.xml import NMToken
from spyne.model.primitive.xml import Name
from spyne.model.primitive.xml import NCName
from spyne.model.primitive.xml import Language
from spyne.model.primitive.xml import NormalizedString

from spyne.model.primitive.spatial import Point
from spyne.model.primitive.spatial import Line
from spyne.model.primitive.spatial import LineString
from spyne.model.primitive.spatial import Polygon
from spyne.model.primitive.spatial import MultiPoint
from spyne.model.primitive.spatial import MultiLine
from spyne.model.primitive.spatial import MultiLineString
from spyne.model.primitive.spatial import MultiPolygon

# Date/Time types
from spyne.model.primitive.datetime import Date
from spyne.model.primitive.datetime import DateTime
from spyne.model.primitive.datetime import Duration
from spyne.model.primitive.datetime import Time

# Numbers
from spyne.model.primitive.number import Decimal
from spyne.model.primitive.number import Double
from spyne.model.primitive.number import Float

from spyne.model.primitive.number import Integer8
from spyne.model.primitive.number import Byte
from spyne.model.primitive.number import Integer16
from spyne.model.primitive.number import Short
from spyne.model.primitive.number import Integer32
from spyne.model.primitive.number import Int
from spyne.model.primitive.number import Integer64
from spyne.model.primitive.number import Long
from spyne.model.primitive.number import Integer

from spyne.model.primitive.number import UnsignedInteger8
from spyne.model.primitive.number import UnsignedByte
from spyne.model.primitive.number import UnsignedInteger16
from spyne.model.primitive.number import UnsignedShort
from spyne.model.primitive.number import UnsignedInteger32
from spyne.model.primitive.number import UnsignedInt
from spyne.model.primitive.number import UnsignedInteger64
from spyne.model.primitive.number import UnsignedLong
from spyne.model.primitive.number import NonNegativeInteger # Xml Schema calls it so
from spyne.model.primitive.number import PositiveInteger
from spyne.model.primitive.number import UnsignedInteger

from spyne.model.primitive.network import MacAddress
from spyne.model.primitive.network import IpAddress
from spyne.model.primitive.network import Ipv4Address
from spyne.model.primitive.network import Ipv6Address


# This class is DEPRECATED. Use the spyne.model.Mandatory like this:
# >>> from spyne.model import Mandatory as M, Unicode
# >>> MandatoryEmail = M(Unicode(pattern='[^@]+@[^@]+'))
class Mandatory:
    Unicode = Unicode(type_name="MandatoryString", min_occurs=1, nillable=False, min_len=1)
    String = String(type_name="MandatoryString", min_occurs=1, nillable=False, min_len=1)

    AnyXml = AnyXml(type_name="MandatoryXml", min_occurs=1, nillable=False)
    AnyDict = AnyDict(type_name="MandatoryDict", min_occurs=1, nillable=False)
    AnyUri = AnyUri(type_name="MandatoryUri", min_occurs=1, nillable=False, min_len=1)
    ImageUri = ImageUri(type_name="MandatoryImageUri", min_occurs=1, nillable=False, min_len=1)

    Boolean = Boolean(type_name="MandatoryBoolean", min_occurs=1, nillable=False)

    Date = Date(type_name="MandatoryDate", min_occurs=1, nillable=False)
    Time = Time(type_name="MandatoryTime", min_occurs=1, nillable=False)
    DateTime = DateTime(type_name="MandatoryDateTime", min_occurs=1, nillable=False)
    Duration = Duration(type_name="MandatoryDuration", min_occurs=1, nillable=False)

    Decimal = Decimal(type_name="MandatoryDecimal", min_occurs=1, nillable=False)
    Double = Double(type_name="MandatoryDouble", min_occurs=1, nillable=False)
    Float = Float(type_name="MandatoryFloat", min_occurs=1, nillable=False)

    Integer = Integer(type_name="MandatoryInteger", min_occurs=1, nillable=False)
    Integer64 = Integer64(type_name="MandatoryLong", min_occurs=1, nillable=False)
    Integer32 = Integer32(type_name="MandatoryInt", min_occurs=1, nillable=False)
    Integer16 = Integer16(type_name="MandatoryShort", min_occurs=1, nillable=False)
    Integer8 = Integer8(type_name="MandatoryByte", min_occurs=1, nillable=False)

    Long = Integer64
    Int = Integer32
    Short = Integer16
    Byte = Integer8

    UnsignedInteger = UnsignedInteger(type_name="MandatoryUnsignedInteger", min_occurs=1, nillable=False)
    UnsignedInteger64 = UnsignedInteger64(type_name="MandatoryUnsignedLong", min_occurs=1, nillable=False)
    UnsignedInteger32 = UnsignedInteger32(type_name="MandatoryUnsignedInt", min_occurs=1, nillable=False)
    UnsignedInteger16 = UnsignedInteger16(type_name="MandatoryUnsignedShort", min_occurs=1, nillable=False)
    UnsignedInteger8 = UnsignedInteger8(type_name="MandatoryUnsignedByte", min_occurs=1, nillable=False)

    UnsignedLong = UnsignedInteger64
    UnsignedInt = UnsignedInteger32
    UnsignedShort = UnsignedInteger16
    UnsignedByte = UnsignedInteger8

    Uuid = Uuid(type_name="MandatoryUuid", min_len=1, min_occurs=1, nillable=False)

    Point = Point(type_name="Point", min_len=1, min_occurs=1, nillable=False)
    Line = Line(type_name="LineString", min_len=1, min_occurs=1, nillable=False)
    LineString = Line
    Polygon = Polygon(type_name="Polygon", min_len=1, min_occurs=1, nillable=False)

    MultiPoint = MultiPoint(type_name="MandatoryMultiPoint", min_len=1, min_occurs=1, nillable=False)
    MultiLine = MultiLine(type_name="MandatoryMultiLineString", min_len=1, min_occurs=1, nillable=False)
    MultiLineString = MultiLine
    MultiPolygon = MultiPolygon(type_name="MandatoryMultiPolygon", min_len=1, min_occurs=1, nillable=False)


assert Mandatory.Long == Mandatory.Integer64
