
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

from soaplib.serializers.binary import Attachment
from soaplib.serializers.clazz import Array
from soaplib.serializers.clazz import ClassSerializer
from soaplib.serializers.enum import Enum

from soaplib.serializers.primitive import Any
from soaplib.serializers.primitive import AnyAsDict
from soaplib.serializers.primitive import Boolean
from soaplib.serializers.primitive import DateTime
from soaplib.serializers.primitive import Float
from soaplib.serializers.primitive import Integer
from soaplib.serializers.primitive import String
from soaplib.serializers.primitive import Double

from soaplib import service
from soaplib.service import rpc
from soaplib.wsgi import ValidatingApplication

from datetime import datetime

import logging
logger = logging.getLogger(__name__)

class SimpleClass(ClassSerializer):
    i = Integer
    s = String

class OtherClass(ClassSerializer):
    dt = DateTime
    d = Double
    b = Boolean

class NestedClass(ClassSerializer):
    __namespace__ = "punk.tunk"

    simple = Array(SimpleClass)
    s = String
    i = Integer
    f = Float
    other = OtherClass

class NonNillableClass(ClassSerializer):
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

class InHeader(ClassSerializer):
    s=String
    i=Integer

class OutHeader(ClassSerializer):
    dt=DateTime
    f=Float

class InteropServiceWithHeader(service.DefinitionBase):
    __in_header__ = InHeader
    __out_header__ = OutHeader

    @rpc(_returns=InHeader)
    def echo_in_header(self):
        return self.soap_in_header

    @rpc(_returns=OutHeader)
    def send_out_header(self):
        self.soap_out_header = OutHeader()
        self.soap_out_header.dt = datetime(year=2000, month=01, day=01)
        self.soap_out_header.f = 3.141592653

        return self.soap_out_header

class InteropPrimitive(service.DefinitionBase):
    @rpc(Any, _returns=Any)
    def echo_any(self, xml):
        return xml

    @rpc(AnyAsDict, _returns=AnyAsDict)
    def echo_any_as_dict(self, xml_as_dict):
        return xml_as_dict

    @rpc(Integer, _returns=Integer)
    def echo_integer(self, i):
        return i

    @rpc(String, _returns=String)
    def echo_string(self, s):
        return s

    @rpc(DateTime, _returns=DateTime)
    def echo_datetime(self, dt):
        return dt

    @rpc(Float, _returns=Float)
    def echo_float(self, f):
        return f

    @rpc(Double, _returns=Double)
    def echo_double(self, f):
        return f

    @rpc(Boolean, _returns=Boolean)
    def echo_boolean(self, b):
        return b

    @rpc(DaysOfWeekEnum, _returns=DaysOfWeekEnum)
    def echo_enum(self, day):
        return day

class InteropArray(service.DefinitionBase):
    @rpc(Array(Integer), _returns=Array(Integer))
    def echo_integer_array(self, ia):
        return ia

    @rpc(Array(String), _returns=Array(String))
    def echo_string_array(self, sa):
        return sa

    @rpc(Array(DateTime), _returns=Array(DateTime))
    def echo_date_time_array(self, dta):
        return dta

    @rpc(Array(Float), _returns=Array(Float))
    def echo_float_array(self, fa):
        return fa

    @rpc(Array(Double), _returns=Array(Double))
    def echo_double_array(self, da):
        return da

    @rpc(Array(Boolean), _returns=Array(Boolean))
    def echo_boolean_array(self, ba):
        return ba

    @rpc(Boolean(max_occurs="unbounded"), _returns=Boolean(max_occurs="unbounded"))
    def echo_simple_boolean_array(self, ba):
        return ba

    @rpc(Array(Boolean), _returns=Array(Array(Boolean)))
    def echo_array_in_array(self, baa):
        return baa

class InteropClass(service.DefinitionBase):
    @rpc(SimpleClass, _returns=SimpleClass)
    def echo_simple_class(self, sc):
        return sc

    @rpc(Array(SimpleClass), _returns=Array(SimpleClass))
    def echo_simple_class_array(self, sca):
        return sca

    @rpc(NestedClass, _returns=NestedClass)
    def echo_nested_class(self, nc):
        return nc

    @rpc(Array(NestedClass), _returns=Array(NestedClass))
    def echo_nested_class_array(self, nca):
        return nca

    @rpc(ExtensionClass, _returns=ExtensionClass)
    def echo_extension_class(self, nc):
        return nc

    @rpc(Attachment, _returns=Attachment)
    def echo_attachment(self, a):
        return a

    @rpc(Array(Attachment), _returns=Array(Attachment))
    def echo_attachment_array(self, aa):
        return aa

class InteropMisc(service.DefinitionBase):
    @rpc()
    def huge_number(_returns=Integer):
        return 2**int(1e5)

    @rpc()
    def long_string(_returns=String):
        return len('0123456789abcdef' * 16384)

    @rpc()
    def test_empty(self):
        pass

    @rpc(String, Integer, DateTime)
    def multi_param(self, s, i, dt):
        pass

    @rpc(_returns=String)
    def return_only(self):
        return 'howdy'

    @rpc(NonNillableClass, _returns=String)
    def non_nillable(self, n):
        return "OK"

    @rpc(String, _returns=String, _public_name="do_something")
    def do_something_else(self, s):
        return s

services = [
    InteropPrimitive,
    InteropArray,
    InteropClass,
    InteropMisc,
    InteropServiceWithHeader,
]

application = ValidatingApplication(services, tns=__name__)
