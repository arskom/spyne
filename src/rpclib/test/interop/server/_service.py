
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
from rpclib.model.complex import Array
from rpclib.model.complex import ComplexModel
from rpclib.model.complex import SelfReference
from rpclib.model.enum import Enum
from rpclib.model.fault import Fault

from rpclib.model.primitive import AnyXml
from rpclib.model.primitive import AnyDict
from rpclib.model.primitive import Boolean
from rpclib.model.primitive import DateTime
from rpclib.model.primitive import Float
from rpclib.model.primitive import Integer
from rpclib.model.primitive import Duration
from rpclib.model.primitive import String
from rpclib.model.primitive import Double

from rpclib.service import ServiceBase
from rpclib.decorator import rpc
from rpclib.decorator import srpc

from datetime import datetime

import logging
logger = logging.getLogger(__name__)

class SimpleClass(ComplexModel):
    i = Integer
    s = String

class DocumentedFault(Fault):
    def __init__(self):
        Fault.__init__(self,
                faultcode="Documented",
                faultstring="A documented fault",
                faultactor='http://faultactor.example.com',
                detail=etree.Element('something')
            )

class OtherClass(ComplexModel):
    dt = DateTime
    d = Double
    b = Boolean

class ClassWithSelfReference(ComplexModel):
    i = Integer
    sr = SelfReference

class NestedClass(ComplexModel):
    __namespace__ = "punk.tunk"

    simple = Array(SimpleClass)
    s = String
    i = Integer
    f = Float
    other = OtherClass
    ai = Array(Integer)

class NonNillableClass(ComplexModel):
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

class InHeader(ComplexModel):
    __namespace__ = "rpclib.test.interop.server"

    s=String
    i=Integer

class OutHeader(ComplexModel):
    __namespace__ = "rpclib.test.interop.server"

    dt=DateTime
    f=Float

class InTraceHeader(ComplexModel):
    __namespace__ = "rpclib.test.interop.server"

    client=String
    callDate=DateTime

class OutTraceHeader(ComplexModel):
    __namespace__ = "rpclib.test.interop.server"

    receiptDate=DateTime
    returnDate=DateTime

class InteropServiceWithHeader(ServiceBase):
    __in_header__ = InHeader
    __out_header__ = OutHeader

    @rpc(_returns=InHeader)
    def echo_in_header(ctx):
        return ctx.in_header

    @rpc(_returns=OutHeader)
    def send_out_header(ctx):
        ctx.out_header = OutHeader()
        ctx.out_header.dt = datetime(year=2000, month=1, day=1)
        ctx.out_header.f = 3.141592653

        return ctx.out_header

class InteropServiceWithComplexHeader(ServiceBase):
    __in_header__ = (InHeader, InTraceHeader)
    __out_header__ = (OutHeader, OutTraceHeader)

    @rpc(_returns=(InHeader, InTraceHeader))
    def echo_in_complex_header(ctx):
        return ctx.in_header

    @rpc(_returns=(OutHeader, OutTraceHeader))
    def send_out_complex_header(ctx):
        out_header = OutHeader()
        out_header.dt = datetime(year=2000, month=1, day=1)
        out_header.f = 3.141592653
        out_trace_header = OutTraceHeader()
        out_trace_header.receiptDate = datetime(year=2000, month=1, day=1,
                                  hour=1, minute=1, second=1, microsecond=1)
        out_trace_header.returnDate = datetime(year=2000, month=1, day=1,
                                 hour=1, minute=1, second=1, microsecond=100)
        ctx.out_header = (out_header, out_trace_header)

        return ctx.out_header

class InteropPrimitive(ServiceBase):
    @srpc(AnyXml, _returns=AnyXml)
    def echo_any(xml):
        return xml

    @srpc(AnyDict, _returns=AnyDict)
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

    @srpc(Duration, _returns=Duration)
    def echo_duration(dur):
        return dur

class InteropArray(ServiceBase):
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

class InteropClass(ServiceBase):
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

    @srpc(ClassWithSelfReference, _returns=ClassWithSelfReference)
    def echo_class_with_self_reference(sr):
        return sr

    @srpc(Attachment, _returns=Attachment)
    def echo_attachment(a):
        assert isinstance(a, Attachment)
        return a

    @srpc(Array(Attachment), _returns=Array(Attachment))
    def echo_attachment_array(aa):
        return aa

class InteropException(ServiceBase):
    @srpc()
    def python_exception():
        raise Exception("Possible")

    @srpc()
    def soap_exception():
        raise Fault("Plausible", "A plausible fault", 'http://faultactor.example.com',
                                            detail=etree.Element('something'))

    @srpc(_throws=DocumentedFault)
    def documented_exception():
        raise DocumentedFault()

class InteropMisc(ServiceBase):
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
        return ('0123456789abcdef' * 16384)

    @srpc()
    def test_empty():
        pass

    @srpc(String, Integer, DateTime)
    def multi_param(s, i, dt):
        pass

    @srpc(NonNillableClass, _returns=String)
    def non_nillable(n):
        return "OK"

    @srpc(String, _returns=String, _public_name="do_something")
    def do_something_else(s):
        return s

    @srpc(Integer, _returns=Array(OtherClass))
    def return_other_class_array(num):
        for i in range(num):
            yield OtherClass(dt=datetime(2010, 12, 6), d=3.0, b=True)

    @srpc(_returns=Attachment)
    def return_binary_data():
        return Attachment(data=''.join([chr(i) for i in range(256)]))

    @srpc(_returns=Integer)
    def return_invalid_data():
        return 'a'

    @srpc(String,
          _public_name="urn:#getCustomMessages",
          _in_message="getCustomMessagesMsgIn",
          _out_message="getCustomMessagesMsgOut",
          _out_variable_name="CustomMessages",
          _returns=String)
    def custom_messages(s):
        return s

services = [
    InteropPrimitive,
    InteropArray,
    InteropClass,
    InteropMisc,
    InteropServiceWithHeader,
    InteropServiceWithComplexHeader,
    InteropException,
]
