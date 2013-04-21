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

import logging
logging.basicConfig(level=logging.DEBUG)

import unittest
import decimal

from decimal import Decimal

from spyne import MethodContext
from spyne.application import Application
from spyne.decorator import srpc
from spyne.model.complex import Array
from spyne.model.complex import ComplexModel
from spyne.model.complex import Iterable
from spyne.model.fault import Fault
from spyne.model.primitive import Decimal
from spyne.model.primitive import Integer
from spyne.model.primitive import String
from spyne.model.primitive import DateTime
from spyne.model.primitive import Mandatory
from spyne.service import ServiceBase
from spyne.server import ServerBase


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
        def test_decimal_return(self):
            decimal.getcontext().prec=200
            d = decimal.Decimal('1e100')
            class SomeService(ServiceBase):
                @srpc(_returns=Decimal)
                def some_call():
                    return d+1

            ctx = _dry_me([SomeService], {"some_call":[]})

            out_strings = list(ctx.out_string)
            print out_strings
            assert out_strings == [serializer.dumps(
                 {"some_callResponse": {"some_callResult": int(d)+1}}, **dumps_kwargs)]

        def test_primitive_only(self):
            class SomeComplexModel(ComplexModel):
                i = Integer
                s = String

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
                s = String

            class CCM(ComplexModel):
                c = CM
                i = Integer
                s = String

            class SomeService(ServiceBase):
                @srpc(CCM, _returns=CCM)
                def some_call(ccm):
                    return CCM(c=ccm.c, i=ccm.i, s=ccm.s)

            ctx = _dry_me([SomeService], {"some_call":
                    {"ccm": {"c":{"i":3, "s": "3x"}, "i":4, "s": "4x"}}
                })

            ret = serializer.loads(''.join(ctx.out_string))

            print(ret)

            assert ret['some_callResponse']['some_callResult']['CCM']['i'] == 4
            assert ret['some_callResponse']['some_callResult']['CCM']['s'] == '4x'
            assert ret['some_callResponse']['some_callResult']['CCM']['c']['CM']['i'] == 3
            assert ret['some_callResponse']['some_callResult']['CCM']['c']['CM']['s'] == '3x'

        def test_multiple_list(self):
            class SomeService(ServiceBase):
                @srpc(String(max_occurs=Decimal('inf')),
                                     _returns=String(max_occurs=Decimal('inf')))
                def some_call(s):
                    return s

            ctx = _dry_me([SomeService], {"some_call":[["a","b"]]})

            assert list(ctx.out_string) == [serializer.dumps(
                         {"some_callResponse": {"some_callResult": ["a", "b"]}}, **dumps_kwargs)]

        def test_multiple_dict(self):
            class SomeService(ServiceBase):
                @srpc(String(max_occurs=Decimal('inf')),
                                     _returns=String(max_occurs=Decimal('inf')))
                def some_call(s):
                    return s

            ctx = _dry_me([SomeService], {"some_call":{"s":["a","b"]}})

            assert ''.join(ctx.out_string) == serializer.dumps(
                         {"some_callResponse": {"some_callResult": ["a", "b"]}},
                        **dumps_kwargs)

        def test_multiple_dict_array(self):
            class SomeService(ServiceBase):
                @srpc(Iterable(String), _returns=Iterable(String))
                def some_call(s):
                    return s

            ctx = _dry_me([SomeService], {"some_call":{"s":["a","b"]}})

            assert list(ctx.out_string) == [serializer.dumps(
                 {"some_callResponse": {"some_callResult": ["a", "b"]}}, **dumps_kwargs)]

        def test_multiple_dict_complex_array(self):
            class CM(ComplexModel):
                i = Integer
                s = String

            class CCM(ComplexModel):
                c = CM
                i = Integer
                s = String

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
                    print(i,s,d)

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
                @srpc(Integer, String, Mandatory.DateTime)
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

    return Test
