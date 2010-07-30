#!/usr/bin/env python

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
from soaplib.serializers.clazz import ClassSerializer
from soaplib.serializers.enum import Enum

from soaplib.serializers.primitive import Array
from soaplib.serializers.primitive import Boolean
from soaplib.serializers.primitive import DateTime
from soaplib.serializers.primitive import Float
from soaplib.serializers.primitive import Integer
from soaplib.serializers.primitive import String

from soaplib.service import rpc
from soaplib.wsgi import AppBase
from soaplib.service import ValidatingDefinition

import logging
logger = logging.getLogger('soaplib')
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

class SimpleClass(ClassSerializer):
    i = Integer
    s = String

class OtherClass(ClassSerializer):
    dt = DateTime
    f = Float
    b = Boolean

class NestedClass(ClassSerializer):
    simple = Array(SimpleClass)
    s = String
    i = Integer
    f = Float
    other = OtherClass

class ExtensionClass(NestedClass):
    p = OtherClass
    l = DateTime
    q = Integer

class NonNillableClass(ClassSerializer):
    nillable = False
    min_occurs = 1

    d = DateTime(min_occurs=1, nillable=False)
    i = Integer(nillable=False)
    s = String(min_len=1, nillable=False)

DaysOfWeekEnum = Enum(
    'Monday',
    'Tuesday',
    'Wednesday',
    'Friday',
    'Saturday',
    'Sunday',
    type_name = 'DaysOfWeekEnum'
)

class InteropService(ValidatingDefinition):
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

    @rpc(Boolean, _returns=Boolean)
    def echo_boolean(self, b):
        return b

    @rpc(DaysOfWeekEnum, _returns=DaysOfWeekEnum)
    def echo_enum(self, day):
        return day

    # lists of primitives

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

    @rpc(Array(Boolean), _returns=Array(Boolean))
    def echo_boolean_array(self, ba):
        return ba

    # classses

    @rpc(SimpleClass, _returns=SimpleClass)
    def echo_simple_class(self, sc):
        return sc

    @rpc(Array(SimpleClass), _returns=Array(SimpleClass))
    def echo_simple_class_array(self, sca):
        return sca

    @rpc(NestedClass, _returns=NestedClass)
    def echo_nested_class(self, nc):
        return nc

    @rpc(ExtensionClass, _returns=ExtensionClass)
    def echo_extension_class(self, nc):
        return nc

    @rpc(Array(NestedClass), _returns=Array(NestedClass))
    def echo_nested_class_array(self, nca):
        return nca

    @rpc(Attachment, _returns=Attachment)
    def echo_attachment(self, a):
        return a

    @rpc(Array(Attachment), _returns=Array(Attachment))
    def echo_attachment_array(self, aa):
        return aa

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

    @rpc(String, _returns=String,
                       _public_name="http://sample.org/webservices/doSomething")
    def do_something_else(self, s):
        return s

if __name__ == '__main__':
    try:
        from wsgiref.simple_server import make_server
        server = make_server('127.0.0.1', 9753, AppBase(InteropService))
        print 'Starting interop server at -- %s:%s' % ('127.0.0.1', 9753)
        server.serve_forever()

    except ImportError:
        print "Error: example server code requires Python >= 2.5"
