#
# soaplib - Copyright (C) 2009 Aaron Bickell, Jamie Kirkpatrick
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

from soaplib.service import soapmethod
from soaplib.serializers.binary import Attachment
from soaplib.serializers.clazz import ClassSerializer
from soaplib.serializers.primitive import (
    String, Integer, DateTime, Float, Boolean, Array)
from soaplib.wsgi_soap import SimpleWSGISoapApp, log_debug, log_exceptions


class SimpleClass(ClassSerializer):

    class types:
        i = Integer
        s = String


class OtherClass(ClassSerializer):

    class types:
        dt = DateTime
        f = Float
        b = Boolean


class NestedClass(ClassSerializer):

    class types:
        simple = Array(SimpleClass)
        s = String
        i = Integer
        f = Float
        other = OtherClass


class InteropService(SimpleWSGISoapApp):

    # basic primitives

    @soapmethod(Integer, _returns=Integer)
    def echoInteger(self, i):
        return i

    @soapmethod(String, _returns=String)
    def echoString(self, s):
        return s

    @soapmethod(DateTime, _returns=DateTime)
    def echoDateTime(self, dt):
        return dt

    @soapmethod(Float, _returns=Float)
    def echoFloat(self, f):
        return f

    @soapmethod(Boolean, _returns=Boolean)
    def echoBoolean(self, b):
        return b

    # lists of primitives

    @soapmethod(Array(Integer), _returns=Array(Integer))
    def echoIntegerArray(self, ia):
        return ia

    @soapmethod(Array(String), _returns=Array(String))
    def echoStringArray(self, sa):
        return sa

    @soapmethod(Array(DateTime), _returns=Array(DateTime))
    def echoDateTimeArray(self, dta):
        return dta

    @soapmethod(Array(Float), _returns=Array(Float))
    def echoFloatArray(self, fa):
        return fa

    @soapmethod(Array(Boolean), _returns=Array(Boolean))
    def echoBooleanArray(self, ba):
        return ba

    # classses

    @soapmethod(SimpleClass, _returns=SimpleClass)
    def echoSimpleClass(self, sc):
        return sc

    @soapmethod(Array(SimpleClass), _returns=Array(SimpleClass))
    def echoSimpleClassArray(self, sca):
        return sca

    @soapmethod(NestedClass, _returns=NestedClass)
    def echoNestedClass(self, nc):
        return nc

    @soapmethod(Array(NestedClass), _returns=Array(NestedClass))
    def echoNestedClassArray(self, nca):
        return nca

    @soapmethod(Attachment, _returns=Attachment)
    def echoAttachment(self, a):
        return a

    @soapmethod(Array(Attachment), _returns=Array(Attachment))
    def echoAttachmentArray(self, aa):
        return aa

    @soapmethod()
    def testEmpty(self):
        # new
        pass

    @soapmethod(String, Integer, DateTime)
    def multiParam(self, s, i, dt):
        # new
        pass

    @soapmethod(_returns=String)
    def returnOnly(self):
        # new
        return 'howdy'

    @soapmethod(String, _returns=String,
        _soapAction="http://sample.org/webservices/doSomething")
    def doSomethingElse(self, s):
        return s


if __name__ == '__main__':
    try:
        from wsgiref.simple_server import make_server
        log_debug(True)
        log_exceptions(True)
        server = make_server('127.0.0.1', 9753, InteropService())
        print 'Starting interop server at -- %s:%s' % ('127.0.0.1', 9753)
        server.serve_forever()
    except ImportError:
        print "Error: example server code requires Python >= 2.5"
