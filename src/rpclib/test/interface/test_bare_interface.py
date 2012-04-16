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

from rpclib.application import Application
from rpclib.decorator import rpc
from rpclib.model.complex import Array
from rpclib.model.complex import ComplexModel
from rpclib.model.primitive import Unicode
from rpclib.model.primitive import String
from rpclib.protocol.http import HttpRpc
from rpclib.protocol.soap import Soap11
from rpclib.service import ServiceBase


class TestComplexModel(unittest.TestCase):
    def test_interface(self):
        class KeyValuePair(ComplexModel):
            key = Unicode
            value = Unicode

        class Service(ServiceBase):
            @rpc(String(max_occurs='unbounded'), _returns=Array(KeyValuePair))
            def get_values(ctx, keys):
                pass

        application = Application([Service],
            in_protocol=HttpRpc(),
            out_protocol=Soap11(),
            name='Service', tns='tns'
        )

if __name__ == '__main__':
    unittest.main()
