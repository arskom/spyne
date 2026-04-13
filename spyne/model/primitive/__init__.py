
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

from spyne.model.primitive._base import Any, AnyDict, AnyHtml, AnyXml, Boolean
# Date/Time types
from spyne.model.primitive.datetime import Date, DateTime, Duration, Time
from spyne.model.primitive.network import (
    IpAddress,
    Ipv4Address,
    Ipv6Address,
    MacAddress
)
# Numbers
from spyne.model.primitive.number import \
    NonNegativeInteger  # Xml Schema calls it so
from spyne.model.primitive.number import (
    Byte,
    Decimal,
    Double,
    Float,
    Int,
    Integer,
    Integer8,
    Integer16,
    Integer32,
    Integer64,
    Long,
    NumberLimitsWarning,
    Short,
    UnsignedByte,
    UnsignedInt,
    UnsignedInteger,
    UnsignedInteger8,
    UnsignedInteger16,
    UnsignedInteger32,
    UnsignedInteger64,
    UnsignedLong,
    UnsignedShort
)
from spyne.model.primitive.spatial import (
    Line,
    LineString,
    MultiLine,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon
)
from spyne.model.primitive.string import (
    AnyUri,
    ImageUri,
    Ltree,
    MediaType,
    MediaTypeStrict,
    MimeType,
    MimeTypeStrict,
    String,
    Unicode,
    Uuid
)
from spyne.model.primitive.xml import (
    ID,
    Language,
    Name,
    NCName,
    NMToken,
    NormalizedString,
    QName,
    Token
)


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
