
#
# soaplib - Copyright (C) Soaplib contributors.
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

from lxml import etree

from soaplib.core.model.binary import Attachment
from soaplib.core.model.clazz import Array
from soaplib.core.model.clazz import ClassModel
from soaplib.core.model.enum import Enum
from soaplib.core.model.exception import Fault

from soaplib.core.model.primitive import Any
from soaplib.core.model.primitive import AnyAsDict
from soaplib.core.model.primitive import Boolean
from soaplib.core.model.primitive import DateTime
from soaplib.core.model.primitive import Float
from soaplib.core.model.primitive import Integer
from soaplib.core.model.primitive import String
from soaplib.core.model.primitive import Double

from soaplib.core import service
from soaplib.core import ValidatingApplication
from soaplib.core.service import soap

from datetime import datetime

import logging
logger = logging.getLogger(__name__)

class SimpleClass(ClassModel):
    i = Integer
    s = String

class OtherClass(ClassModel):
    dt = DateTime
    d = Double
    b = Boolean

class NestedClass(ClassModel):
    __namespace__ = "punk.tunk"

    simple = Array(SimpleClass)
    s = String
    i = Integer
    f = Float
    other = OtherClass
    ai = Array(Integer)

class NonNillableClass(ClassModel):
    __namespace__ = "hunk.sunk"

    nillable = False
    min_occurs = 1

    dt = DateTime(min_occurs=1, nillable=False)
    i = Integer(nillable=False)
    s = String(min_len=1, nillable=False)

class ExtensionClass(NestedClass):
    __namespace__ = "bar"

    p = NonNillableClass
    l = DateTime
    q = Integer

DaysOfWeekEnum = Enum(
    'Monday',
    'Tuesday',
    'Wednesday',
    'Friday',
    'Saturday',
    'Sunday',
    type_name = 'DaysOfWeekEnum'
)

class InHeader(ClassModel):
    s=String
    i=Integer

class OutHeader(ClassModel):
    dt=DateTime
    f=Float

class InteropServiceWithHeader(service.DefinitionBase):
    __in_header__ = InHeader
    __out_header__ = OutHeader

    @soap(_returns=InHeader)
    def echo_in_header(self):
        return self.in_header

    @soap(_returns=OutHeader)
    def send_out_header(self):
        self.out_header = OutHeader()
        self.out_header.dt = datetime(year=2000, month=01, day=01)
        self.out_header.f = 3.141592653

        return self.out_header

class InteropPrimitive(service.DefinitionBase):
    @soap(Any, _returns=Any)
    def echo_any(self, xml):
        return xml

    @soap(AnyAsDict, _returns=AnyAsDict)
    def echo_any_as_dict(self, xml_as_dict):
        return xml_as_dict

    @soap(Integer, _returns=Integer)
    def echo_integer(self, i):
        return i

    @soap(String, _returns=String)
    def echo_string(self, s):
        return s

    @soap(DateTime, _returns=DateTime)
    def echo_datetime(self, dt):
        return dt

    @soap(Float, _returns=Float)
    def echo_float(self, f):
        return f

    @soap(Double, _returns=Double)
    def echo_double(self, f):
        return f

    @soap(Boolean, _returns=Boolean)
    def echo_boolean(self, b):
        return b

    @soap(DaysOfWeekEnum, _returns=DaysOfWeekEnum)
    def echo_enum(self, day):
        return day

class InteropArray(service.DefinitionBase):
    @soap(Array(Integer), _returns=Array(Integer))
    def echo_integer_array(self, ia):
        return ia

    @soap(Array(String), _returns=Array(String))
    def echo_string_array(self, sa):
        return sa

    @soap(Array(DateTime), _returns=Array(DateTime))
    def echo_date_time_array(self, dta):
        return dta

    @soap(Array(Float), _returns=Array(Float))
    def echo_float_array(self, fa):
        return fa

    @soap(Array(Double), _returns=Array(Double))
    def echo_double_array(self, da):
        return da

    @soap(Array(Boolean), _returns=Array(Boolean))
    def echo_boolean_array(self, ba):
        return ba

    @soap(Boolean(max_occurs="unbounded"), _returns=Boolean(max_occurs="unbounded"))
    def echo_simple_boolean_array(self, ba):
        return ba

    @soap(Array(Boolean), _returns=Array(Array(Boolean)))
    def echo_array_in_array(self, baa):
        return baa

class InteropClass(service.DefinitionBase):
    @soap(SimpleClass, _returns=SimpleClass)
    def echo_simple_class(self, sc):
        return sc

    @soap(Array(SimpleClass), _returns=Array(SimpleClass))
    def echo_simple_class_array(self, sca):
        return sca

    @soap(NestedClass, _returns=NestedClass)
    def echo_nested_class(self, nc):
        return nc

    @soap(Array(NestedClass), _returns=Array(NestedClass))
    def echo_nested_class_array(self, nca):
        return nca

    @soap(ExtensionClass, _returns=ExtensionClass)
    def echo_extension_class(self, nc):
        return nc

    @soap(Attachment, _returns=Attachment)
    def echo_attachment(self, a):
        return a

    @soap(Array(Attachment), _returns=Array(Attachment))
    def echo_attachment_array(self, aa):
        return aa

class InteropException(service.DefinitionBase):
    @soap()
    def python_exception(self):
        raise Exception("Possible")

    @soap()
    def soap_exception(self):
        raise Fault("Plausible", "A plausible fault", 'Fault actor',
                                            detail=etree.Element('something'))

class InteropMisc(service.DefinitionBase):
    @soap(
        _returns=[
            Integer,
            String,
            Integer,
            Array(Enum("MEMBER", type_name="RoleEnum"))
        ],
        _out_variable_names=[
            'resultCode',
            'resultDescription',
            'transactionId',
            'roles'
        ]
    )
    def complex_return(self):
        return [1, "Test", 123, ["MEMBER"]]

    @soap()
    def huge_number(_returns=Integer):
        return 2**int(1e5)

    @soap()
    def long_string(_returns=String):
        return len('0123456789abcdef' * 16384)

    @soap()
    def test_empty(self):
        pass

    @soap(String, Integer, DateTime)
    def multi_param(self, s, i, dt):
        pass

    @soap(_returns=String)
    def return_only(self):
        return 'howdy'

    @soap(NonNillableClass, _returns=String)
    def non_nillable(self, n):
        return "OK"

    @soap(String, _returns=String, _public_name="do_something")
    def do_something_else(self, s):
        return s

services = [
    InteropPrimitive,
    InteropArray,
    InteropClass,
    InteropMisc,
    InteropServiceWithHeader,
    InteropException,
]

application = ValidatingApplication(services, tns=__name__)
