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


zeep_logger = logging.getLogger('zeep')
zeep_logger.setLevel(logging.INFO)

import unittest

from datetime import datetime
from base64 import b64encode, b64decode

from spyne.test.interop._test_soap_client_base import server_started
from spyne.util import six

from zeep import Client
from zeep.transports import Transport
from zeep.exceptions import Error as ZeepError


class TestZeep(unittest.TestCase):
    def setUp(self):
        from spyne.test.interop._test_soap_client_base import run_server
        run_server('http')

        port, = server_started.keys()

        transport = Transport(cache=False)
        self.client = Client("http://localhost:%d/?wsdl" % port,
                                                            transport=transport)
        self.ns = "spyne.test.interop.server"

    def get_inst(self, what):
        return self.client.get_type(what)()

    def test_echo_datetime(self):
        val = datetime.now()
        ret = self.client.service.echo_datetime(val)

        assert val == ret

    def test_echo_datetime_with_invalid_format(self):
        val = datetime.now()
        ret = self.client.service.echo_datetime_with_invalid_format(val)

        assert val == ret

    def test_echo_date(self):
        val = datetime.now().date()
        ret = self.client.service.echo_date(val)

        assert val == ret

    def test_echo_date_with_invalid_format(self):
        val = datetime.now().date()
        ret = self.client.service.echo_date_with_invalid_format(val)

        assert val == ret

    def test_echo_time(self):
        val = datetime.now().time()
        ret = self.client.service.echo_time(val)

        assert val == ret

    def test_echo_time_with_invalid_format(self):
        val = datetime.now().time()
        ret = self.client.service.echo_time_with_invalid_format(val)

        assert val == ret

    def test_echo_simple_boolean_array(self):
        val = [False, False, False, True]
        ret = self.client.service.echo_simple_boolean_array(val)

        assert val == ret

    def test_echo_boolean(self):
        val = True
        ret = self.client.service.echo_boolean(val)
        self.assertEqual(val, ret)

        val = False
        ret = self.client.service.echo_boolean(val)
        self.assertEqual(val, ret)

    def test_enum(self):
        val = self.client.get_type("{%s}DaysOfWeekEnum" % self.ns)('Monday')

        ret = self.client.service.echo_enum(val)

        assert val == ret

    def test_bytearray(self):
        val = b"\x00\x01\x02\x03\x04"
        ret = self.client.service.echo_bytearray(val)

        assert val == ret

    def test_validation(self):
        non_nillable_class = self.client.get_type("{hunk.sunk}NonNillableClass")()
        non_nillable_class.i = 6
        non_nillable_class.s = None

        try:
            self.client.service.non_nillable(non_nillable_class)
        except ZeepError as e:
            pass
        else:
            raise Exception("must fail")

    def test_echo_integer_array(self):
        ia = self.client.get_type('{%s}integerArray' % self.ns)()
        ia.integer.extend([1, 2, 3, 4, 5])
        self.client.service.echo_integer_array(ia)

    def test_echo_in_header(self):
        in_header = self.client.get_type('{%s}InHeader' % self.ns)()
        in_header.s = 'a'
        in_header.i = 3

        ret = self.client.service.echo_in_header(_soapheaders={
            'InHeader': in_header,
        })

        print(ret)

        out_header = ret.body.echo_in_headerResult
        self.assertEqual(in_header.s, out_header.s)
        self.assertEqual(in_header.i, out_header.i)

    def test_echo_in_complex_header(self):
        in_header = self.client.get_type('{%s}InHeader' % self.ns)()
        in_header.s = 'a'
        in_header.i = 3
        in_trace_header = self.client.get_type('{%s}InTraceHeader' % self.ns)()
        in_trace_header.client = 'suds'
        in_trace_header.callDate = datetime(year=2000, month=1, day=1, hour=0,
                                              minute=0, second=0, microsecond=0)

        ret = self.client.service.echo_in_complex_header(_soapheaders={
            'InHeader': in_header,
            'InTraceHeader': in_trace_header
        })

        print(ret)

        out_header = ret.body.echo_in_complex_headerResult0
        out_trace_header = ret.body.echo_in_complex_headerResult1

        self.assertEqual(in_header.s, out_header.s)
        self.assertEqual(in_header.i, out_header.i)
        self.assertEqual(in_trace_header.client, out_trace_header.client)
        self.assertEqual(in_trace_header.callDate, out_trace_header.callDate)

    def test_send_out_header(self):
        out_header = self.client.get_type('{%s}OutHeader' % self.ns)()
        out_header.dt = datetime(year=2000, month=1, day=1)
        out_header.f = 3.141592653

        ret = self.client.service.send_out_header()

        self.assertEqual(ret.header.OutHeader.dt, out_header.dt)
        self.assertEqual(ret.header.OutHeader.f, out_header.f)

    def test_send_out_complex_header(self):
        out_header = self.client.get_type('{%s}OutHeader' % self.ns)()
        out_header.dt = datetime(year=2000, month=1, day=1)
        out_header.f = 3.141592653
        out_trace_header = self.client.get_type('{%s}OutTraceHeader' % self.ns)()
        out_trace_header.receiptDate = datetime(year=2000, month=1, day=1,
                                  hour=1, minute=1, second=1, microsecond=1)
        out_trace_header.returnDate = datetime(year=2000, month=1, day=1,
                                 hour=1, minute=1, second=1, microsecond=100)

        ret = self.client.service.send_out_complex_header()

        self.assertEqual(ret.header.OutHeader.dt, out_header.dt)
        self.assertEqual(ret.header.OutHeader.f, out_header.f)
        self.assertEqual(ret.header.OutTraceHeader.receiptDate, out_trace_header.receiptDate)
        self.assertEqual(ret.header.OutTraceHeader.returnDate, out_trace_header.returnDate)

    def test_echo_string(self):
        test_string = "OK"
        ret = self.client.service.echo_string(test_string)

        self.assertEqual(ret, test_string)

    def __get_xml_test_val(self):
        return {
            "test_sub": {
                "test_subsub1": {
                    "test_subsubsub1": ["subsubsub1 value"]
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


    def test_echo_simple_class(self):
        val = self.client.get_type("{%s}SimpleClass" % self.ns)()

        val.i = 45
        val.s = "asd"

        ret = self.client.service.echo_simple_class(val)

        assert ret.i == val.i
        assert ret.s == val.s

    def test_echo_class_with_self_reference(self):
        val = self.client.get_type("{%s}ClassWithSelfReference" % self.ns)()

        val.i = 45
        val.sr = self.client.get_type("{%s}ClassWithSelfReference" % self.ns)()
        val.sr.i = 50
        val.sr.sr = None

        ret = self.client.service.echo_class_with_self_reference(val)

        assert ret.i == val.i
        assert ret.sr.i == val.sr.i

    def test_echo_nested_class(self):
        val = self.client.get_type("{punk.tunk}NestedClass")()

        val.i = 45
        val.s = "asd"
        val.f = 12.34
        val.ai = self.client.get_type("{%s}integerArray" % self.ns)()
        val.ai.integer.extend([1, 2, 3, 45, 5, 3, 2, 1, 4])

        val.simple = self.client.get_type("{%s}SimpleClassArray" % self.ns)()

        val.simple.SimpleClass.append(self.client.get_type("{%s}SimpleClass" % self.ns)())
        val.simple.SimpleClass.append(self.client.get_type("{%s}SimpleClass" % self.ns)())

        val.simple.SimpleClass[0].i = 45
        val.simple.SimpleClass[0].s = "asd"
        val.simple.SimpleClass[1].i = 12
        val.simple.SimpleClass[1].s = "qwe"

        val.other = self.client.get_type("{%s}OtherClass" % self.ns)()
        val.other.dt = datetime.now()
        val.other.d = 123.456
        val.other.b = True

        ret = self.client.service.echo_nested_class(val)

        self.assertEqual(ret.i, val.i)
        self.assertEqual(ret.ai.integer, val.ai.integer)
        self.assertEqual(ret.ai.integer[0], val.ai.integer[0])
        self.assertEqual(ret.simple.SimpleClass[0].s, val.simple.SimpleClass[0].s)
        self.assertEqual(ret.other.dt, val.other.dt)

    def test_huge_number(self):
        self.assertEqual(self.client.service.huge_number(), 2 ** int(1e5))

    def test_long_string(self):
        self.assertEqual(self.client.service.long_string(),
                                                   ('0123456789abcdef' * 16384))

    def test_empty(self):
        self.client.service.test_empty()

    def test_echo_extension_class(self):
        val = self.client.get_type("{bar}ExtensionClass")()

        val.i = 45
        val.s = "asd"
        val.f = 12.34

        val.simple = self.client.get_type("{%s}SimpleClassArray" % self.ns)()

        val.simple.SimpleClass.append(self.client.get_type("{%s}SimpleClass" % self.ns)())
        val.simple.SimpleClass.append(self.client.get_type("{%s}SimpleClass" % self.ns)())

        val.simple.SimpleClass[0].i = 45
        val.simple.SimpleClass[0].s = "asd"
        val.simple.SimpleClass[1].i = 12
        val.simple.SimpleClass[1].s = "qwe"

        val.other = self.client.get_type("{%s}OtherClass" % self.ns)()
        val.other.dt = datetime.now()
        val.other.d = 123.456
        val.other.b = True

        val.p = self.client.get_type("{hunk.sunk}NonNillableClass")()
        val.p.dt = datetime(2010, 6, 2)
        val.p.i = 123
        val.p.s = "punk"

        val.l = datetime(2010, 7, 2)
        val.q = 5

        ret = self.client.service.echo_extension_class(val)
        print(ret)

        self.assertEqual(ret.i, val.i)
        self.assertEqual(ret.s, val.s)
        self.assertEqual(ret.f, val.f)
        self.assertEqual(ret.simple.SimpleClass[0].i, val.simple.SimpleClass[0].i)
        self.assertEqual(ret.other.dt, val.other.dt)
        self.assertEqual(ret.p.s, val.p.s)


    def test_python_exception(self):
        try:
            self.client.service.python_exception()
            raise Exception("must fail")
        except ZeepError as e:
            pass

    def test_soap_exception(self):
        try:
            self.client.service.soap_exception()
            raise Exception("must fail")
        except ZeepError as e:
            pass

    def test_complex_return(self):
        ret = self.client.service.complex_return()

        self.assertEqual(ret.resultCode, 1)
        self.assertEqual(ret.resultDescription, "Test")
        self.assertEqual(ret.transactionId, 123)
        self.assertEqual(ret.roles.RoleEnum[0], "MEMBER")

    def test_return_invalid_data(self):
        try:
            self.client.service.return_invalid_data()
            raise Exception("must fail")
        except:
            pass

    def test_custom_messages(self):
        ret = self.client.service.custom_messages("test")

        assert ret == 'test'

    def test_echo_simple_bare(self):
        ret = self.client.service.echo_simple_bare("test")

        assert ret == 'test'

    def test_echo_complex_bare(self):
        val = ['abc','def']
        ret = self.client.service.echo_complex_bare(val)

        assert ret == val

if __name__ == '__main__':
    unittest.main()
