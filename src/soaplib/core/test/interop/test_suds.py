#!/usr/bin/env python
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

import unittest

from suds.client import Client
from suds import WebFault
from datetime import datetime
from lxml import etree

from soaplib.core.util.etreeconv import  root_dict_to_etree



class TestSuds(unittest.TestCase):
    def setUp(self):
        self.client = Client("http://localhost:9753/?wsdl", cache=None)
        self.ns = "soaplib.test.interop.server._service"

    def test_echo_simple_boolean_array(self):
        val = [False, False, False, True]
        ret = self.client.service.echo_simple_boolean_array(val)

        assert val == ret

    def test_echo_boolean(self):
        val = True
        ret = self.client.service.echo_boolean(val)
        self.assertEquals(val,ret)

        val = False
        ret = self.client.service.echo_boolean(val)
        self.assertEquals(val,ret)

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
        except WebFault, e:
            pass

    def test_echo_integer_array(self):
        ia = self.client.factory.create('integerArray')
        ia.integer.extend([1,2,3,4,5])
        self.client.service.echo_integer_array(ia)

    def test_echo_in_header(self):
        in_header = self.client.factory.create('InHeader')
        in_header.s = 'a'
        in_header.i = 3

        self.client.set_options(soapheaders=in_header)
        ret = self.client.service.echo_in_header()
        self.client.set_options(soapheaders=None)

        print ret

        self.assertEquals(in_header.s, ret.s)
        self.assertEquals(in_header.i, ret.i)

    def test_send_out_header(self):
        out_header = self.client.factory.create('OutHeader')
        out_header.dt = datetime(year=2000, month=01, day=01)
        out_header.f = 3.141592653

        ret = self.client.service.send_out_header()

        self.assertTrue(isinstance(ret,type(out_header)))
        self.assertEquals(ret.dt, out_header.dt)
        self.assertEquals(ret.f, out_header.f)

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

        val=self.__get_xml_test_val()
        et = root_dict_to_etree(val)

        ret = self.client.service.echo_any(etree.tostring(et))

        self.assertEquals(
            ret['test_sub']['test_subsub1']['test_subsubsub1'],
            et.find("test_subsub1").find("test_subsubsub1").text
        )
        self.assertEquals(
            ret['test_sub']['test_subsub5'],
            et.find("test_subsub5").text
        )

    def test_any_as_dict(self):
        val = self.__get_xml_test_val()
        et = root_dict_to_etree(val)

        ret = self.client.service.echo_any_as_dict(etree.tostring(et))

        self.assertEquals(
            ret['test_sub']['test_subsub1']['test_subsubsub1'],
            et.find("test_subsub1").find("test_subsubsub1").text
        )
        self.assertEquals(
            ret['test_sub']['test_subsub5'],
            et.find("test_subsub5").text
        )

    def test_echo_simple_class(self):
        val = self.client.factory.create("SimpleClass")

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
        val.ai = self.client.factory.create("integerArray")
        val.ai.integer.extend([1,2,3,45,5,3,2,1,4])

        val.simple = self.client.factory.create("SimpleClassArray")

        val.simple.SimpleClass.append(self.client.factory.create("SimpleClass"))
        val.simple.SimpleClass.append(self.client.factory.create("SimpleClass"))

        val.simple.SimpleClass[0].i = 45
        val.simple.SimpleClass[0].s = "asd"
        val.simple.SimpleClass[1].i = 12
        val.simple.SimpleClass[1].s = "qwe"

        val.other = self.client.factory.create("OtherClass");
        val.other.dt = datetime.now()
        val.other.d = 123.456
        val.other.b = True

        ret = self.client.service.echo_nested_class(val)



        self.assertEquals(ret.i, val.i)
        self.assertEqual(ret.ai[0], val.ai[0])
        self.assertEquals(ret.simple.SimpleClass[0].s, val.simple.SimpleClass[0].s)
        self.assertEqual(ret.other.dt, val.other.dt)


    def test_echo_extension_class(self):
        service_name = "echo_extension_class";
        val = self.client.factory.create("{bar}ExtensionClass");

        val.i = 45
        val.s = "asd"
        val.f = 12.34

        val.simple = self.client.factory.create("SimpleClassArray")

        val.simple.SimpleClass.append(self.client.factory.create("SimpleClass"))
        val.simple.SimpleClass.append(self.client.factory.create("SimpleClass"))

        val.simple.SimpleClass[0].i = 45
        val.simple.SimpleClass[0].s = "asd"
        val.simple.SimpleClass[1].i = 12
        val.simple.SimpleClass[1].s = "qwe"

        val.other = self.client.factory.create("OtherClass");
        val.other.dt = datetime.now()
        val.other.d = 123.456
        val.other.b = True

        val.p = self.client.factory.create("{hunk.sunk}NonNillableClass");
        val.p.dt = datetime(2010,06,02)
        val.p.i = 123
        val.p.s = "punk"

        val.l = datetime(2010,07,02)
        val.q = 5

        ret = self.client.service.echo_extension_class(val)
        print ret

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

if __name__ == '__main__':
    unittest.main()
