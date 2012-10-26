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


from spyne.model.primitive import UnsignedInteger16
import unittest

from spyne.application import Application
from spyne.decorator import rpc
from spyne.model.complex import Array
from spyne.model.complex import ComplexModel
from spyne.model.primitive import AnyXml
from spyne.model.primitive import UnsignedLong
from spyne.model.primitive import Integer
from spyne.model.primitive import DateTime
from spyne.model.primitive import Unicode
from spyne.protocol.http import HttpRpc
from spyne.protocol.soap import Soap11
from spyne.service import ServiceBase


class TestInterface(unittest.TestCase):
    def test_imports(self):
        import logging
        logging.basicConfig(level=logging.DEBUG)
        class KeyValuePair(ComplexModel):
            __namespace__ = "1"
            key = Unicode
            value = Unicode

        class Something(ComplexModel):
            __namespace__ = "2"
            d = DateTime
            i = Integer

        class SomethingElse(ComplexModel):
            __namespace__ = "3"
            a = AnyXml
            b = UnsignedLong
            s = Something

        class BetterSomething(Something):
            __namespace__ = "4"
            k = UnsignedInteger16

        class Service1(ServiceBase):
            @rpc(SomethingElse, _returns=Array(KeyValuePair))
            def some_call(ctx, sth):
                pass

        class Service2(ServiceBase):
            @rpc(BetterSomething, _returns=Array(KeyValuePair))
            def some_other_call(ctx, sth):
                pass

        application = Application([Service1, Service2],
            in_protocol=HttpRpc(),
            out_protocol=Soap11(),
            name='Service', tns='target_namespace'
        )

        imports = application.interface.imports
        tns = application.interface.get_tns()
        smm = application.interface.service_method_map
        print(imports)

        assert imports[tns] == set(['1','3','4'])
        assert imports['3'] == set(['2'])
        assert imports['4'] == set(['2'])

        assert smm['{%s}some_call' % tns]
        assert smm['{%s}some_call' % tns][0][0] == Service1
        assert smm['{%s}some_call' % tns][0][1].function == Service1.some_call

        assert smm['{%s}some_other_call' % tns]
        assert smm['{%s}some_other_call' % tns][0][0] == Service2
        assert smm['{%s}some_other_call' % tns][0][1].function == Service2.some_other_call

if __name__ == '__main__':
    unittest.main()
