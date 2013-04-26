#!/usr/bin/env python
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

from spyne.model.binary import binary_encoding_handlers
import logging
logging.basicConfig(level=logging.DEBUG)

import unittest

import decimal
import datetime
import uuid
import pytz

import lxml.etree

from lxml.builder import E

from spyne import MethodContext
from spyne.service import ServiceBase
from spyne.server import ServerBase
from spyne.application import Application
from spyne.decorator import srpc
from spyne.model.complex import ComplexModel
from spyne.model.complex import Iterable
from spyne.model.fault import Fault
from spyne.protocol import ProtocolBase
from spyne.model.binary import ByteArray
from spyne.model.primitive import Decimal
from spyne.model.primitive import Integer
from spyne.model.primitive import String
from spyne.model.primitive import DateTime
from spyne.model.primitive import Mandatory
from spyne.model.primitive import AnyXml
from spyne.model.primitive import AnyHtml
from spyne.model.primitive import AnyDict
from spyne.model.primitive import Unicode
from spyne.model.primitive import String
from spyne.model.primitive import AnyUri
from spyne.model.primitive import ImageUri
from spyne.model.primitive import Decimal
from spyne.model.primitive import Double
from spyne.model.primitive import Integer
from spyne.model.primitive import Time
from spyne.model.primitive import DateTime
from spyne.model.primitive import Date
from spyne.model.primitive import Duration
from spyne.model.primitive import Boolean
from spyne.model.primitive import Uuid
from spyne.model.primitive import Point
from spyne.model.primitive import Line
from spyne.model.primitive import Polygon
from spyne.model.primitive import MultiPoint
from spyne.model.primitive import MultiLine
from spyne.model.primitive import MultiPolygon


def TDictDocumentTest(serializer, _DictDocumentChild, dumps_kwargs={}):
    def _dry_me(services, d, ignore_wrappers=False, complex_as=dict,
                         just_ctx=False, just_in_object=False, validator=None):

        app = Application(services, 'tns',
                in_protocol=_DictDocumentChild(validator=validator),
                out_protocol=_DictDocumentChild(
                        ignore_wrappers=ignore_wrappers, complex_as=complex_as),
            )

        server = ServerBase(app)
        initial_ctx = MethodContext(server)
        initial_ctx.in_string = [serializer.dumps(d, **dumps_kwargs)]

        ctx, = server.generate_contexts(initial_ctx)
        if not just_ctx:
            server.get_in_object(ctx)
            if not just_in_object:
                server.get_out_object(ctx)
                server.get_out_string(ctx)

        return ctx

    class Test(unittest.TestCase):
        def test_complex_with_only_primitive_fields(self):
            class SomeComplexModel(ComplexModel):
                i = Integer
                s = Unicode

            class SomeService(ServiceBase):
                @srpc(SomeComplexModel, _returns=SomeComplexModel)
                def some_call(scm):
                    return SomeComplexModel(i=5, s='5x')

            ctx = _dry_me([SomeService], {"some_call":[]})

            s = ''.join(ctx.out_string)
            d = serializer.dumps({"some_callResponse": {"some_callResult":
                    {"SomeComplexModel": {"i": 5, "s": "5x"}}}}, **dumps_kwargs)
            print s
            print d
            assert s == d

        def test_complex(self):
            class CM(ComplexModel):
                i = Integer
                s = Unicode

            class CCM(ComplexModel):
                c = CM
                i = Integer
                s = Unicode

            class SomeService(ServiceBase):
                @srpc(CCM, _returns=CCM)
                def some_call(ccm):
                    return CCM(c=ccm.c, i=ccm.i, s=ccm.s)

            ctx = _dry_me([SomeService], {"some_call":
                    {"ccm": {"c":{"i":3, "s": "3x"}, "i":4, "s": "4x"}}
                })

            ret = serializer.loads(''.join(ctx.out_string))

            print(ret)

            d = ret['some_callResponse']['some_callResult']['CCM']
            assert d['i'] == 4
            assert d['s'] == '4x'
            assert d['c']['CM']['i'] == 3
            assert d['c']['CM']['s'] == '3x'

        def test_multiple_list(self):
            class SomeService(ServiceBase):
                @srpc(Unicode(max_occurs=Decimal('inf')),
                                    _returns=Unicode(max_occurs=Decimal('inf')))
                def some_call(s):
                    return s

            ctx = _dry_me([SomeService], {"some_call":[["a","b"]]})

            assert ''.join(ctx.out_string) == serializer.dumps(
                    {"some_callResponse": {"some_callResult": ["a", "b"]}},
                                                                 **dumps_kwargs)

        def test_multiple_dict(self):
            class SomeService(ServiceBase):
                @srpc(Unicode(max_occurs=Decimal('inf')),
                                    _returns=Unicode(max_occurs=Decimal('inf')))
                def some_call(s):
                    return s

            ctx = _dry_me([SomeService], {"some_call":{"s":["a","b"]}})

            assert ''.join(ctx.out_string) == serializer.dumps(
                    {"some_callResponse": {"some_callResult": ["a", "b"]}},
                                                                 **dumps_kwargs)

        def test_multiple_dict_array(self):
            class SomeService(ServiceBase):
                @srpc(Iterable(Unicode), _returns=Iterable(Unicode))
                def some_call(s):
                    return s

            ctx = _dry_me([SomeService], {"some_call":{"s":["a","b"]}})

            assert list(ctx.out_string) == [serializer.dumps(
                 {"some_callResponse": {"some_callResult": ["a", "b"]}}, **dumps_kwargs)]

        def test_multiple_dict_complex_array(self):
            class CM(ComplexModel):
                i = Integer
                s = Unicode

            class CCM(ComplexModel):
                c = CM
                i = Integer
                s = Unicode

            class ECM(CCM):
                d = DateTime

            class SomeService(ServiceBase):
                @srpc(Iterable(ECM), _returns=Iterable(ECM))
                def some_call(ecm):
                    return ecm

            ctx = _dry_me([SomeService], {
                "some_call": {"ecm": [{
                        "c": {"i":3, "s": "3x"},
                        "i":4,
                        "s": "4x",
                        "d": "2011-12-13T14:15:16Z"
                    }]
                }})

            print(ctx.in_object)

            ret = serializer.loads(''.join(ctx.out_string))
            print(ret)
            assert ret["some_callResponse"]['some_callResult']
            assert ret["some_callResponse"]['some_callResult'][0]
            assert ret["some_callResponse"]['some_callResult'][0]["ECM"]["c"]
            assert ret["some_callResponse"]['some_callResult'][0]["ECM"]["c"]["CM"]["i"] == 3
            assert ret["some_callResponse"]['some_callResult'][0]["ECM"]["c"]["CM"]["s"] == "3x"
            assert ret["some_callResponse"]['some_callResult'][0]["ECM"]["i"] == 4
            assert ret["some_callResponse"]['some_callResult'][0]["ECM"]["s"] == "4x"
            assert ret["some_callResponse"]['some_callResult'][0]["ECM"]["d"] == "2011-12-13T14:15:16+00:00"


        def test_invalid_request(self):
            class SomeService(ServiceBase):
                @srpc(Integer, String, DateTime)
                def yay(i,s,d):
                    print(i,s,d)

            ctx = _dry_me([SomeService], {"some_call": {"yay": []}},
                                                            just_in_object=True)

            print(ctx.in_error)
            assert ctx.in_error.faultcode == 'Client.ResourceNotFound'

        def test_invalid_string(self):
            class SomeService(ServiceBase):
                @srpc(Integer, String, DateTime)
                def yay(i,s,d):
                    print(i, s, d)

            ctx = _dry_me([SomeService], {"yay": {"s": 1}}, validator='soft',
                                                            just_in_object=True)

            assert ctx.in_error.faultcode == 'Client.ValidationError'

        def test_invalid_number(self):
            class SomeService(ServiceBase):
                @srpc(Integer, String, DateTime)
                def yay(i,s,d):
                    print(i,s,d)

            ctx = _dry_me([SomeService], {"yay": ["s", "B"]}, validator='soft',
                                                            just_in_object=True)

            assert ctx.in_error.faultcode == 'Client.ValidationError'

        def test_missing_value(self):
            class SomeService(ServiceBase):
                @srpc(Integer, Unicode, Mandatory.DateTime)
                def yay(i,s,d):
                    print(i,s,d)

            ctx = _dry_me([SomeService], {"yay": [1, "B"]}, validator='soft',
                                                            just_in_object=True)

            print(ctx.in_error.faultstring)
            assert ctx.in_error.faultcode == 'Client.ValidationError'
            assert ctx.in_error.faultstring.endswith("at least 1 times.")

        def test_invalid_datetime(self):
            class SomeService(ServiceBase):
                @srpc(Integer, String, Mandatory.DateTime)
                def yay(i,s,d):
                    print(i,s,d)

            ctx = _dry_me([SomeService],{"yay": {"d":"a2011"}},validator='soft',
                                                            just_in_object=True)

            assert ctx.in_error.faultcode == 'Client.ValidationError'

        def test_fault_to_dict(self):
            class SomeService(ServiceBase):
                @srpc(_returns=String)
                def some_call():
                    raise Fault()

            ctx = _dry_me([SomeService], {"some_call":[]})

        def test_prune_none_and_optional(self):
            class SomeObject(ComplexModel):
                i = Integer
                s = String(min_occurs=1)

            class SomeService(ServiceBase):
                @srpc(_returns=SomeObject)
                def some_call():
                    raise SomeObject()

        def test_any_xml(self):
            d = lxml.etree.tostring(E('{ns1}x', E('{ns2}Y', "some data")))

            class SomeService(ServiceBase):
                @srpc(AnyXml, _returns=AnyXml)
                def some_call(p):
                    print p
                    print type(p)
                    assert type(p) == lxml.etree._Element
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = ''.join(ctx.out_string)
            d = serializer.dumps({"some_callResponse": {"some_callResult":
                                                        d}}, **dumps_kwargs)
            print s
            print d
            assert s == d


        def test_any_html(self):
            d = lxml.html.tostring(E('div', E('span', "something")))

            class SomeService(ServiceBase):
                @srpc(AnyHtml, _returns=AnyHtml)
                def some_call(p):
                    print p
                    print type(p)
                    assert type(p) == lxml.html.HtmlElement
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = ''.join(ctx.out_string)
            d = serializer.dumps({"some_callResponse": {"some_callResult":
                                                        d}}, **dumps_kwargs)
            print s
            print d
            assert s == d


        def test_any_dict(self):
            d = {'helo': 213, 'data': {'nested': [12, 0.3]}}

            class SomeService(ServiceBase):
                @srpc(AnyDict, _returns=AnyDict)
                def some_call(p):
                    print p
                    print type(p)
                    assert type(p) == dict
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = ''.join(ctx.out_string)
            d = serializer.dumps({"some_callResponse": {"some_callResult":
                                                        d}}, **dumps_kwargs)
            print s
            print d
            assert s == d

        def test_unicode(self):
            d = u'some string'

            class SomeService(ServiceBase):
                @srpc(Unicode, _returns=Unicode)
                def some_call(p):
                    print p
                    print type(p)
                    assert type(p) == unicode
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = ''.join(ctx.out_string)
            d = serializer.dumps({"some_callResponse": {"some_callResult":
                                                        d}}, **dumps_kwargs)
            print s
            print d
            assert s == d

        def test_string(self):
            d = 'some string'

            class SomeService(ServiceBase):
                @srpc(String(encoding='utf8'), _returns=String)
                def some_call(p):
                    print p
                    print type(p)
                    assert isinstance(p, str)
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = ''.join(ctx.out_string)
            d = serializer.dumps({"some_callResponse": {"some_callResult":
                                                        d}}, **dumps_kwargs)
            print s
            print d
            assert s == d

        def test_any_uri(self):
            d = 'http://example.com/?asd=b12&df=aa#tag'

            class SomeService(ServiceBase):
                @srpc(AnyUri, _returns=AnyUri)
                def some_call(p):
                    print p
                    print type(p)
                    assert isinstance(p, basestring)
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = ''.join(ctx.out_string)
            d = serializer.dumps({"some_callResponse": {"some_callResult":
                                                        d}}, **dumps_kwargs)
            print s
            print d
            assert s == d

        def test_image_uri(self):
            d = 'http://example.com/funny.gif'

            class SomeService(ServiceBase):
                @srpc(ImageUri, _returns=ImageUri)
                def some_call(p):
                    print p
                    print type(p)
                    assert isinstance(p, basestring)
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = ''.join(ctx.out_string)
            d = serializer.dumps({"some_callResponse": {"some_callResult":
                                                        d}}, **dumps_kwargs)
            print s
            print d
            assert s == d

        def test_decimal(self):
            d = decimal.Decimal('1e100')
            if _DictDocumentChild._decimal_as_string:
                d = str(d)

            class SomeService(ServiceBase):
                @srpc(Decimal, _returns=Decimal)
                def some_call(p):
                    print p
                    print type(p)
                    assert type(p) == decimal.Decimal
                    return p

            ctx = _dry_me([SomeService], {"some_call": [d]})

            s = ''.join(ctx.out_string)
            d = serializer.dumps({"some_callResponse":
                                        {"some_callResult": d}}, **dumps_kwargs)
            print s
            print d
            assert s == d

        def test_double(self):
            d = 12.3467

            class SomeService(ServiceBase):
                @srpc(Double, _returns=Double)
                def some_call(p):
                    print p
                    print type(p)
                    assert type(p) == float
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = ''.join(ctx.out_string)
            d = serializer.dumps({"some_callResponse": {"some_callResult":
                                                        d}}, **dumps_kwargs)
            print s
            print d
            assert s == d

        def test_integer(self):
            d = 5

            class SomeService(ServiceBase):
                @srpc(Integer, _returns=Integer)
                def some_call(p):
                    print p
                    print type(p)
                    assert type(p) == int
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = ''.join(ctx.out_string)
            d = serializer.dumps({"some_callResponse": {"some_callResult":
                                                        d}}, **dumps_kwargs)
            print s
            print d
            assert s == d

        def test_integer(self):
            d = -1<<1000
            if _DictDocumentChild._huge_numbers_as_string:
                d = str(d)

            class SomeService(ServiceBase):
                @srpc(Integer, _returns=Integer)
                def some_call(p):
                    print p
                    print type(p)
                    assert type(p) == long
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = ''.join(ctx.out_string)
            d = serializer.dumps({"some_callResponse": {"some_callResult":
                                                        d}}, **dumps_kwargs)

            print s
            print d
            assert s == d

        def test_integer_2(self):
            d = 1<<1000
            if _DictDocumentChild._huge_numbers_as_string:
                d = str(d)

            class SomeService(ServiceBase):
                @srpc(Integer, _returns=Integer)
                def some_call(p):
                    print p
                    print type(p)
                    assert type(p) == long
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = ''.join(ctx.out_string)
            d = serializer.dumps({"some_callResponse": {"some_callResult":
                                                        d}}, **dumps_kwargs)
            print s
            print d
            assert s == d

        def test_time(self):
            d = datetime.time(10, 20, 30).isoformat()

            class SomeService(ServiceBase):
                @srpc(Time, _returns=Time)
                def some_call(p):
                    print p
                    print type(p)
                    assert type(p) == datetime.time
                    assert p.isoformat() == d
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = ''.join(ctx.out_string)
            d = serializer.dumps({"some_callResponse": {"some_callResult":
                                                        d}}, **dumps_kwargs)
            print s
            print d
            assert s == d

        def test_date(self):
            d = datetime.date(2010, 9, 8).isoformat()

            class SomeService(ServiceBase):
                @srpc(Date, _returns=Date)
                def some_call(p):
                    print p
                    print type(p)
                    assert type(p) == datetime.date
                    assert p.isoformat() == d
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = ''.join(ctx.out_string)
            d = serializer.dumps({"some_callResponse": {"some_callResult":
                                                        d}}, **dumps_kwargs)
            print s
            print d
            assert s == d


        def test_datetime(self):
            d = datetime.datetime(2010, 9, 8, 7, 6, 5).isoformat()

            class SomeService(ServiceBase):
                @srpc(DateTime, _returns=DateTime)
                def some_call(p):
                    print p
                    print type(p)
                    assert type(p) == datetime.datetime
                    assert p.isoformat() == d
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = ''.join(ctx.out_string)
            d = serializer.dumps({"some_callResponse": {"some_callResult":
                                                        d}}, **dumps_kwargs)
            print s
            print d
            assert s == d

        def test_datetime_tz(self):
            d = datetime.datetime(2010, 9, 8, 7, 6, 5, tzinfo=pytz.UTC).isoformat()

            class SomeService(ServiceBase):
                @srpc(DateTime, _returns=DateTime)
                def some_call(p):
                    print p
                    print type(p)
                    assert type(p) == datetime.datetime
                    assert p.isoformat() == d
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = ''.join(ctx.out_string)
            d = serializer.dumps({"some_callResponse": {"some_callResult":
                                                        d}}, **dumps_kwargs)
            print s
            print d
            assert s == d

        def test_duration(self):
            d = ProtocolBase().to_string(Duration, datetime.timedelta(0, 45))

            class SomeService(ServiceBase):
                @srpc(Duration, _returns=Duration)
                def some_call(p):
                    print p
                    print type(p)
                    assert type(p) == datetime.timedelta
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = ''.join(ctx.out_string)
            d = serializer.dumps({"some_callResponse": {"some_callResult":
                                                        d}}, **dumps_kwargs)
            print s
            print d
            assert s == d

        def test_boolean(self):
            d = True

            class SomeService(ServiceBase):
                @srpc(Boolean, _returns=Boolean)
                def some_call(p):
                    print p
                    print type(p)
                    assert type(p) == bool
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = ''.join(ctx.out_string)
            d = serializer.dumps({"some_callResponse": {"some_callResult":
                                                        d}}, **dumps_kwargs)
            print s
            print d
            assert s == d

        def test_uuid(self):
            d = '7d2a6330-eb64-4900-8a10-38ebef415e9d'

            class SomeService(ServiceBase):
                @srpc(Uuid, _returns=Uuid)
                def some_call(p):
                    print p
                    print type(p)
                    assert type(p) == uuid.UUID
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = ''.join(ctx.out_string)
            d = serializer.dumps({"some_callResponse": {"some_callResult":
                                                        d}}, **dumps_kwargs)
            print s
            print d
            assert s == d

        def test_point2d(self):
            d = 'POINT(1 2)'

            class SomeService(ServiceBase):
                @srpc(Point, _returns=Point)
                def some_call(p):
                    print p
                    print type(p)
                    assert isinstance(p, basestring)
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = ''.join(ctx.out_string)
            d = serializer.dumps({"some_callResponse": {"some_callResult":
                                                        d}}, **dumps_kwargs)
            print s
            print d
            assert s == d

        def test_point3d(self):
            d = 'POINT(1 2 3)'

            class SomeService(ServiceBase):
                @srpc(Point, _returns=Point)
                def some_call(p):
                    print p
                    print type(p)
                    assert isinstance(p, basestring)
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = ''.join(ctx.out_string)
            d = serializer.dumps({"some_callResponse": {"some_callResult":
                                                        d}}, **dumps_kwargs)
            print s
            print d
            assert s == d

        def test_line2d(self):
            d = 'LINESTRING(1 2, 3 4)'

            class SomeService(ServiceBase):
                @srpc(Line, _returns=Line)
                def some_call(p):
                    print p
                    print type(p)
                    assert isinstance(p, basestring)
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = ''.join(ctx.out_string)
            d = serializer.dumps({"some_callResponse": {"some_callResult":
                                                        d}}, **dumps_kwargs)
            print s
            print d
            assert s == d

        def test_line3d(self):
            d = 'LINESTRING(1 2 3, 4 5 6)'

            class SomeService(ServiceBase):
                @srpc(Line, _returns=Line)
                def some_call(p):
                    print p
                    print type(p)
                    assert isinstance(p, basestring)
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = ''.join(ctx.out_string)
            d = serializer.dumps({"some_callResponse": {"some_callResult":
                                                        d}}, **dumps_kwargs)
            print s
            print d
            assert s == d

        def test_polygon2d(self):
            d = 'POLYGON((1 1, 1 2, 2 2, 2 1, 1 1))'

            class SomeService(ServiceBase):
                @srpc(Polygon(2), _returns=Polygon(2))
                def some_call(p):
                    print p
                    print type(p)
                    assert isinstance(p, basestring)
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = ''.join(ctx.out_string)
            d = serializer.dumps({"some_callResponse": {"some_callResult":
                                                        d}}, **dumps_kwargs)
            print s
            print d
            assert s == d

        def test_polygon3d(self):
            d = 'POLYGON((1 1 0, 1 2 0, 2 2 0, 2 1 0, 1 1 0))'

            class SomeService(ServiceBase):
                @srpc(Polygon(3), _returns=Polygon(3))
                def some_call(p):
                    print p
                    print type(p)
                    assert isinstance(p, basestring)
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = ''.join(ctx.out_string)
            d = serializer.dumps({"some_callResponse": {"some_callResult":
                                                        d}}, **dumps_kwargs)
            print s
            print d
            assert s == d

        def test_multipoint2d(self):
            d = 'MULTIPOINT ((10 40), (40 30), (20 20), (30 10))'

            class SomeService(ServiceBase):
                @srpc(MultiPoint(2), _returns=MultiPoint(2))
                def some_call(p):
                    print p
                    print type(p)
                    assert isinstance(p, basestring)
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = ''.join(ctx.out_string)
            d = serializer.dumps({"some_callResponse": {"some_callResult":
                                                        d}}, **dumps_kwargs)
            print s
            print d
            assert s == d

        def test_multipoint3d(self):
            d = 'MULTIPOINT (10 40 30, 40 30 10,)'

            class SomeService(ServiceBase):
                @srpc(MultiPoint(3), _returns=MultiPoint(3))
                def some_call(p):
                    print p
                    print type(p)
                    assert isinstance(p, basestring)
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = ''.join(ctx.out_string)
            d = serializer.dumps({"some_callResponse": {"some_callResult":
                                                        d}}, **dumps_kwargs)
            print s
            print d
            assert s == d

        def test_multiline2d(self):
            d = 'MULTILINESTRING ((10 10, 20 20, 10 40), (40 40, 30 30, 40 20, 30 10))'

            class SomeService(ServiceBase):
                @srpc(MultiLine(2), _returns=MultiLine(2))
                def some_call(p):
                    print p
                    print type(p)
                    assert isinstance(p, basestring)
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = ''.join(ctx.out_string)
            d = serializer.dumps({"some_callResponse": {"some_callResult":
                                                        d}}, **dumps_kwargs)
            print s
            print d
            assert s == d

        def test_multiline3d(self):
            d = 'MULTILINESTRING ((10 10, 20 20, 10 40), (40 40, 30 30, 40 20, 30 10))'

            class SomeService(ServiceBase):
                @srpc(MultiLine(3), _returns=MultiLine(3))
                def some_call(p):
                    print p
                    print type(p)
                    assert isinstance(p, basestring)
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = ''.join(ctx.out_string)
            d = serializer.dumps({"some_callResponse": {"some_callResult":
                                                        d}}, **dumps_kwargs)
            print s
            print d
            assert s == d

        def test_multipolygon2d(self):
            d = 'MULTIPOLYGON (((30 20, 10 40, 45 40, 30 20)),((15 5, 40 10, 10 20, 5 10, 15 5)))'

            class SomeService(ServiceBase):
                @srpc(MultiPolygon(2), _returns=MultiPolygon(2))
                def some_call(p):
                    print p
                    print type(p)
                    assert isinstance(p, basestring)
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = ''.join(ctx.out_string)
            d = serializer.dumps({"some_callResponse": {"some_callResult":
                                                        d}}, **dumps_kwargs)
            print s
            print d
            assert s == d

        def test_multipolygon3d(self):
            d = 'MULTIPOLYGON (((40 40, 20 45, 45 30, 40 40)),((20 35, 45 20, 30 5, 10 10, 10 30, 20 35),(30 20, 20 25, 20 15, 30 20)))'

            class SomeService(ServiceBase):
                @srpc(MultiPolygon(3), _returns=MultiPolygon(3))
                def some_call(p):
                    print p
                    print type(p)
                    assert isinstance(p, basestring)
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = ''.join(ctx.out_string)
            d = serializer.dumps({"some_callResponse": {"some_callResult":
                                                        d}}, **dumps_kwargs)
            print s
            print d
            assert s == d

        def test_generator(self):
            class SomeService(ServiceBase):
                @srpc(_returns=Iterable(Integer))
                def some_call():
                    return iter(range(1000))

            ctx = _dry_me([SomeService], {"some_call":[]})

            s = ''.join(ctx.out_string)
            d = serializer.dumps({"some_callResponse": {"some_callResult":
                                                  range(1000)}}, **dumps_kwargs)
            print s
            print d
            assert s == d

        def test_bytearray(self):
            dbe = _DictDocumentChild.default_binary_encoding
            beh = binary_encoding_handlers[dbe]

            data = ''.join([chr(x) for x in range(0xff)])
            if beh is not None:
                encoded_data = beh(data)

            class SomeService(ServiceBase):
                @srpc(ByteArray, _returns=ByteArray)
                def some_call(p):
                    print p
                    print type(p)
                    assert isinstance(p, list)
                    assert p == [data]
                    return p

            ctx = _dry_me([SomeService], {"some_call": [encoded_data]})

            s = ''.join(ctx.out_string)
            d = serializer.dumps({"some_callResponse": {"some_callResult":
                                                encoded_data}}, **dumps_kwargs)

            print s
            print d
            print encoded_data
            assert s == d

    return Test
