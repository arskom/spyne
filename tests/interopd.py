
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
from soaplib.wsgi_soap import SimpleWSGIApp

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

DaysOfWeekEnum = Enum(
    'Monday',
    'Tuesday',
    'Wednesday',
    'Friday',
    'Saturday',
    'Sunday',
    type_name = 'DaysOfWeekEnum'
)

class InteropService(SimpleWSGIApp):
    @rpc(Integer, _returns=Integer)
    def echoInteger(self, i):
        return i

    @rpc(String, _returns=String)
    def echoString(self, s):
        return s

    @rpc(DateTime, _returns=DateTime)
    def echoDateTime(self, dt):
        return dt

    @rpc(Float, _returns=Float)
    def echoFloat(self, f):
        return f

    @rpc(Boolean, _returns=Boolean)
    def echoBoolean(self, b):
        return b

    @rpc(DaysOfWeekEnum, _returns=DaysOfWeekEnum)
    def echoEnum(self, day):
        return day

    # lists of primitives

    @rpc(Array(Integer), _returns=Array(Integer))
    def echoIntegerArray(self, ia):
        return ia

    @rpc(Array(String), _returns=Array(String))
    def echoStringArray(self, sa):
        return sa

    @rpc(Array(DateTime), _returns=Array(DateTime))
    def echoDateTimeArray(self, dta):
        return dta

    @rpc(Array(Float), _returns=Array(Float))
    def echoFloatArray(self, fa):
        return fa

    @rpc(Array(Boolean), _returns=Array(Boolean))
    def echoBooleanArray(self, ba):
        return ba

    # classses

    @rpc(SimpleClass, _returns=SimpleClass)
    def echoSimpleClass(self, sc):
        return sc

    @rpc(Array(SimpleClass), _returns=Array(SimpleClass))
    def echoSimpleClassArray(self, sca):
        return sca

    @rpc(NestedClass, _returns=NestedClass)
    def echoNestedClass(self, nc):
        return nc

    @rpc(ExtensionClass, _returns=ExtensionClass)
    def echoExtensionClass(self, nc):
        return nc

    @rpc(Array(NestedClass), _returns=Array(NestedClass))
    def echoNestedClassArray(self, nca):
        return nca

    @rpc(Attachment, _returns=Attachment)
    def echoAttachment(self, a):
        return a

    @rpc(Array(Attachment), _returns=Array(Attachment))
    def echoAttachmentArray(self, aa):
        return aa

    @rpc()
    def testEmpty(self):
        pass

    @rpc(String, Integer, DateTime)
    def multiParam(self, s, i, dt):
        pass

    @rpc(_returns=String)
    def returnOnly(self):
        return 'howdy'

    @rpc(String, _returns=String,
                        _public_name="http://sample.org/webservices/doSomething")
    def doSomethingElse(self, s):
        return s

if __name__ == '__main__':
    try:
        from wsgiref.simple_server import make_server
        server = make_server('127.0.0.1', 9753, InteropService())
        print 'Starting interop server at -- %s:%s' % ('127.0.0.1', 9753)
        server.serve_forever()

    except ImportError:
        print "Error: example server code requires Python >= 2.5"
