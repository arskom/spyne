
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

from lxml import etree

from rpclib.model.binary import Attachment
from rpclib.model.clazz import Array
from rpclib.model.clazz import ClassSerializer
from rpclib.model.enum import Enum
from rpclib.model.exception import Fault

from rpclib.model.primitive import Any
from rpclib.model.primitive import AnyAsDict
from rpclib.model.primitive import Boolean
from rpclib.model.primitive import DateTime
from rpclib.model.primitive import Float
from rpclib.model.primitive import Integer
from rpclib.model.primitive import String
from rpclib.model.primitive import Double

from rpclib import service
from rpclib.service import rpc
from rpclib.service import srpc

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
    ai = Array(Integer)

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
    def echo_in_header(ctx):
        return ctx.in_header

    @rpc(_returns=OutHeader)
    def send_out_header(ctx):
        ctx.out_header = OutHeader()
        ctx.out_header.dt = datetime(year=2000, month=01, day=01)
        ctx.out_header.f = 3.141592653

        return ctx.out_header

class InteropPrimitive(service.DefinitionBase):
    @srpc(Any, _returns=Any)
    def echo_any(xml):
        return xml

    @srpc(AnyAsDict, _returns=AnyAsDict)
    def echo_any_as_dict(xml_as_dict):
        return xml_as_dict

    @srpc(Integer, _returns=Integer)
    def echo_integer(i):
        return i

    @srpc(String, _returns=String)
    def echo_string(s):
        return s

    @srpc(DateTime, _returns=DateTime)
    def echo_datetime(dt):
        return dt

    @srpc(Float, _returns=Float)
    def echo_float(f):
        return f

    @srpc(Double, _returns=Double)
    def echo_double(f):
        return f

    @srpc(Boolean, _returns=Boolean)
    def echo_boolean(b):
        return b

    @srpc(DaysOfWeekEnum, _returns=DaysOfWeekEnum)
    def echo_enum(day):
        return day

class InteropArray(service.DefinitionBase):
    @srpc(Array(Integer), _returns=Array(Integer))
    def echo_integer_array(ia):
        return ia

    @srpc(Array(String), _returns=Array(String))
    def echo_string_array(sa):
        return sa

    @srpc(Array(DateTime), _returns=Array(DateTime))
    def echo_date_time_array(dta):
        return dta

    @srpc(Array(Float), _returns=Array(Float))
    def echo_float_array(fa):
        return fa

    @srpc(Array(Double), _returns=Array(Double))
    def echo_double_array(da):
        return da

    @srpc(Array(Boolean), _returns=Array(Boolean))
    def echo_boolean_array(ba):
        return ba

    @srpc(Boolean(max_occurs="unbounded"), _returns=Boolean(max_occurs="unbounded"))
    def echo_simple_boolean_array(ba):
        return ba

    @srpc(Array(Boolean), _returns=Array(Array(Boolean)))
    def echo_array_in_array(baa):
        return baa

class InteropClass(service.DefinitionBase):
    @srpc(SimpleClass, _returns=SimpleClass)
    def echo_simple_class(sc):
        return sc

    @srpc(Array(SimpleClass), _returns=Array(SimpleClass))
    def echo_simple_class_array(sca):
        return sca

    @srpc(NestedClass, _returns=NestedClass)
    def echo_nested_class(nc):
        return nc

    @srpc(Array(NestedClass), _returns=Array(NestedClass))
    def echo_nested_class_array(nca):
        return nca

    @srpc(ExtensionClass, _returns=ExtensionClass)
    def echo_extension_class(nc):
        return nc

    @srpc(Attachment, _returns=Attachment)
    def echo_attachment(a):
        assert isinstance(a,Attachment)
        return a

    @srpc(Array(Attachment), _returns=Array(Attachment))
    def echo_attachment_array(aa):
        return aa

class InteropException(service.DefinitionBase):
    @srpc()
    def python_exception():
        raise Exception("Possible")

    @srpc()
    def soap_exception():
        raise Fault("Plausible", "A plausible fault", 'Fault actor',
                                            detail=etree.Element('something'))

class InteropMisc(service.DefinitionBase):
    @srpc(
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
    def complex_return():
        return [1, "Test", 123, ["MEMBER"]]

    @srpc(_returns=Integer)
    def huge_number():
        return 2**int(1e5)

    @srpc(_returns=String)
    def long_string():
        return len('0123456789abcdef' * 16384)

    @srpc()
    def test_empty():
        pass

    @srpc(String, Integer, DateTime)
    def multi_param(s, i, dt):
        pass

    @srpc(_returns=String)
    def return_only():
        return 'howdy'

    @srpc(NonNillableClass, _returns=String)
    def non_nillable(n):
        return "OK"

    @srpc(String, _returns=String, _public_name="do_something")
    def do_something_else(s):
        return s

    @srpc(Integer, _returns=Array(OtherClass))
    def return_other_class_array(num):
        for i in xrange(num):
            yield OtherClass(dt=datetime(2010,12,06), d=3.0, b=True)

    @srpc(_returns=Attachment)
    def return_binary_data():
        return Attachment(data=''.join([chr(i) for i in xrange(256)]))

services = [
    InteropPrimitive,
    InteropArray,
    InteropClass,
    InteropMisc,
    InteropServiceWithHeader,
    InteropException,
]
