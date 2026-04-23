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
# fmt: off
# isort: skip_file

"""The ``spyne.model`` package contains data types that Spyne is able to
distinguish. These are just type markers, they are not of much use without
protocols.
"""

from spyne.model._base import (
    Ignored,
    ModelBase,
    Null,
    PushBase,
    SimpleModel,
)

# Primitives
from spyne.model.primitive import *

# store_as values
# it's sad that xml the pssm and xml the module conflict. that's why we need
# this after import of primitive package
from spyne.model._base import json, jsonb, msgpack, table, xml

# Classes
from spyne.model.complex import (
    Array,
    ComplexModel,
    ComplexModelBase,
    ComplexModelMeta,
    Iterable,
    Mandatory,
    PushBase,
    SelfReference,
    TTableModel,
    TTableModelBase,
    XmlAttribute,
    XmlData,
)

# Enum
from spyne.model.enum import Enum

# Fault
from spyne.model.fault import Fault, ValidationError

# Binary (must come last — depends on primitive, complex and fault being initialized)
from spyne.model.binary import ByteArray, File
