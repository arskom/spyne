#!/usr/bin/env python
# encoding: utf8
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

from spyne.server.wsgi import _parse_qs
from spyne.application import Application
from spyne.error import ValidationError
from spyne.const.http import HTTP_200
from spyne.decorator import rpc
from spyne.decorator import srpc
from spyne.model import ByteArray, DateTime, Uuid, String, Integer, Integer8, \
    ComplexModel, Array
from spyne.protocol.http import HttpRpc, HttpPattern, _parse_cookie
from spyne.service import Service
from spyne.server.wsgi import WsgiApplication, WsgiMethodContext
from spyne.server.http import HttpTransportContext
from spyne.util.test import call_wsgi_app_kwargs


class TestString(unittest.TestCase):
    def setUp(self):
        class SomeService(Service):
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
        assert ret == b'string'

    def test_without_encoding(self):
        headers = {'CONTENT_TYPE':'text/plain'}
        ret = call_wsgi_app_kwargs(self.app, 'echo_string', headers, s="string")
        assert ret == b'string'

    def test_with_encoding(self):
        headers = {'CONTENT_TYPE':'text/plain; charset=utf8'}
        ret = call_wsgi_app_kwargs(self.app, 'echo_string', headers, s="string")
        assert ret == b'string'


class TestHttpTransportContext(unittest.TestCase):
    def test_gen_header(self):
        val = HttpTransportContext.gen_header("text/plain", charset="utf8")
        assert val == 'text/plain; charset="utf8"'


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
        class SomeService(Service):
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
        class SomeService(Service):
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

        class SomeService(Service):
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

        class SomeService(Service):
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

        class SomeService(Service):
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

        class SomeService(Service):
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

        class SomeService(Service):
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

        class SomeService(Service):
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
        class SomeService(Service):
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
        class SomeService(Service):
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
        class SomeService(Service):
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
        class SomeService(Service):
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
        class SomeService(Service):
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
        class SomeService(Service):
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

        class SomeService(Service):
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

        class SomeService(Service):
            @srpc(CCM, _returns=String)
            def some_call(ccm):
                return repr(CCM(c=ccm.c, i=ccm.i, s=ccm.s))

        ctx = _test([SomeService], '&ccm.i=1&ccm.s=s&ccm.c.i=3&ccm.c.s=cs')

        assert ctx.out_string[0] == b"CCM(i=1, c=CM(i=3, s='cs'), s='s')"

    def test_simple_array(self):
        class SomeService(Service):
            @srpc(String(max_occurs='unbounded'), _returns=String)
            def some_call(s):
                return '\n'.join(s)

        ctx = _test([SomeService], '&s=1&s=2')
        assert b''.join(ctx.out_string) == b'1\n2'

    def test_complex_array(self):
        class CM(ComplexModel):
            _type_info = [
                ("i", Integer),
                ("s", String),
            ]

        class SomeService(Service):
            @srpc(Array(CM), _returns=String)
            def some_call(cs):
                return '\n'.join([repr(c) for c in cs])

        ctx = _test([SomeService],
             'cs[0].i=1&cs[0].s=x'
            '&cs[1].i=2&cs[1].s=y'
            '&cs[2].i=3&cs[2].s=z')

        assert b''.join(ctx.out_string) == \
           b"CM(i=1, s='x')\n" \
           b"CM(i=2, s='y')\n" \
           b"CM(i=3, s='z')"

    def test_complex_array_empty(self):
        class CM(ComplexModel):
            _type_info = [
                ("i", Integer),
                ("s", String),
            ]

        class SomeService(Service):
            @srpc(Array(CM), _returns=String)
            def some_call(cs):
                return repr(cs)

        ctx = _test([SomeService], 'cs=empty')

        assert b''.join(ctx.out_string) == b'[]'

    def test_complex_object_empty(self):
        class CM(ComplexModel):
            _type_info = [
                ("i", Integer),
                ("s", String),
            ]

        class SomeService(Service):
            @srpc(CM, _returns=String)
            def some_call(c):
                return repr(c)

        ctx = _test([SomeService], 'c=empty')

        assert b''.join(ctx.out_string) == b'CM()'

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

        class SomeService(Service):
            @srpc(CCM, _returns=String)
            def some_call(ccm):
                return repr(ccm)

        ctx = _test([SomeService], '&ccm.i=1&ccm.s=s&ccm.c.i=3&ccm.c.s=cs')

        print(ctx.out_string)
        assert b''.join(ctx.out_string) == b"CCM(i=1, c=CM(i=3, s='cs'), s='s')"

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

        class SomeService(Service):
            @srpc(CCM.customize(max_occurs=2), _returns=String)
            def some_call(ccm):
                return repr(ccm)

        ctx = _test([SomeService],  'ccm[0].i=1&ccm[0].s=s'
                                   '&ccm[0].c.i=1&ccm[0].c.s=a'
                                   '&ccm[1].c.i=2&ccm[1].c.s=b')

        s = b''.join(ctx.out_string)

        assert s == b"[CCM(i=1, c=CM(i=1, s='a'), s='s'), CCM(c=CM(i=2, s='b'))]"

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

        class SomeService(Service):
            @srpc(CCM, _returns=String)
            def some_call(ccm):
                return repr(ccm)

        ctx = _test([SomeService],  'ccm.i=1&ccm.s=s'
                                   '&ccm.c[0].i=1&ccm.c[0].s=a'
                                   '&ccm.c[1].i=2&ccm.c[1].s=b')

        s = b''.join(list(ctx.out_string))
        assert s == b"CCM(i=1, c=[CM(i=1, s='a'), CM(i=2, s='b')], s='s')"

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

        class SomeService(Service):
            @srpc(CCM, _returns=String)
            def some_call(ccm):
                return repr(ccm)

        ctx = _test([SomeService],  'ccm.i=1&ccm.s=s'
                                   '&ccm.c[0].i=1&ccm.c[0].s=a'
                                   '&ccm.c[1].i=2&ccm.c[1].s=b')

        s = b''.join(list(ctx.out_string))
        assert s == b"CCM(i=1, c=[CM(i=1, s='a'), CM(i=2, s='b')], s='s')"

    def test_nested_2_flatten_with_primitive_array(self):
        class CCM(ComplexModel):
            _type_info = [
                ("i", Integer),
                ("c", Array(String)),
                ("s", String),
            ]

        class SomeService(Service):
            @srpc(Array(CCM), _returns=String)
            def some_call(ccm):
                return repr(ccm)

        ctx = _test([SomeService],  'ccm[0].i=1&ccm[0].s=s'
                                   '&ccm[0].c=a'
                                   '&ccm[0].c=b')
        s = b''.join(list(ctx.out_string))
        assert s == b"[CCM(i=1, c=['a', 'b'], s='s')]"

    def test_default(self):
        class CM(ComplexModel):
            _type_info = [
                ("i", Integer),
                ("s", String(default='default')),
            ]

        class SomeService(Service):
            @srpc(CM, _returns=String)
            def some_call(cm):
                return repr(cm)

        # s is missing
        ctx = _test([SomeService], 'cm.i=1')
        s = b''.join(ctx.out_string)
        assert s == b"CM(i=1, s='default')"

        # s is None
        ctx = _test([SomeService], 'cm.i=1&cm.s')
        s = b''.join(ctx.out_string)
        assert s == b"CM(i=1)"

        # s is empty
        ctx = _test([SomeService], 'cm.i=1&cm.s=')
        s = b''.join(ctx.out_string)
        assert s == b"CM(i=1, s='')"

    def test_nested_flatten_with_primitive_array(self):
        class CCM(ComplexModel):
            _type_info = [
                ("i", Integer),
                ("c", Array(String)),
                ("s", String),
            ]

        class SomeService(Service):
            @srpc(CCM, _returns=String)
            def some_call(ccm):
                return repr(ccm)

        ctx = _test([SomeService],  'ccm.i=1&ccm.s=s'
                                   '&ccm.c=a'
                                   '&ccm.c=b')
        s = b''.join(list(ctx.out_string))
        assert s == b"CCM(i=1, c=['a', 'b'], s='s')"

        ctx = _test([SomeService],  'ccm.i=1'
                                   '&ccm.s=s'
                                   '&ccm.c[1]=b'
                                   '&ccm.c[0]=a')
        s = b''.join(list(ctx.out_string))
        assert s == b"CCM(i=1, c=['a', 'b'], s='s')"

        ctx = _test([SomeService],  'ccm.i=1'
                                   '&ccm.s=s'
                                   '&ccm.c[0]=a'
                                   '&ccm.c[1]=b')
        s = b''.join(list(ctx.out_string))
        assert s == b"CCM(i=1, c=['a', 'b'], s='s')"

    def test_http_headers(self):
        d = datetime(year=2013, month=1, day=1)
        string = ['hey', 'yo']

        class ResponseHeader(ComplexModel):
            _type_info = {
                'Set-Cookie': String(max_occurs='unbounded'),
                'Expires': DateTime
            }

        class SomeService(Service):
            __out_header__ = ResponseHeader

            @rpc(String)
            def some_call(ctx, s):
                assert s is not None
                ctx.out_header = ResponseHeader(**{'Set-Cookie': string,
                                                                  'Expires': d})

        def start_response(code, headers):
            print(headers)
            assert len([s for s in string
                                if ('Set-Cookie', s) in headers]) == len(string)
            assert dict(headers)['Expires'] == 'Tue, 01 Jan 2013 00:00:00 GMT'

        app = Application([SomeService], 'tns',
                                  in_protocol=HttpRpc(), out_protocol=HttpRpc())
        wsgi_app = WsgiApplication(app)

        req_dict = {
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
        }

        ret = wsgi_app(req_dict, start_response)
        print(list(ret))

        wsgi_app = wsgiref_validator(wsgi_app)

        ret = wsgi_app(req_dict, start_response)

        assert list(ret) == [b'']


class TestHttpPatterns(unittest.TestCase):
    def test_rules(self):
        _int = 5
        _fragment = 'some_fragment'

        class SomeService(Service):
            @srpc(Integer, _returns=Integer, _patterns=[
                                     HttpPattern('/%s/<some_int>' % _fragment)])
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


class ParseCookieTest(unittest.TestCase):
    def test_cookie_parse(self):
        string = 'some_string'
        class RequestHeader(ComplexModel):
            some_field = String

        class SomeService(Service):
            __in_header__ = RequestHeader

            @rpc(String)
            def some_call(ctx, s):
                assert ctx.in_header.some_field == string

        def start_response(code, headers):
            assert code == HTTP_200

        c = 'some_field=%s'% (string,)

        app = Application([SomeService], 'tns',
            in_protocol=HttpRpc(parse_cookie=True), out_protocol=HttpRpc())

        wsgi_app = WsgiApplication(app)

        req_dict = {
            'SCRIPT_NAME': '',
            'QUERY_STRING': '',
            'PATH_INFO': '/some_call',
            'REQUEST_METHOD': 'GET',
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': "9999",
            'HTTP_COOKIE': c,
            'wsgi.url_scheme': 'http',
            'wsgi.version': (1,0),
            'wsgi.input': StringIO(),
            'wsgi.errors': StringIO(),
            'wsgi.multithread': False,
            'wsgi.multiprocess': False,
            'wsgi.run_once': True,
        }

        ret = wsgi_app(req_dict, start_response)
        print(ret)

        wsgi_app = wsgiref_validator(wsgi_app)

        ret = wsgi_app(req_dict, start_response)
        print(ret)

    # These tests copied from Django:
    # https://github.com/django/django/pull/6277/commits/da810901ada1cae9fc1f018f879f11a7fb467b28
    def test_python_cookies(self):
        """
        Test cases copied from Python's Lib/test/test_http_cookies.py
        """
        self.assertEqual(_parse_cookie('chips=ahoy; vienna=finger'), {'chips': 'ahoy', 'vienna': 'finger'})
        # Here _parse_cookie() differs from Python's cookie parsing in that it
        # treats all semicolons as delimiters, even within quotes.
        self.assertEqual(
            _parse_cookie('keebler="E=mc2; L=\\"Loves\\"; fudge=\\012;"'),
            {'keebler': '"E=mc2', 'L': '\\"Loves\\"', 'fudge': '\\012', '': '"'}
        )
        # Illegal cookies that have an '=' char in an unquoted value.
        self.assertEqual(_parse_cookie('keebler=E=mc2'), {'keebler': 'E=mc2'})
        # Cookies with ':' character in their name.
        self.assertEqual(_parse_cookie('key:term=value:term'), {'key:term': 'value:term'})
        # Cookies with '[' and ']'.
        self.assertEqual(_parse_cookie('a=b; c=[; d=r; f=h'), {'a': 'b', 'c': '[', 'd': 'r', 'f': 'h'})

    def test_cookie_edgecases(self):
        # Cookies that RFC6265 allows.
        self.assertEqual(_parse_cookie('a=b; Domain=example.com'), {'a': 'b', 'Domain': 'example.com'})
        # _parse_cookie() has historically kept only the last cookie with the
        # same name.
        self.assertEqual(_parse_cookie('a=b; h=i; a=c'), {'a': 'c', 'h': 'i'})

    def test_invalid_cookies(self):
        """
        Cookie strings that go against RFC6265 but browsers will send if set
        via document.cookie.
        """
        # Chunks without an equals sign appear as unnamed values per
        # https://bugzilla.mozilla.org/show_bug.cgi?id=169091
        self.assertIn('django_language',
                   _parse_cookie('abc=def; unnamed; django_language=en').keys())
        # Even a double quote may be an unamed value.
        self.assertEqual(
                   _parse_cookie('a=b; "; c=d'), {'a': 'b', '': '"', 'c': 'd'})
        # Spaces in names and values, and an equals sign in values.
        self.assertEqual(_parse_cookie('a b c=d e = f; gh=i'),
                                                {'a b c': 'd e = f', 'gh': 'i'})
        # More characters the spec forbids.
        self.assertEqual(_parse_cookie('a   b,c<>@:/[]?{}=d  "  =e,f g'),
                                          {'a   b,c<>@:/[]?{}': 'd  "  =e,f g'})
        # Unicode characters. The spec only allows ASCII.
        self.assertEqual(_parse_cookie(u'saint=André Bessette'),
                                                  {u'saint': u'André Bessette'})
        # Browsers don't send extra whitespace or semicolons in Cookie headers,
        # but _parse_cookie() should parse whitespace the same way
        # document.cookie parses whitespace.
        self.assertEqual(_parse_cookie('  =  b  ;  ;  =  ;   c  =  ;  '),
                                                             {'': 'b', 'c': ''})


if __name__ == '__main__':
    unittest.main()
