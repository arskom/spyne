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

from spyne.util.six import StringIO
from spyne.util.six.moves.http_cookies import SimpleCookie

from datetime import datetime
from wsgiref.validate import validator as wsgiref_validator

from spyne.model.complex import Array

from spyne.server.wsgi import _parse_qs
from spyne.application import Application
from spyne.error import ValidationError
from spyne.const.http import HTTP_200
from spyne.decorator import rpc
from spyne.decorator import srpc
from spyne.model.binary import ByteArray
from spyne.model.primitive import DateTime
from spyne.model.primitive import Uuid
from spyne.model.primitive import String
from spyne.model.primitive import Integer
from spyne.model.primitive import Integer8
from spyne.model.complex import ComplexModel
from spyne.protocol.http import HttpRpc
from spyne.protocol.http import HttpPattern
from spyne.service import ServiceBase
from spyne.server.wsgi import WsgiApplication
from spyne.server.wsgi import WsgiMethodContext
from spyne.util.test import call_wsgi_app_kwargs



class TestString(unittest.TestCase):
    def setUp(self):
        class SomeService(ServiceBase):
            @srpc(String, _returns=String)
            def echo_string(s):
                return s

        app = Application([SomeService], 'tns',
                in_protocol=HttpRpc(validator='soft'),
                out_protocol=HttpRpc(),
            )

        self.app = WsgiApplication(app)

    def test_without_content_type(self):
        headers = None
        ret = call_wsgi_app_kwargs(self.app, 'echo_string', headers, s="string")
        assert ret == 'string'

    def test_without_encoding(self):
        headers = {'CONTENT_TYPE':'text/plain'}
        ret = call_wsgi_app_kwargs(self.app, 'echo_string', headers, s="string")
        assert ret == 'string'

    def test_with_encoding(self):
        headers = {'CONTENT_TYPE':'text/plain; charset=utf8'}
        ret = call_wsgi_app_kwargs(self.app, 'echo_string', headers, s="string")
        assert ret == 'string'


class TestSimpleDictDocument(unittest.TestCase):
    def test_own_parse_qs_01(self):
        assert dict(_parse_qs('')) == {}
    def test_own_parse_qs_02(self):
        assert dict(_parse_qs('p')) == {'p': [None]}
    def test_own_parse_qs_03(self):
        assert dict(_parse_qs('p=')) == {'p': ['']}
    def test_own_parse_qs_04(self):
        assert dict(_parse_qs('p=1')) == {'p': ['1']}
    def test_own_parse_qs_05(self):
        assert dict(_parse_qs('p=1&')) == {'p': ['1']}
    def test_own_parse_qs_06(self):
        assert dict(_parse_qs('p=1&q')) == {'p': ['1'], 'q': [None]}
    def test_own_parse_qs_07(self):
        assert dict(_parse_qs('p=1&q=')) == {'p': ['1'], 'q': ['']}
    def test_own_parse_qs_08(self):
        assert dict(_parse_qs('p=1&q=2')) == {'p': ['1'], 'q': ['2']}
    def test_own_parse_qs_09(self):
        assert dict(_parse_qs('p=1&q=2&p')) == {'p': ['1', None], 'q': ['2']}
    def test_own_parse_qs_10(self):
        assert dict(_parse_qs('p=1&q=2&p=')) == {'p': ['1', ''], 'q': ['2']}
    def test_own_parse_qs_11(self):
        assert dict(_parse_qs('p=1&q=2&p=3')) == {'p': ['1', '3'], 'q': ['2']}

def _test(services, qs, validator='soft', strict_arrays=False):
    app = Application(services, 'tns',
          in_protocol=HttpRpc(validator=validator, strict_arrays=strict_arrays),
          out_protocol=HttpRpc())
    server = WsgiApplication(app)

    initial_ctx = WsgiMethodContext(server, {
        'QUERY_STRING': qs,
        'PATH_INFO': '/some_call',
        'REQUEST_METHOD': 'GET',
        'SERVER_NAME': "localhost",
    }, 'some-content-type')

    ctx, = server.generate_contexts(initial_ctx)

    server.get_in_object(ctx)
    if ctx.in_error is not None:
        raise ctx.in_error

    server.get_out_object(ctx)
    if ctx.out_error is not None:
        raise ctx.out_error

    server.get_out_string(ctx)

    return ctx

class TestValidation(unittest.TestCase):
    def test_validation_frequency(self):
        class SomeService(ServiceBase):
            @srpc(ByteArray(min_occurs=1), _returns=ByteArray)
            def some_call(p):
                pass

        try:
            _test([SomeService], '', validator='soft')
        except ValidationError:
            pass
        else:
            raise Exception("must raise ValidationError")

    def _test_validation_frequency_simple_bare(self):
        class SomeService(ServiceBase):
            @srpc(ByteArray(min_occurs=1), _body_style='bare', _returns=ByteArray)
            def some_call(p):
                pass

        try:
            _test([SomeService], '', validator='soft')
        except ValidationError:
            pass
        else:
            raise Exception("must raise ValidationError")

    def test_validation_frequency_complex_bare_parent(self):
        class C(ComplexModel):
            i=Integer(min_occurs=1)
            s=String

        class SomeService(ServiceBase):
            @srpc(C, _body_style='bare')
            def some_call(p):
                pass

        # must not complain about missing s
        _test([SomeService], 'i=5', validator='soft')

        # must raise validation error for missing i
        try:
            _test([SomeService], 's=a', validator='soft')
        except ValidationError:
            pass
        else:
            raise Exception("must raise ValidationError")

        # must raise validation error for missing i
        try:
            _test([SomeService], '', validator='soft')
        except ValidationError:
            pass
        else:
            raise Exception("must raise ValidationError")

    def test_validation_frequency_parent(self):
        class C(ComplexModel):
            i=Integer(min_occurs=1)
            s=String

        class SomeService(ServiceBase):
            @srpc(C)
            def some_call(p):
                pass

        # must not complain about missing s
        _test([SomeService], 'p.i=5', validator='soft')
        try:
            # must raise validation error for missing i
            _test([SomeService], 'p.s=a', validator='soft')
        except ValidationError:
            pass
        else:
            raise Exception("must raise ValidationError")

        # must not raise anything for missing p because C has min_occurs=0
        _test([SomeService], '', validator='soft')

    def test_validation_array(self):
        class C(ComplexModel):
            i=Integer(min_occurs=1)
            s=String

        class SomeService(ServiceBase):
            @srpc(Array(C))
            def some_call(p):
                pass

        # must not complain about missing s
        _test([SomeService], 'p[0].i=5', validator='soft')
        try:
            # must raise validation error for missing i
            _test([SomeService], 'p[0].s=a', validator='soft')
        except ValidationError:
            pass
        else:
            raise Exception("must raise ValidationError")

        # must not raise anything for missing p because C has min_occurs=0
        _test([SomeService], '', validator='soft')

    def test_validation_array_index_jump_error(self):
        class C(ComplexModel):
            i=Integer

        class SomeService(ServiceBase):
            @srpc(Array(C), _returns=String)
            def some_call(p):
                return repr(p)

        try:
            # must raise validation error for index jump from 0 to 2 even without
            # any validation
            _test([SomeService], 'p[0].i=42&p[2].i=42&', strict_arrays=True)
        except ValidationError:
            pass
        else:
            raise Exception("must raise ValidationError")

    def test_validation_array_index_jump_tolerate(self):
        class C(ComplexModel):
            i=Integer

        class SomeService(ServiceBase):
            @srpc(Array(C), _returns=String)
            def some_call(p):
                return repr(p)

        # must not raise validation error for index jump from 0 to 2 and ignore
        # element with index 1
        ret = _test([SomeService], 'p[0].i=0&p[2].i=2&', strict_arrays=False)
        assert ret.out_object[0] == '[C(i=0), C(i=2)]'

        # even if they arrive out-of-order.
        ret = _test([SomeService], 'p[2].i=2&p[0].i=0&', strict_arrays=False)
        assert ret.out_object[0] == '[C(i=0), C(i=2)]'

    def test_validation_nested_array(self):
        class CC(ComplexModel):
            d = DateTime

        class C(ComplexModel):
            i = Integer(min_occurs=1)
            cc = Array(CC)

        class SomeService(ServiceBase):
            @srpc(Array(C))
            def some_call(p):
                print(p)

        # must not complain about missing s
        _test([SomeService], 'p[0].i=5', validator='soft')
        try:
            # must raise validation error for missing i
            _test([SomeService], 'p[0].cc[0].d=2013-01-01', validator='soft')
        except ValidationError:
            pass
        else:
            raise Exception("must raise ValidationError")

        # must not raise anything for missing p because C has min_occurs=0
        _test([SomeService], '', validator='soft')

    def test_validation_nullable(self):
        class SomeService(ServiceBase):
            @srpc(ByteArray(nullable=False), _returns=ByteArray)
            def some_call(p):
                pass

        try:
            _test([SomeService], 'p', validator='soft')
        except ValidationError:
            pass
        else:
            raise Exception("must raise ValidationError")

    def test_validation_string_pattern(self):
        class SomeService(ServiceBase):
            @srpc(Uuid)
            def some_call(p):
                pass

        try:
            _test([SomeService], "p=duduk", validator='soft')
        except ValidationError:
            pass
        else:
            raise Exception("must raise ValidationError")

    def test_validation_integer_range(self):
        class SomeService(ServiceBase):
            @srpc(Integer(ge=0, le=5))
            def some_call(p):
                pass

        try:
            _test([SomeService], 'p=10', validator='soft')
        except ValidationError:
            pass
        else:
            raise Exception("must raise ValidationError")

    def test_validation_integer_type(self):
        class SomeService(ServiceBase):
            @srpc(Integer8)
            def some_call(p):
                pass

        try:
            _test([SomeService], "p=-129", validator='soft')
        except ValidationError:
            pass
        else:
            raise Exception("must raise ValidationError")

    def test_validation_integer_type_2(self):
        class SomeService(ServiceBase):
            @srpc(Integer8)
            def some_call(p):
                pass

        try:
            _test([SomeService], "p=1.2", validator='soft')
        except ValidationError:
            pass
        else:
            raise Exception("must raise ValidationError")


class Test(unittest.TestCase):
    def test_multiple_return(self):
        class SomeService(ServiceBase):
            @srpc(_returns=[Integer, String])
            def some_call():
                return 1, 's'

        try:
            _test([SomeService], '')
        except TypeError:
            pass
        else:
            raise Exception("Must fail with: HttpRpc does not support complex "
                "return types.")

    def test_primitive_only(self):
        class SomeComplexModel(ComplexModel):
            i = Integer
            s = String

        class SomeService(ServiceBase):
            @srpc(SomeComplexModel, _returns=SomeComplexModel)
            def some_call(scm):
                return SomeComplexModel(i=5, s='5x')

        try:
            _test([SomeService], '')
        except TypeError:
            pass
        else:
            raise Exception("Must fail with: HttpRpc does not support complex "
                "return types.")

    def test_complex(self):
        class CM(ComplexModel):
            _type_info = [
                ("i", Integer),
                ("s", String),
            ]

        class CCM(ComplexModel):
            _type_info = [
                ("i", Integer),
                ("c", CM),
                ("s", String),
            ]

        class SomeService(ServiceBase):
            @srpc(CCM, _returns=String)
            def some_call(ccm):
                return repr(CCM(c=ccm.c, i=ccm.i, s=ccm.s))

        ctx = _test([SomeService], '&ccm.i=1&ccm.s=s&ccm.c.i=3&ccm.c.s=cs')

        assert ctx.out_string[0] == "CCM(i=1, c=CM(i=3, s='cs'), s='s')"

    def test_simple_array(self):
        class SomeService(ServiceBase):
            @srpc(String(max_occurs='unbounded'), _returns=String)
            def some_call(s):
                return '\n'.join(s)

        ctx = _test([SomeService], '&s=1&s=2')
        assert ''.join(ctx.out_string) == '1\n2'

    def test_complex_array(self):
        class CM(ComplexModel):
            _type_info = [
                ("i", Integer),
                ("s", String),
            ]

        class SomeService(ServiceBase):
            @srpc(Array(CM), _returns=String)
            def some_call(cs):
                return '\n'.join([repr(c) for c in cs])

        ctx = _test([SomeService],
             'cs[0].i=1&cs[0].s=x'
            '&cs[1].i=2&cs[1].s=y'
            '&cs[2].i=3&cs[2].s=z')

        assert ''.join(ctx.out_string) == \
           "CM(i=1, s='x')\n" \
           "CM(i=2, s='y')\n" \
           "CM(i=3, s='z')"

    def test_complex_array_empty(self):
        class CM(ComplexModel):
            _type_info = [
                ("i", Integer),
                ("s", String),
            ]

        class SomeService(ServiceBase):
            @srpc(Array(CM), _returns=String)
            def some_call(cs):
                return repr(cs)

        ctx = _test([SomeService], 'cs=empty')

        assert ''.join(ctx.out_string) == '[]'

    def test_complex_object_empty(self):
        class CM(ComplexModel):
            _type_info = [
                ("i", Integer),
                ("s", String),
            ]

        class SomeService(ServiceBase):
            @srpc(CM, _returns=String)
            def some_call(c):
                return repr(c)

        ctx = _test([SomeService], 'c=empty')

        assert ''.join(ctx.out_string) == 'CM()'

    def test_nested_flatten(self):
        class CM(ComplexModel):
            _type_info = [
                ("i", Integer),
                ("s", String),
            ]

        class CCM(ComplexModel):
            _type_info = [
                ("i", Integer),
                ("c", CM),
                ("s", String),
            ]

        class SomeService(ServiceBase):
            @srpc(CCM, _returns=String)
            def some_call(ccm):
                return repr(ccm)

        ctx = _test([SomeService], '&ccm.i=1&ccm.s=s&ccm.c.i=3&ccm.c.s=cs')

        print(ctx.out_string)
        assert ''.join(ctx.out_string) == "CCM(i=1, c=CM(i=3, s='cs'), s='s')"

    def test_nested_flatten_with_multiple_values_1(self):
        class CM(ComplexModel):
            _type_info = [
                ("i", Integer),
                ("s", String),
            ]

        class CCM(ComplexModel):
            _type_info = [
                ("i", Integer),
                ("c", CM),
                ("s", String),
            ]

        class SomeService(ServiceBase):
            @srpc(CCM.customize(max_occurs=2), _returns=String)
            def some_call(ccm):
                return repr(ccm)

        ctx = _test([SomeService],  'ccm[0].i=1&ccm[0].s=s'
                                   '&ccm[0].c.i=1&ccm[0].c.s=a'
                                   '&ccm[1].c.i=2&ccm[1].c.s=b')

        s = ''.join(ctx.out_string)

        assert s == "[CCM(i=1, c=CM(i=1, s='a'), s='s'), CCM(c=CM(i=2, s='b'))]"

    def test_nested_flatten_with_multiple_values_2(self):
        class CM(ComplexModel):
            _type_info = [
                ("i", Integer),
                ("s", String),
            ]

        class CCM(ComplexModel):
            _type_info = [
                ("i", Integer),
                ("c", CM.customize(max_occurs=2)),
                ("s", String),
            ]

        class SomeService(ServiceBase):
            @srpc(CCM, _returns=String)
            def some_call(ccm):
                return repr(ccm)

        ctx = _test([SomeService],  'ccm.i=1&ccm.s=s'
                                   '&ccm.c[0].i=1&ccm.c[0].s=a'
                                   '&ccm.c[1].i=2&ccm.c[1].s=b')

        s = ''.join(list(ctx.out_string))
        assert s == "CCM(i=1, c=[CM(i=1, s='a'), CM(i=2, s='b')], s='s')"

    def test_nested_flatten_with_complex_array(self):
        class CM(ComplexModel):
            _type_info = [
                ("i", Integer),
                ("s", String),
            ]

        class CCM(ComplexModel):
            _type_info = [
                ("i", Integer),
                ("c", Array(CM)),
                ("s", String),
            ]

        class SomeService(ServiceBase):
            @srpc(CCM, _returns=String)
            def some_call(ccm):
                return repr(ccm)

        ctx = _test([SomeService],  'ccm.i=1&ccm.s=s'
                                   '&ccm.c[0].i=1&ccm.c[0].s=a'
                                   '&ccm.c[1].i=2&ccm.c[1].s=b')

        s = ''.join(list(ctx.out_string))
        assert s == "CCM(i=1, c=[CM(i=1, s='a'), CM(i=2, s='b')], s='s')"

    def test_nested_2_flatten_with_primitive_array(self):
        class CCM(ComplexModel):
            _type_info = [
                ("i", Integer),
                ("c", Array(String)),
                ("s", String),
            ]

        class SomeService(ServiceBase):
            @srpc(Array(CCM), _returns=String)
            def some_call(ccm):
                return repr(ccm)

        ctx = _test([SomeService],  'ccm[0].i=1&ccm[0].s=s'
                                   '&ccm[0].c=a'
                                   '&ccm[0].c=b')
        s = ''.join(list(ctx.out_string))
        assert s == "[CCM(i=1, c=['a', 'b'], s='s')]"

    def test_default(self):
        class CM(ComplexModel):
            _type_info = [
                ("i", Integer),
                ("s", String(default='default')),
            ]

        class SomeService(ServiceBase):
            @srpc(CM, _returns=String)
            def some_call(cm):
                return repr(cm)

        # s is missing
        ctx = _test([SomeService], 'cm.i=1')
        s = ''.join(ctx.out_string)
        assert s == "CM(i=1, s='default')"

        # s is None
        ctx = _test([SomeService], 'cm.i=1&cm.s')
        s = ''.join(ctx.out_string)
        assert s == "CM(i=1)"

        # s is empty
        ctx = _test([SomeService], 'cm.i=1&cm.s=')
        s = ''.join(ctx.out_string)
        assert s == "CM(i=1, s='')"

    def test_nested_flatten_with_primitive_array(self):
        class CCM(ComplexModel):
            _type_info = [
                ("i", Integer),
                ("c", Array(String)),
                ("s", String),
            ]

        class SomeService(ServiceBase):
            @srpc(CCM, _returns=String)
            def some_call(ccm):
                return repr(ccm)

        ctx = _test([SomeService],  'ccm.i=1&ccm.s=s'
                                   '&ccm.c=a'
                                   '&ccm.c=b')
        s = ''.join(list(ctx.out_string))
        assert s == "CCM(i=1, c=['a', 'b'], s='s')"

        ctx = _test([SomeService],  'ccm.i=1'
                                   '&ccm.s=s'
                                   '&ccm.c[1]=b'
                                   '&ccm.c[0]=a')
        s = ''.join(list(ctx.out_string))
        assert s == "CCM(i=1, c=['a', 'b'], s='s')"

        ctx = _test([SomeService],  'ccm.i=1'
                                   '&ccm.s=s'
                                   '&ccm.c[0]=a'
                                   '&ccm.c[1]=b')
        s = ''.join(list(ctx.out_string))
        assert s == "CCM(i=1, c=['a', 'b'], s='s')"

    def test_cookie_parse(self):
        string = 'some_string'
        class RequestHeader(ComplexModel):
            some_field = String

        class SomeService(ServiceBase):
            __in_header__ = RequestHeader

            @rpc(String)
            def some_call(ctx, s):
                assert ctx.in_header.some_field == string

        def start_response(code, headers):
            assert code == HTTP_200

        c = SimpleCookie()
        c['some_field'] = string

        ''.join(wsgiref_validator(WsgiApplication(Application([SomeService], 'tns',
            in_protocol=HttpRpc(parse_cookie=True), out_protocol=HttpRpc())))({
                'SCRIPT_NAME': '',
                'QUERY_STRING': '',
                'PATH_INFO': '/some_call',
                'REQUEST_METHOD': 'GET',
                'SERVER_NAME': 'localhost',
                'SERVER_PORT': "9999",
                'HTTP_COOKIE': str(c),
                'wsgi.url_scheme': 'http',
                'wsgi.version': (1,0),
                'wsgi.input': StringIO(),
                'wsgi.errors': StringIO(),
                'wsgi.multithread': False,
                'wsgi.multiprocess': False,
                'wsgi.run_once': True,
            }, start_response))

    def test_http_headers(self):
        d = datetime(year=2013, month=1, day=1)
        string = ['hey', 'yo']

        class ResponseHeader(ComplexModel):
            _type_info = {
                'Set-Cookie': String(max_occurs='unbounded'),
                'Expires': DateTime
            }

        class SomeService(ServiceBase):
            __out_header__ = ResponseHeader

            @rpc(String)
            def some_call(ctx, s):
                assert s is not None
                ctx.out_header = ResponseHeader(**{'Set-Cookie': string,
                                                                'Expires': d})

        def start_response(code, headers):
            assert len([s for s in string if ('Set-Cookie', s) in headers]) == len(string)
            assert dict(headers)['Expires'] == 'Tue, 01 Jan 2013 00:00:00 GMT'

        ret = ''.join(wsgiref_validator(WsgiApplication(Application([SomeService], 'tns',
            in_protocol=HttpRpc(), out_protocol=HttpRpc())))({
                'SCRIPT_NAME': '',
                'QUERY_STRING': '&s=foo',
                'PATH_INFO': '/some_call',
                'REQUEST_METHOD': 'GET',
                'SERVER_NAME': 'localhost',
                'SERVER_PORT': "9999",
                'wsgi.url_scheme': 'http',
                'wsgi.version': (1,0),
                'wsgi.input': StringIO(),
                'wsgi.errors': StringIO(),
                'wsgi.multithread': False,
                'wsgi.multiprocess': False,
                'wsgi.run_once': True,
            }, start_response))

        assert ret == ''


class TestHttpPatterns(unittest.TestCase):
    def test_rules(self):
        _int = 5
        _fragment = 'some_fragment'

        class SomeService(ServiceBase):
            @srpc(Integer, _returns=Integer, _patterns=[
                                      HttpPattern('/%s/<some_int>'% _fragment)])
            def some_call(some_int):
                assert some_int == _int

        app = Application([SomeService], 'tns', in_protocol=HttpRpc(), out_protocol=HttpRpc())
        server = WsgiApplication(app)

        environ = {
            'QUERY_STRING': '',
            'PATH_INFO': '/%s/%d' % (_fragment, _int),
            'SERVER_PATH':"/",
            'SERVER_NAME': "localhost",
            'wsgi.url_scheme': 'http',
            'SERVER_PORT': '9000',
            'REQUEST_METHOD': 'GET',
        }

        initial_ctx = WsgiMethodContext(server, environ, 'some-content-type')

        ctx, = server.generate_contexts(initial_ctx)

        foo = []
        for i in server._http_patterns:
            foo.append(i)

        assert len(foo) == 1
        print(foo)
        assert ctx.descriptor is not None

        server.get_in_object(ctx)
        assert ctx.in_error is None

        server.get_out_object(ctx)
        assert ctx.out_error is None


if __name__ == '__main__':
    unittest.main()
