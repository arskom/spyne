
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

import unittest

from rpclib.model.fault import Fault

from datetime import datetime

class RpclibClientTestBase(object):
    def test_echo_boolean(self):
        val = True
        ret = self.client.service.echo_boolean(val)
        self.assertEquals(val, ret)

        val = False
        ret = self.client.service.echo_boolean(val)
        self.assertEquals(val, ret)

    def test_echo_simple_boolean_array(self):
        val = [False, False, False, True]
        ret = self.client.service.echo_simple_boolean_array(val)

        assert val == ret

    def test_echo_integer_array(self):
        val = [1, 2, 3, 4, 5]
        ret = self.client.service.echo_integer_array([1, 2, 3, 4, 5])

        self.assertEquals(val, ret)

    def test_echo_string(self):
        val = "OK"
        ret = self.client.service.echo_string(val)

        self.assertEquals(ret, val)

    def test_enum(self):
        DaysOfWeekEnum = self.client.factory.create("DaysOfWeekEnum")

        val = DaysOfWeekEnum.Monday
        ret = self.client.service.echo_enum(val)

        assert val == ret

    def test_validation(self):
        non_nillable_class = self.client.factory.create(
                                                "{hunk.sunk}NonNillableClass")
        non_nillable_class.i = 6
        non_nillable_class.s = None

        try:
            ret = self.client.service.non_nillable(non_nillable_class)
            raise Exception("must fail")

        except Fault, e:
            assert e.faultcode in ('senv:Client.SchemaValidationError', 'senv:Client.ValidationError')

    def test_echo_in_header(self):
        in_header = self.client.factory.create('{rpclib.test.interop.server}InHeader')
        in_header.s = 'a'
        in_header.i = 3

        self.client.set_options(soapheaders=in_header)
        ret = self.client.service.echo_in_header()
        self.client.set_options(soapheaders=None)

        self.assertEquals(in_header.s, ret.s)
        self.assertEquals(in_header.i, ret.i)

    def test_send_out_header(self):
        call = self.client.service.send_out_header
        ret = call()
        in_header = call.ctx.in_header

        self.assertTrue(isinstance(ret, type(in_header)))
        self.assertEquals(ret.dt, in_header.dt)
        self.assertEquals(ret.f, in_header.f)

    def _get_xml_test_val(self):
        return {
            "test_sub": {
                "test_subsub1": {
                    "test_subsubsub1" : ["subsubsub1 value"]
                },
                "test_subsub2": ["subsub2 value 1", "subsub2 value 2"],
                "test_subsub3": [
                    {
                        "test_subsub3sub1": ["subsub3sub1 value"]
                    },
                    {
                        "test_subsub3sub2": ["subsub3sub2 value"]
                    },
                ],
                "test_subsub4": [],
                "test_subsub5": ["x"],
            }
        }

    def test_any(self):
        val = self._get_xml_test_val()
        ret = self.client.service.echo_any(val)

        self.assertDictEquals(ret, val)

    def test_any_as_dict(self):
        val=self._get_xml_test_val()
        ret = self.client.service.echo_any_as_dict(val)

        self.assertEquals(ret, val)

    def test_echo_simple_class(self):
        val = self.client.factory.create("{rpclib.test.interop.server._service}SimpleClass")

        val.i = 45
        val.s = "asd"

        ret = self.client.service.echo_simple_class(val)

        assert ret.i == val.i
        assert ret.s == val.s

    def test_echo_nested_class(self):
        val = self.client.factory.create("{punk.tunk}NestedClass");

        val.i = 45
        val.s = "asd"
        val.f = 12.34
        val.ai = [1, 2, 3, 45, 5, 3, 2, 1, 4]

        val.simple = [
            self.client.factory.create("{rpclib.test.interop.server._service}SimpleClass"),
            self.client.factory.create("{rpclib.test.interop.server._service}SimpleClass"),
        ]

        val.simple[0].i = 45
        val.simple[0].s = "asd"
        val.simple[1].i = 12
        val.simple[1].s = "qwe"

        val.other = self.client.factory.create("{rpclib.test.interop.server._service}OtherClass");
        val.other.dt = datetime.now()
        val.other.d = 123.456
        val.other.b = True

        ret = self.client.service.echo_nested_class(val)

        self.assertEquals(ret.i, val.i)
        self.assertEqual(ret.ai[0], val.ai[0])
        self.assertEquals(ret.simple[0].s, val.simple[0].s)
        self.assertEqual(ret.other.dt, val.other.dt)

    def test_echo_extension_class(self):
        val = self.client.factory.create("{bar}ExtensionClass");

        val.i = 45
        val.s = "asd"
        val.f = 12.34

        val.simple = [
            self.client.factory.create("{rpclib.test.interop.server._service}SimpleClass"),
            self.client.factory.create("{rpclib.test.interop.server._service}SimpleClass"),
        ]

        val.simple[0].i = 45
        val.simple[0].s = "asd"
        val.simple[1].i = 12
        val.simple[1].s = "qwe"

        val.other = self.client.factory.create("{rpclib.test.interop.server._service}OtherClass");
        val.other.dt = datetime.now()
        val.other.d = 123.456
        val.other.b = True

        val.p = self.client.factory.create("{hunk.sunk}NonNillableClass");
        val.p.dt = datetime(2010, 6, 2)
        val.p.i = 123
        val.p.s = "punk"

        val.l = datetime(2010, 7, 2)
        val.q = 5

        ret = self.client.service.echo_extension_class(val)
        print(ret)

        self.assertEquals(ret.i, val.i)
        self.assertEquals(ret.s, val.s)
        self.assertEquals(ret.f, val.f)
        self.assertEquals(ret.simple[0].i, val.simple[0].i)
        self.assertEquals(ret.other.dt, val.other.dt)
        self.assertEquals(ret.p.s, val.p.s)


    def test_python_exception(self):
        try:
            self.client.service.python_exception()
        except Exception, e:
            pass
        else:
            raise Exception("must fail")

    def test_soap_exception(self):
        try:
            self.client.service.soap_exception()
        except Exception, e:
            pass
        else:
            raise Exception("must fail")

    def test_complex_return(self):
        roles = self.client.factory.create("RoleEnum")
        ret = self.client.service.complex_return()

        self.assertEquals(ret.resultCode, 1)
        self.assertEquals(ret.resultDescription, "Test")
        self.assertEquals(ret.transactionId, 123)
        self.assertEquals(ret.roles[0], roles.MEMBER)

if __name__ == '__main__':
    unittest.main()
