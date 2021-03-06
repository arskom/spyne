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

from __future__ import unicode_literals

import logging

import yaml

logger = logging.getLogger(__name__)

import unittest

import uuid
import pytz
import decimal
from spyne.util import six
from spyne.util.dictdoc import get_object_as_dict

if not six.PY2:
    long = int

from datetime import datetime
from datetime import date
from datetime import time
from datetime import timedelta

import lxml.etree
import lxml.html

from lxml.builder import E

from spyne import MethodContext, Ignored
from spyne.service import Service
from spyne.server import ServerBase
from spyne.application import Application
from spyne.decorator import srpc, rpc
from spyne.error import ValidationError
from spyne.model.binary import binary_encoding_handlers, File
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
from spyne.model.primitive import AnyUri
from spyne.model.primitive import ImageUri
from spyne.model.primitive import Double
from spyne.model.primitive import Integer8
from spyne.model.primitive import Time
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


def _unbyte(d):
    if d is None:
        return

    for k, v in list(d.items()):
        if isinstance(k, bytes):
            del d[k]
            d[k.decode('utf8')] = v

        if isinstance(v, dict):
            _unbyte(v)

    for k, v in d.items():
        if isinstance(v, (list, tuple)):
            l = []
            for sub in v:
                if isinstance(sub, dict):
                    l.append(_unbyte(sub))

                elif isinstance(sub, bytes):
                    l.append(sub.decode("utf8"))

                else:
                    l.append(sub)

            d[k] = tuple(l)

        elif isinstance(v, bytes):
            try:
                d[k] = v.decode('utf8')
            except UnicodeDecodeError:
                d[k] = v

    return d


def TDry(serializer, _DictDocumentChild, dumps_kwargs=None):
    if not dumps_kwargs:
        dumps_kwargs = {}

    def _dry_me(services, d, ignore_wrappers=False, complex_as=dict,
                    just_ctx=False, just_in_object=False, validator=None,
                                                             polymorphic=False):

        app = Application(services, 'tns',
                in_protocol=_DictDocumentChild(
                    ignore_wrappers=ignore_wrappers, complex_as=complex_as,
                    polymorphic=polymorphic, validator=validator,
                ),
                out_protocol=_DictDocumentChild(
                     ignore_wrappers=ignore_wrappers, complex_as=complex_as,
                                                       polymorphic=polymorphic),
            )

        server = ServerBase(app)
        initial_ctx = MethodContext(server, MethodContext.SERVER)
        in_string = serializer.dumps(d, **dumps_kwargs)
        if not isinstance(in_string, bytes):
            in_string = in_string.encode('utf8')
        initial_ctx.in_string = [in_string]

        ctx, = server.generate_contexts(initial_ctx, in_string_charset='utf8')
        if not just_ctx:
            server.get_in_object(ctx)
            if not just_in_object:
                server.get_out_object(ctx)
                server.get_out_string(ctx)

        return ctx
    return _dry_me

def TDictDocumentTest(serializer, _DictDocumentChild, dumps_kwargs=None,
                                          loads_kwargs=None, convert_dict=None):
    if not dumps_kwargs:
        dumps_kwargs = {}
    if not loads_kwargs:
        loads_kwargs = {}
    _dry_me = TDry(serializer, _DictDocumentChild, dumps_kwargs)

    if convert_dict is None:
        convert_dict = lambda v: v

    class Test(unittest.TestCase):
        def dumps(self, o):
            print("using", dumps_kwargs, "to dump", o)
            return serializer.dumps(o, **dumps_kwargs)

        def loads(self, o):
            try:
                return _unbyte(serializer.loads(o, **loads_kwargs))
            except TypeError:
                return _unbyte(serializer.loads(o, Loader=yaml.FullLoader, **loads_kwargs))

        def test_complex_with_only_primitive_fields(self):
            class SomeComplexModel(ComplexModel):
                i = Integer
                s = Unicode

            class SomeService(Service):
                @srpc(SomeComplexModel, _returns=SomeComplexModel)
                def some_call(scm):
                    return SomeComplexModel(i=5, s='5x')

            ctx = _dry_me([SomeService], {"some_call":[]})

            s = self.loads(b''.join(ctx.out_string))

            s = s["some_callResponse"]["some_callResult"]["SomeComplexModel"]
            assert s["i"] == 5
            assert s["s"] in ("5x", b"5x")

        def test_complex(self):
            class CM(ComplexModel):
                i = Integer
                s = Unicode

            class CCM(ComplexModel):
                c = CM
                i = Integer
                s = Unicode

            class SomeService(Service):
                @srpc(CCM, _returns=CCM)
                def some_call(ccm):
                    return CCM(c=ccm.c, i=ccm.i, s=ccm.s)

            ctx = _dry_me([SomeService], {"some_call":
                    {"ccm": {"CCM":{
                        "c":{"CM":{"i":3, "s": "3x"}},
                        "i":4,
                        "s": "4x",
                    }}}
                })

            ret = self.loads(b''.join(ctx.out_string))
            print(ret)

            d = ret['some_callResponse']['some_callResult']['CCM']
            assert d['i'] == 4
            assert d['s'] in ('4x', b'4x')
            assert d['c']['CM']['i'] == 3
            assert d['c']['CM']['s'] in ('3x', b'3x')

        def test_multiple_list(self):
            class SomeService(Service):
                @srpc(Unicode(max_occurs=decimal.Decimal('inf')),
                            _returns=Unicode(max_occurs=decimal.Decimal('inf')))
                def some_call(s):
                    return s

            ctx = _dry_me([SomeService], {"some_call":[["a","b"]]})

            data = b''.join(ctx.out_string)
            print(data)

            assert self.loads(data) == \
                          {"some_callResponse": {"some_callResult": ("a", "b")}}

        def test_multiple_dict(self):
            class SomeService(Service):
                @srpc(Unicode(max_occurs=decimal.Decimal('inf')),
                            _returns=Unicode(max_occurs=decimal.Decimal('inf')))
                def some_call(s):
                    return s

            ctx = _dry_me([SomeService], {"some_call":{"s":["a","b"]}})

            assert self.loads(b''.join(ctx.out_string)) == \
                    {"some_callResponse": {"some_callResult": ("a", "b")}}

        def test_multiple_dict_array(self):
            class SomeService(Service):
                @srpc(Iterable(Unicode), _returns=Iterable(Unicode))
                def some_call(s):
                    return s

            ctx = _dry_me([SomeService], {"some_call":{"s":["a","b"]}})

            assert self.loads(b''.join(ctx.out_string)) == \
                 {"some_callResponse": {"some_callResult": ("a", "b")}}

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

            class SomeService(Service):
                @srpc(Iterable(ECM), _returns=Iterable(ECM))
                def some_call(ecm):
                    return ecm

            ctx = _dry_me([SomeService], {
                "some_call": {"ecm": [{"ECM": {
                        "c": {"CM":{"i":3, "s": "3x"}},
                        "i":4,
                        "s": "4x",
                        "d": "2011-12-13T14:15:16Z"
                    }}]
                }})

            print(ctx.in_object)

            ret = self.loads(b''.join(ctx.out_string))
            print(ret)
            assert ret["some_callResponse"]['some_callResult']
            assert ret["some_callResponse"]['some_callResult'][0]
            assert ret["some_callResponse"]['some_callResult'][0]["ECM"]["c"]
            assert ret["some_callResponse"]['some_callResult'][0]["ECM"]["c"]["CM"]["i"] == 3
            assert ret["some_callResponse"]['some_callResult'][0]["ECM"]["c"]["CM"]["s"] in ("3x", b"3x")
            assert ret["some_callResponse"]['some_callResult'][0]["ECM"]["i"] == 4
            assert ret["some_callResponse"]['some_callResult'][0]["ECM"]["s"] in ("4x", b"4x")
            assert ret["some_callResponse"]['some_callResult'][0]["ECM"]["d"] == "2011-12-13T14:15:16+00:00"

        def test_invalid_request(self):
            class SomeService(Service):
                @srpc(Integer, String, DateTime)
                def yay(i,s,d):
                    print(i,s,d)

            ctx = _dry_me([SomeService], {"some_call": {"yay": []}},
                                                            just_in_object=True)

            print(ctx.in_error)
            assert ctx.in_error.faultcode == 'Client.ResourceNotFound'

        def test_invalid_string(self):
            class SomeService(Service):
                @srpc(Integer, String, DateTime)
                def yay(i,s,d):
                    print(i, s, d)

            ctx = _dry_me([SomeService], {"yay": {"s": 1}}, validator='soft',
                                                            just_in_object=True)

            assert ctx.in_error.faultcode == 'Client.ValidationError'

        def test_invalid_number(self):
            class SomeService(Service):
                @srpc(Integer, String, DateTime)
                def yay(i,s,d):
                    print(i,s,d)

            ctx = _dry_me([SomeService], {"yay": ["s", "B"]}, validator='soft',
                                                            just_in_object=True)

            assert ctx.in_error.faultcode == 'Client.ValidationError'

        def test_missing_value(self):
            class SomeService(Service):
                @srpc(Integer, Unicode, Mandatory.DateTime)
                def yay(i, s, d):
                    print(i, s, d)

            ctx = _dry_me([SomeService], {"yay": [1, "B"]}, validator='soft',
                                                            just_in_object=True)

            print(ctx.in_error.faultstring)
            assert ctx.in_error.faultcode == 'Client.ValidationError'
            assert ctx.in_error.faultstring.endswith("at least 1 times.")

        def test_invalid_datetime(self):
            class SomeService(Service):
                @srpc(Integer, String, Mandatory.DateTime)
                def yay(i,s,d):
                    print(i,s,d)

            ctx = _dry_me([SomeService],{"yay": {"d":"a2011"}},validator='soft',
                                                            just_in_object=True)

            assert ctx.in_error.faultcode == 'Client.ValidationError'

        def test_fault_to_dict(self):
            class SomeService(Service):
                @srpc(_returns=String)
                def some_call():
                    raise Fault()

            _dry_me([SomeService], {"some_call":[]})

        def test_prune_none_and_optional(self):
            class SomeObject(ComplexModel):
                i = Integer
                s = String(min_occurs=1)

            class SomeService(Service):
                @srpc(_returns=SomeObject)
                def some_call():
                    return SomeObject()

            ctx = _dry_me([SomeService], {"some_call":[]})

            ret = self.loads(b''.join(ctx.out_string))

            assert ret == {"some_callResponse": {'some_callResult':
                                                   {'SomeObject': {'s': None}}}}

        def test_any_xml(self):
            d = lxml.etree.tostring(E('{ns1}x', E('{ns2}Y', "some data")),
                                                             encoding='unicode')

            class SomeService(Service):
                @srpc(AnyXml, _returns=AnyXml)
                def some_call(p):
                    print(p)
                    print(type(p))
                    assert type(p) == lxml.etree._Element
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = self.loads(b''.join(ctx.out_string))
            d = {"some_callResponse": {"some_callResult": d}}
            print(s)
            print(d)
            assert s == d

        def test_any_html(self):
            d = lxml.html.tostring(E('div', E('span', "something")),
                                                             encoding='unicode')

            class SomeService(Service):
                @srpc(AnyHtml, _returns=AnyHtml)
                def some_call(p):
                    print(p)
                    print(type(p))
                    assert type(p) == lxml.html.HtmlElement
                    return p

            ctx = _dry_me([SomeService], {"some_call": [d]})

            s = self.loads(b''.join(ctx.out_string))
            d = {"some_callResponse": {"some_callResult": d}}

            print(s)
            print(d)
            assert s == d

        def test_any_dict(self):
            d = {'helo': 213, 'data': {'nested': [12, 0.3]}}

            class SomeService(Service):
                @srpc(AnyDict, _returns=AnyDict)
                def some_call(p):
                    print(p)
                    print(type(p))
                    assert type(p) == dict
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = b''.join(ctx.out_string)
            d = self.dumps({"some_callResponse": {"some_callResult": d}})

            print(s)
            print(d)
            assert self.loads(s) == self.loads(d)

        def test_unicode(self):
            d = u'some string'

            class SomeService(Service):
                @srpc(Unicode, _returns=Unicode)
                def some_call(p):
                    print(p)
                    print(type(p))
                    assert type(p) == six.text_type
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = self.loads(b''.join(ctx.out_string))
            d = {"some_callResponse": {"some_callResult": d}}
            print(s)
            print(d)
            assert s == d

        def test_any_uri(self):
            d = 'http://example.com/?asd=b12&df=aa#tag'

            class SomeService(Service):
                @srpc(AnyUri, _returns=AnyUri)
                def some_call(p):
                    print(p)
                    print(type(p))
                    assert isinstance(p, six.string_types)
                    return p

            ctx = _dry_me([SomeService], {"some_call": [d]})

            s = self.loads(b''.join(ctx.out_string))
            d = {"some_callResponse": {"some_callResult": d}}
            print(s)
            print(d)
            assert s == d

        def test_image_uri(self):
            d = 'http://example.com/funny.gif'

            class SomeService(Service):
                @srpc(ImageUri, _returns=ImageUri)
                def some_call(p):
                    print(p)
                    print(type(p))
                    assert isinstance(p, six.string_types)
                    return p

            ctx = _dry_me([SomeService], {"some_call": [d]})

            s = self.loads(b''.join(ctx.out_string))
            d = {"some_callResponse": {"some_callResult": d}}
            print(s)
            print(d)
            assert s == d

        def test_decimal(self):
            d = decimal.Decimal('1e100')
            if _DictDocumentChild._decimal_as_string:
                d = str(d)

            class SomeService(Service):
                @srpc(Decimal, _returns=Decimal)
                def some_call(p):
                    print(p)
                    print(type(p))
                    assert type(p) == decimal.Decimal
                    return p

            ctx = _dry_me([SomeService], {"some_call": [d]})

            s = self.loads(b''.join(ctx.out_string))
            d = {"some_callResponse": {"some_callResult": d}}
            print(s)
            print(d)
            assert s == d

        def test_double(self):
            d = 12.3467

            class SomeService(Service):
                @srpc(Double, _returns=Double)
                def some_call(p):
                    print(p)
                    print(type(p))
                    assert type(p) == float
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = self.loads(b''.join(ctx.out_string))
            d = {"some_callResponse": {"some_callResult": d}}
            print(s)
            print(d)
            assert s == d

        def test_integer(self):
            d = 5

            class SomeService(Service):
                @srpc(Integer, _returns=Integer)
                def some_call(p):
                    print(p)
                    print(type(p))
                    assert type(p) == int
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = self.loads(b''.join(ctx.out_string))
            d = {"some_callResponse": {"some_callResult": d}}
            print(s)
            print(d)
            assert s == d

        def test_integer_way_small(self):
            d = -1<<1000
            if _DictDocumentChild._huge_numbers_as_string:
                d = str(d)

            class SomeService(Service):
                @srpc(Integer, _returns=Integer)
                def some_call(p):
                    print(p)
                    print(type(p))
                    assert type(p) == long
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = self.loads(b''.join(ctx.out_string))
            d = {"some_callResponse": {"some_callResult": d}}

            print(s)
            print(d)
            assert s == d

        def test_integer_way_big(self):
            d = 1<<1000
            if _DictDocumentChild._huge_numbers_as_string:
                d = str(d)

            class SomeService(Service):
                @srpc(Integer, _returns=Integer)
                def some_call(p):
                    print(p)
                    print(type(p))
                    assert type(p) == long
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = self.loads(b''.join(ctx.out_string))
            d = {"some_callResponse": {"some_callResult": d}}
            print(s)
            print(d)
            assert s == d

        def test_time(self):
            d = time(10, 20, 30).isoformat()

            class SomeService(Service):
                @srpc(Time, _returns=Time)
                def some_call(p):
                    print(p)
                    print(type(p))
                    assert type(p) == time
                    assert p.isoformat() == d
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = self.loads(b''.join(ctx.out_string))
            d = {"some_callResponse": {"some_callResult": d}}
            print(s)
            print(d)
            assert s == d

        def test_date(self):
            vdt = datetime(2010, 9, 8)
            d = vdt.date().isoformat()

            class SomeService(Service):
                @srpc(Date, _returns=Date)
                def some_call(p):
                    print(p)
                    print(type(p))
                    assert type(p) == date
                    assert p.isoformat() == d
                    return p

                @srpc(_returns=Date)
                def some_call_dt():
                    return vdt

            ctx = _dry_me([SomeService], {"some_call": [d]})
            s = self.loads(b''.join(ctx.out_string))
            rd = {"some_callResponse": {"some_callResult": d}}
            print(s)
            print(rd)
            assert s == rd

            ctx = _dry_me([SomeService], {"some_call_dt": []})
            s = self.loads(b''.join(ctx.out_string))
            rd = {"some_call_dtResponse": {"some_call_dtResult": d}}
            print(s)
            print(rd)
            assert s == rd

        def test_datetime(self):
            d = datetime(2010, 9, 8, 7, 6, 5).isoformat()

            class SomeService(Service):
                @srpc(DateTime, _returns=DateTime(timezone=False))
                def some_call(p):
                    print(p)
                    print(type(p))
                    assert type(p) == datetime
                    assert p.replace(tzinfo=None).isoformat() == d
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]}, validator='soft')

            s = self.loads(b''.join(ctx.out_string))
            d = {"some_callResponse": {"some_callResult": d}}
            print(s)
            print(d)
            assert s == d

        def test_datetime_tz(self):
            d = datetime(2010, 9, 8, 7, 6, 5, tzinfo=pytz.utc).isoformat()

            class SomeService(Service):
                @srpc(DateTime, _returns=DateTime(ge=datetime(2010,1,1,tzinfo=pytz.utc)))
                def some_call(p):
                    print(p)
                    print(type(p))
                    assert type(p) == datetime
                    assert p.isoformat() == d
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]}, validator='soft')

            s = self.loads(b''.join(ctx.out_string))
            d = {"some_callResponse": {"some_callResult": d}}
            print(s)
            print(d)
            assert s == d

        def test_duration(self):
            d = ProtocolBase().to_unicode(Duration, timedelta(0, 45))

            class SomeService(Service):
                @srpc(Duration, _returns=Duration)
                def some_call(p):
                    print(p)
                    print(type(p))
                    assert type(p) == timedelta
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = self.loads(b''.join(ctx.out_string))
            d = {"some_callResponse": {"some_callResult": d}}
            print(s)
            print(d)
            assert s == d

        def test_boolean(self):
            d = True

            class SomeService(Service):
                @srpc(Boolean, _returns=Boolean)
                def some_call(p):
                    print(p)
                    print(type(p))
                    assert type(p) == bool
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = self.loads(b''.join(ctx.out_string))
            d = {"some_callResponse": {"some_callResult": d}}
            print(s)
            print(d)
            assert s == d

        def test_uuid(self):
            d = '7d2a6330-eb64-4900-8a10-38ebef415e9d'

            class SomeService(Service):
                @srpc(Uuid, _returns=Uuid)
                def some_call(p):
                    print(p)
                    print(type(p))
                    assert type(p) == uuid.UUID
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = self.loads(b''.join(ctx.out_string))
            d = {"some_callResponse": {"some_callResult": d}}
            print(s)
            print(d)
            assert s == d

        def test_point2d(self):
            d = 'POINT(1 2)'

            class SomeService(Service):
                @srpc(Point, _returns=Point)
                def some_call(p):
                    print(p)
                    print(type(p))
                    assert isinstance(p, six.string_types)
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = self.loads(b''.join(ctx.out_string))
            d = {"some_callResponse": {"some_callResult": d}}
            print(s)
            print(d)
            assert s == d

        def test_point3d(self):
            d = 'POINT(1 2 3)'

            class SomeService(Service):
                @srpc(Point, _returns=Point)
                def some_call(p):
                    print(p)
                    print(type(p))
                    assert isinstance(p, six.string_types)
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = self.loads(b''.join(ctx.out_string))
            d = {"some_callResponse": {"some_callResult": d}}
            print(s)
            print(d)
            assert s == d

        def test_line2d(self):
            d = 'LINESTRING(1 2, 3 4)'

            class SomeService(Service):
                @srpc(Line, _returns=Line)
                def some_call(p):
                    print(p)
                    print(type(p))
                    assert isinstance(p, six.string_types)
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = self.loads(b''.join(ctx.out_string))
            d = {"some_callResponse": {"some_callResult": d}}
            print(s)
            print(d)
            assert s == d

        def test_line3d(self):
            d = 'LINESTRING(1 2 3, 4 5 6)'

            class SomeService(Service):
                @srpc(Line, _returns=Line)
                def some_call(p):
                    print(p)
                    print(type(p))
                    assert isinstance(p, six.string_types)
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = self.loads(b''.join(ctx.out_string))
            d = {"some_callResponse": {"some_callResult": d}}
            print(s)
            print(d)
            assert s == d

        def test_polygon2d(self):
            d = 'POLYGON((1 1, 1 2, 2 2, 2 1, 1 1))'

            class SomeService(Service):
                @srpc(Polygon(2), _returns=Polygon(2))
                def some_call(p):
                    print(p)
                    print(type(p))
                    assert isinstance(p, six.string_types)
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = self.loads(b''.join(ctx.out_string))
            d = {"some_callResponse": {"some_callResult": d}}
            print(s)
            print(d)
            assert s == d

        def test_polygon3d(self):
            d = 'POLYGON((1 1 0, 1 2 0, 2 2 0, 2 1 0, 1 1 0))'

            class SomeService(Service):
                @srpc(Polygon(3), _returns=Polygon(3))
                def some_call(p):
                    print(p)
                    print(type(p))
                    assert isinstance(p, six.string_types)
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = self.loads(b''.join(ctx.out_string))
            d = {"some_callResponse": {"some_callResult": d}}
            print(s)
            print(d)
            assert s == d

        def test_multipoint2d(self):
            d = 'MULTIPOINT ((10 40), (40 30), (20 20), (30 10))'

            class SomeService(Service):
                @srpc(MultiPoint(2), _returns=MultiPoint(2))
                def some_call(p):
                    print(p)
                    print(type(p))
                    assert isinstance(p, six.string_types)
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = self.loads(b''.join(ctx.out_string))
            d = {"some_callResponse": {"some_callResult": d}}
            print(s)
            print(d)
            assert s == d

        def test_multipoint3d(self):
            d = 'MULTIPOINT (10 40 30, 40 30 10,)'

            class SomeService(Service):
                @srpc(MultiPoint(3), _returns=MultiPoint(3))
                def some_call(p):
                    print(p)
                    print(type(p))
                    assert isinstance(p, six.string_types)
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = self.loads(b''.join(ctx.out_string))
            d = {"some_callResponse": {"some_callResult": d}}
            print(s)
            print(d)
            assert s == d

        def test_multiline2d(self):
            d = 'MULTILINESTRING ((10 10, 20 20, 10 40), (40 40, 30 30, 40 20, 30 10))'

            class SomeService(Service):
                @srpc(MultiLine(2), _returns=MultiLine(2))
                def some_call(p):
                    print(p)
                    print(type(p))
                    assert isinstance(p, six.string_types)
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = self.loads(b''.join(ctx.out_string))
            d = {"some_callResponse": {"some_callResult": d}}
            print(s)
            print(d)
            assert s == d

        def test_multiline3d(self):
            d = 'MULTILINESTRING ((10 10, 20 20, 10 40), (40 40, 30 30, 40 20, 30 10))'

            class SomeService(Service):
                @srpc(MultiLine(3), _returns=MultiLine(3))
                def some_call(p):
                    print(p)
                    print(type(p))
                    assert isinstance(p, six.string_types)
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = self.loads(b''.join(ctx.out_string))
            d = {"some_callResponse": {"some_callResult": d}}
            print(s)
            print(d)
            assert s == d

        def test_multipolygon2d(self):
            d = 'MULTIPOLYGON (((30 20, 10 40, 45 40, 30 20)),((15 5, 40 10, 10 20, 5 10, 15 5)))'

            class SomeService(Service):
                @srpc(MultiPolygon(2), _returns=MultiPolygon(2))
                def some_call(p):
                    print(p)
                    print(type(p))
                    assert isinstance(p, six.string_types)
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = self.loads(b''.join(ctx.out_string))
            d = {"some_callResponse": {"some_callResult": d}}
            print(s)
            print(d)
            assert s == d

        def test_multipolygon3d(self):
            d = 'MULTIPOLYGON (((40 40, 20 45, 45 30, 40 40)),' \
                              '((20 35, 45 20, 30 5, 10 10, 10 30, 20 35),' \
                               '(30 20, 20 25, 20 15, 30 20)))'

            class SomeService(Service):
                @srpc(MultiPolygon(3), _returns=MultiPolygon(3))
                def some_call(p):
                    print(p)
                    print(type(p))
                    assert isinstance(p, six.string_types)
                    return p

            ctx = _dry_me([SomeService], {"some_call":[d]})

            s = self.loads(b''.join(ctx.out_string))
            d = {"some_callResponse": {"some_callResult": d}}
            print(s)
            print(d)
            assert s == d

        def test_generator(self):
            class SomeService(Service):
                @srpc(_returns=Iterable(Integer))
                def some_call():
                    return iter(range(1000))

            ctx = _dry_me([SomeService], {"some_call":[]})

            s = self.loads(b''.join(ctx.out_string))
            d = {"some_callResponse": {"some_callResult": tuple(range(1000))}}
            print(s)
            print(d)
            assert s == d

        def test_bytearray(self):
            dbe = _DictDocumentChild.default_binary_encoding
            beh = binary_encoding_handlers[dbe]

            data = bytes(bytearray(range(0xff)))
            encoded_data = beh([data])
            if _DictDocumentChild.text_based:
                encoded_data = encoded_data.decode('latin1')

            class SomeService(Service):
                @srpc(ByteArray, _returns=ByteArray)
                def some_call(ba):
                    print(ba)
                    print(type(ba))
                    assert isinstance(ba, tuple)
                    assert ba == (data,)
                    return ba

            ctx = _dry_me([SomeService], {"some_call": [encoded_data]})

            s = self.loads(b''.join(ctx.out_string))
            d = {"some_callResponse": {"some_callResult": encoded_data}}

            print(repr(s))
            print(repr(d))
            print(repr(encoded_data))
            assert s == d

        def test_file_data(self):
            # the only difference with the bytearray test is/are the types
            # inside @srpc
            dbe = _DictDocumentChild.default_binary_encoding
            beh = binary_encoding_handlers[dbe]

            data = bytes(bytearray(range(0xff)))
            encoded_data = beh([data])
            if _DictDocumentChild.text_based:
                encoded_data = encoded_data.decode('latin1')

            class SomeService(Service):
                @srpc(File, _returns=File)
                def some_call(p):
                    print(p)
                    print(type(p))
                    assert isinstance(p, File.Value)
                    assert p.data == (data,)
                    return p.data

            # we put the encoded data in the list of arguments.
            ctx = _dry_me([SomeService], {"some_call": [encoded_data]})

            s = self.loads(b''.join(ctx.out_string))
            d = {"some_callResponse": {"some_callResult": encoded_data}}

            print(s)
            print(d)
            print(repr(encoded_data))
            assert s == d

        def test_file_value(self):
            dbe = _DictDocumentChild.default_binary_encoding
            beh = binary_encoding_handlers[dbe]

            # Prepare data
            v = File.Value(
                name='some_file.bin',
                type='application/octet-stream',
            )
            file_data = bytes(bytearray(range(0xff)))
            v.data = (file_data,)
            beh([file_data])
            if _DictDocumentChild.text_based:
                test_data = beh(v.data).decode('latin1')
            else:
                test_data = beh(v.data)

            print(repr(v.data))

            class SomeService(Service):
                @srpc(File, _returns=File)
                def some_call(p):
                    print(p)
                    print(type(p))
                    assert isinstance(p, File.Value)
                    assert p.data == (file_data,)
                    assert p.type == v.type
                    assert p.name == v.name
                    return p

            d = get_object_as_dict(v, File, protocol=_DictDocumentChild,
                                                          ignore_wrappers=False)
            ctx = _dry_me([SomeService], {"some_call": {'p': d}})
            s = b''.join(ctx.out_string)
            d = self.dumps({"some_callResponse": {"some_callResult": {
                'name': v.name,
                'type': v.type,
                'data': test_data,
            }}})

            print(self.loads(s))
            print(self.loads(d))
            print(v)
            assert self.loads(s) == self.loads(d)

        def test_ignored(self):
            class SomeService(Service):
                @srpc(Unicode, _returns=Unicode)
                def some_call(p):
                    print(p)
                    print(type(p))
                    assert isinstance(p, six.string_types)
                    return Ignored("aaa", b=1, c=2)

            ctx = _dry_me([SomeService], {"some_call": ["some string"]})

            s = self.loads(b''.join(ctx.out_string))
            d = {"some_callResponse": {}}
            assert s == d

        def test_validation_frequency(self):
            class SomeService(Service):
                @srpc(ByteArray(min_occurs=1), _returns=ByteArray)
                def some_call(p):
                    pass

            try:
                _dry_me([SomeService], {"some_call": []}, validator='soft')
            except ValidationError:
                pass
            else:
                raise Exception("must raise ValidationError")

        def test_validation_nullable(self):
            class SomeService(Service):
                @srpc(ByteArray(nullable=False), _returns=ByteArray)
                def some_call(p):
                    pass

            try:
                _dry_me([SomeService], {"some_call": [None]},
                                                            validator='soft')
            except ValidationError:
                pass

            else:
                raise Exception("must raise ValidationError")

        def test_validation_string_pattern(self):
            class SomeService(Service):
                @srpc(Uuid)
                def some_call(p):
                    pass

            try:
                _dry_me([SomeService], {"some_call": ["duduk"]},
                                                               validator='soft')
            except ValidationError as e:
                print(e)
                pass

            else:
                raise Exception("must raise ValidationError")

        def test_validation_integer_range(self):
            class SomeService(Service):
                @srpc(Integer(ge=0, le=5))
                def some_call(p):
                    pass

            try:
                _dry_me([SomeService], {"some_call": [10]},
                                                            validator='soft')
            except ValidationError:
                pass

            else:
                raise Exception("must raise ValidationError")

        def test_validation_integer_type(self):
            class SomeService(Service):
                @srpc(Integer8)
                def some_call(p):
                    pass

            try:
                _dry_me([SomeService], {"some_call": [-129]},
                                                            validator='soft')
            except ValidationError:
                pass

            else:
                raise Exception("must raise ValidationError")

        def test_validation_integer_type_2(self):
            class SomeService(Service):
                @srpc(Integer8)
                def some_call(p):
                    pass

            try:
                _dry_me([SomeService], {"some_call": [1.2]}, validator='soft')

            except ValidationError:
                pass

            else:
                raise Exception("must raise ValidationError")

        def test_not_wrapped(self):
            class SomeInnerClass(ComplexModel):
                d = date
                dt = datetime

            class SomeClass(ComplexModel):
                a = int
                b = Unicode
                c = SomeInnerClass.customize(not_wrapped=True)

            class SomeService(Service):
                @srpc(SomeClass.customize(not_wrapped=True),
                      _returns=SomeClass.customize(not_wrapped=True))
                def some_call(p):
                    assert p.a == 1
                    assert p.b == 's'
                    assert p.c.d == date(2018, 11, 22)
                    return p

            inner = {"a": 1, "b": "s", "c": {"d": '2018-11-22'}}
            doc = {"some_call": [inner]}
            ctx = _dry_me([SomeService], doc, validator='soft')

            print(ctx.out_document)

            d = convert_dict({"some_callResponse": {"some_callResult": inner}})
            self.assertEquals(ctx.out_document[0], d)

        def test_validation_freq_parent(self):
            class C(ComplexModel):
                i = Integer(min_occurs=1)
                s = Unicode

            class SomeService(Service):
                @srpc(C)
                def some_call(p):
                    pass

            try:
                # must raise validation error for missing i
                _dry_me([SomeService], {"some_call": {'p': {'C': {'s': 'a'}}}},
                                                               validator='soft')
            except ValidationError as e:
                logger.exception(e)
                pass
            except BaseException as e:
                logger.exception(e)
                pass
            else:
                raise Exception("must raise ValidationError")

            # must not raise anything for missing p because C has min_occurs=0
            _dry_me([SomeService], {"some_call": {}}, validator='soft')

        def test_inheritance(self):
            class P(ComplexModel):
                identifier = Uuid
                signature = Unicode

            class C(P):
                foo = Unicode
                bar = Uuid

            class SomeService(Service):
                @rpc(_returns=C)
                def some_call(ctx):
                    result = C()
                    result.identifier = uuid.UUID(int=0)
                    result.signature = 'yyyyyyyyyyy'
                    result.foo = 'zzzzzz'
                    result.bar = uuid.UUID(int=1)
                    return result

            ctx = _dry_me([SomeService], {"some_call": []})

            s = self.loads(b''.join(ctx.out_string))
            d = {"some_callResponse": {"some_callResult": {"C": {
                    'identifier': '00000000-0000-0000-0000-000000000000',
                    'bar': '00000000-0000-0000-0000-000000000001',
                    'foo': 'zzzzzz',
                    'signature': 'yyyyyyyyyyy'
                }}}}

            assert s == d

        def test_exclude(self):
            class C(ComplexModel):
                s1 = Unicode(exc=True)
                s2 = Unicode

            class SomeService(Service):
                @srpc(C, _returns=C)
                def some_call(sc):
                    assert sc.s1 is None, "sc={}".format(sc)
                    assert sc.s2 == "s2"
                    return C(s1="s1", s2="s2")

            doc = [{"C": {"s1": "s1","s2": "s2"}}]
            ctx = _dry_me([SomeService], {"some_call": doc})

            self.assertEquals(ctx.out_document[0], convert_dict(
                {'some_callResponse': {'some_callResult': {'C': {'s2': 's2'}}}})
            )

        def test_polymorphic_deserialization(self):
            class P(ComplexModel):
                sig = Unicode

            class C(P):
                foo = Unicode

            class D(P):
                bar = Integer

            class SomeService(Service):
                @rpc(P, _returns=Unicode)
                def typeof(ctx, p):
                    return type(p).__name__

            ctx = _dry_me([SomeService],
                            {"typeof": [{'C':{'sig':'a', 'foo': 'f'}}]},
                                                               polymorphic=True)

            s = self.loads(b''.join(ctx.out_string))
            d = {"typeofResponse": {"typeofResult": 'C'}}

            print(s)
            print(d)
            assert s == d

            ctx = _dry_me([SomeService],
                                  {"typeof": [{'D':{'sig':'b', 'bar': 5}}]},
                                                               polymorphic=True)

            s = self.loads(b''.join(ctx.out_string))
            d = {"typeofResponse": {"typeofResult": 'D'}}

            print(s)
            print(d)
            assert s == d

        def test_default(self):
            class SomeComplexModel(ComplexModel):
                _type_info = [
                    ('a', Unicode),
                    ('b', Unicode(default='default')),
                ]

            class SomeService(Service):
                @srpc(SomeComplexModel)
                def some_method(s):
                    pass

            ctx = _dry_me([SomeService],
                            {"some_method": [{"s": {"a": "x", "b": None}}]},
                                                               polymorphic=True)

            assert ctx.in_object.s.b == None
            assert ctx.in_error is None

            ctx = _dry_me([SomeService], {"some_method": {"s": {"a": "x"}}},
                                                               polymorphic=True)

            assert ctx.in_object.s.b == 'default'
            assert ctx.in_error is None

        def test_nillable_default(self):
            class SomeComplexModel(ComplexModel):
                _type_info = [
                    ('a', Unicode),
                    ('b', Unicode(min_occurs=1, default='default', nillable=True)),
                ]

            class SomeService(Service):
                @srpc(SomeComplexModel)
                def some_method(s):
                    pass

            ctx = _dry_me([SomeService],
                            {"some_method": [{"s": {"a": "x", "b": None}}]},
                                           polymorphic=True, validator='soft')

            assert ctx.in_object.s.b == None
            assert ctx.in_error is None

            ctx = _dry_me([SomeService], {"some_method": {"s": {"a": "x"}}},
                                                               polymorphic=True)

            assert ctx.in_object.s.b == 'default'
            assert ctx.in_error is None

    return Test
