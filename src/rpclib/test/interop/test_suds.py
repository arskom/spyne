#!/usr/bin/env python
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

from suds.client import Client
from suds import WebFault
from datetime import datetime

import logging
suds_logger = logging.getLogger('suds')
suds_logger.setLevel(logging.INFO)

class TestSuds(unittest.TestCase):
    def setUp(self):
        self.client = Client("http://localhost:9753/?wsdl", cache=None)
        self.ns = "rpclib.test.interop.server._service"

    def test_echo_simple_boolean_array(self):
        val = [False, False, False, True]
        ret = self.client.service.echo_simple_boolean_array(val)

        assert val == ret

    def test_echo_boolean(self):
        val = True
        ret = self.client.service.echo_boolean(val)
        self.assertEquals(val, ret)

        val = False
        ret = self.client.service.echo_boolean(val)
        self.assertEquals(val, ret)

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
            self.client.service.non_nillable(non_nillable_class)
        except WebFault, e:
            pass
        else:
            raise Exception("must fail")

    def test_echo_integer_array(self):
        ia = self.client.factory.create('integerArray')
        ia.integer.extend([1, 2, 3, 4, 5])
        self.client.service.echo_integer_array(ia)

    def test_echo_in_header(self):
        in_header = self.client.factory.create('InHeader')
        in_header.s = 'a'
        in_header.i = 3

        self.client.set_options(soapheaders=in_header)
        ret = self.client.service.echo_in_header()
        self.client.set_options(soapheaders=None)

        print(ret)

        self.assertEquals(in_header.s, ret.s)
        self.assertEquals(in_header.i, ret.i)

    def test_echo_in_complex_header(self):
        in_header = self.client.factory.create('InHeader')
        in_header.s = 'a'
        in_header.i = 3
        in_trace_header = self.client.factory.create('InTraceHeader')
        in_trace_header.client = 'suds'
        in_trace_header.callDate = datetime(year=2000, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

        self.client.set_options(soapheaders=(in_header, in_trace_header))
        ret = self.client.service.echo_in_complex_header()
        self.client.set_options(soapheaders=None)

        print(ret)

        self.assertEquals(in_header.s, ret[0].s)
        self.assertEquals(in_header.i, ret[0].i)
        self.assertEquals(in_trace_header.client, ret[1].client)
        self.assertEquals(in_trace_header.callDate, ret[1].callDate)

    def test_send_out_header(self):
        out_header = self.client.factory.create('OutHeader')
        out_header.dt = datetime(year=2000, month=1, day=1)
        out_header.f = 3.141592653

        ret = self.client.service.send_out_header()

        self.assertTrue(isinstance(ret, type(out_header)))
        self.assertEquals(ret.dt, out_header.dt)
        self.assertEquals(ret.f, out_header.f)

    def test_send_out_complex_header(self):
        out_header = self.client.factory.create('OutHeader')
        out_header.dt = datetime(year=2000, month=1, day=1)
        out_header.f = 3.141592653
        out_trace_header = self.client.factory.create('OutTraceHeader')
        out_trace_header.receiptDate = datetime(year=2000, month=1, day=1,
                                  hour=1, minute=1, second=1, microsecond=1)
        out_trace_header.returnDate = datetime(year=2000, month=1, day=1,
                                 hour=1, minute=1, second=1, microsecond=100)

        ret = self.client.service.send_out_complex_header()

        self.assertTrue(isinstance(ret[0], type(out_header)))
        self.assertEquals(ret[0].dt, out_header.dt)
        self.assertEquals(ret[0].f, out_header.f)
        self.assertTrue(isinstance(ret[1], type(out_trace_header)))
        self.assertEquals(ret[1].receiptDate, out_trace_header.receiptDate)
        self.assertEquals(ret[1].returnDate, out_trace_header.returnDate)
        # Control the reply soap header (in an unelegant way but this is the
        # only way with suds)
        soapheaders = self.client.last_received().getChild("Envelope").getChild("Header")
        soap_out_header = soapheaders.getChild('OutHeader')
        self.assertEquals('T'.join((out_header.dt.date().isoformat(),
                                    out_header.dt.time().isoformat())),
                          soap_out_header.getChild('dt').getText())
        self.assertEquals(unicode(out_header.f), soap_out_header.getChild('f').getText())
        soap_out_trace_header = soapheaders.getChild('OutTraceHeader')
        self.assertEquals('T'.join((out_trace_header.receiptDate.date().isoformat(),
                                    out_trace_header.receiptDate.time().isoformat())),
                          soap_out_trace_header.getChild('receiptDate').getText())
        self.assertEquals('T'.join((out_trace_header.returnDate.date().isoformat(),
                                    out_trace_header.returnDate.time().isoformat())),
                          soap_out_trace_header.getChild('returnDate').getText())

    def test_echo_string(self):
        test_string = "OK"
        ret = self.client.service.echo_string(test_string)

        self.assertEquals(ret, test_string)

    def __get_xml_test_val(self):
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
        val = self.__get_xml_test_val()
        ret = self.client.service.echo_any(val)

        self.assertDictEqual(dict(ret[0]), val) # FIXME: Bah. Somebody write this comparison code!..

    def test_any_as_dict(self):
        val = self.__get_xml_test_val()
        ret = self.client.service.echo_any_as_dict(val)

        self.assertDictEqual(dict(ret[0]), val) # FIXME: Same as above!..

    def test_echo_simple_class(self):
        val = self.client.factory.create("{rpclib.test.interop.server._service}SimpleClass")

        val.i = 45
        val.s = "asd"

        ret = self.client.service.echo_simple_class(val)

        assert ret.i == val.i
        assert ret.s == val.s

    def test_echo_class_with_self_reference(self):
        val = self.client.factory.create("{rpclib.test.interop.server._service}ClassWithSelfReference")

        val.i = 45
        val.sr = self.client.factory.create("{rpclib.test.interop.server._service}ClassWithSelfReference")
        val.sr.i = 50
        val.sr.sr = None

        ret = self.client.service.echo_class_with_self_reference(val)

        assert ret.i == val.i
        assert ret.sr.i == val.sr.i

    def test_echo_nested_class(self):
        val = self.client.factory.create("{punk.tunk}NestedClass");

        val.i = 45
        val.s = "asd"
        val.f = 12.34
        val.ai = self.client.factory.create("integerArray")
        val.ai.integer.extend([1, 2, 3, 45, 5, 3, 2, 1, 4])

        val.simple = self.client.factory.create("{rpclib.test.interop.server._service}SimpleClassArray")

        val.simple.SimpleClass.append(self.client.factory.create("{rpclib.test.interop.server._service}SimpleClass"))
        val.simple.SimpleClass.append(self.client.factory.create("{rpclib.test.interop.server._service}SimpleClass"))

        val.simple.SimpleClass[0].i = 45
        val.simple.SimpleClass[0].s = "asd"
        val.simple.SimpleClass[1].i = 12
        val.simple.SimpleClass[1].s = "qwe"

        val.other = self.client.factory.create("{rpclib.test.interop.server._service}OtherClass");
        val.other.dt = datetime.now()
        val.other.d = 123.456
        val.other.b = True

        ret = self.client.service.echo_nested_class(val)

        self.assertEquals(ret.i, val.i)
        self.assertEqual(ret.ai[0], val.ai[0])
        self.assertEquals(ret.simple.SimpleClass[0].s, val.simple.SimpleClass[0].s)
        self.assertEqual(ret.other.dt, val.other.dt)

    def test_huge_number(self):
        self.assertEquals(self.client.service.huge_number(), 2**int(1e5))

    def test_long_string(self):
        self.assertEquals(self.client.service.long_string(), ('0123456789abcdef' * 16384))

    def test_long_string(self):
        self.client.service.test_empty()

    def test_echo_extension_class(self):
        val = self.client.factory.create("{bar}ExtensionClass")

        val.i = 45
        val.s = "asd"
        val.f = 12.34

        val.simple = self.client.factory.create("{rpclib.test.interop.server._service}SimpleClassArray")

        val.simple.SimpleClass.append(self.client.factory.create("{rpclib.test.interop.server._service}SimpleClass"))
        val.simple.SimpleClass.append(self.client.factory.create("{rpclib.test.interop.server._service}SimpleClass"))

        val.simple.SimpleClass[0].i = 45
        val.simple.SimpleClass[0].s = "asd"
        val.simple.SimpleClass[1].i = 12
        val.simple.SimpleClass[1].s = "qwe"

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
        self.assertEquals(ret.simple.SimpleClass[0].i, val.simple.SimpleClass[0].i)
        self.assertEquals(ret.other.dt, val.other.dt)
        self.assertEquals(ret.p.s, val.p.s)


    def test_python_exception(self):
        try:
            self.client.service.python_exception()
            raise Exception("must fail")
        except WebFault, e:
            pass

    def test_soap_exception(self):
        try:
            self.client.service.soap_exception()
            raise Exception("must fail")
        except WebFault, e:
            pass

    def test_complex_return(self):
        ret = self.client.service.complex_return()

        self.assertEquals(ret.resultCode, 1)
        self.assertEquals(ret.resultDescription, "Test")
        self.assertEquals(ret.transactionId, 123)
        self.assertEquals(ret.roles.RoleEnum[0], "MEMBER")

    def test_return_invalid_data(self):
        try:
            self.client.service.return_invalid_data()
            raise Exception("must fail")
        except:
            pass

    def test_custom_messages(self):
        ret = self.client.service.custom_messages("test")

        assert ret == 'test'

if __name__ == '__main__':
    unittest.main()
