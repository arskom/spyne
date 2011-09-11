
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

import logging
logging.basicConfig(level=logging.DEBUG)

import unittest

from rpclib.application import Application
from rpclib.decorator import srpc
from rpclib.model.primitive import Integer
from rpclib.model.primitive import String
from rpclib.model.complex import ComplexModel
from rpclib.interface.wsdl import Wsdl11
from rpclib.protocol.http import HttpRpc
from rpclib.protocol.soap import Soap11
from rpclib.service import ServiceBase

class Test(unittest.TestCase):
    '''Most of the service tests are performed through the interop tests.'''

    def test_multiple_return(self):
        class SomeNotSoComplexModel(ComplexModel):
            s = String

        class SomeService(ServiceBase):
            @srpc(_returns=[Integer, String])
            def some_call():
                return 1,'s'

        app = Application([SomeService], 'tns', Wsdl11(), HttpRpc(), HttpRpc())

        from rpclib.server.wsgi import WsgiMethodContext

        ctx = WsgiMethodContext(app,{
            'QUERY_STRING': '',
            'PATH_INFO': '/some_call',
        }, 'some-content-type')

        from rpclib.server import ServerBase

        server = ServerBase(app)
        try:
            server.get_in_object(ctx)
            server.get_out_object(ctx)
            server.get_out_string(ctx)
        except ValueError:
            pass
        else:
            raise Exception("Must Fail")

    def test_primitive_only(self):
        class SomeComplexModel(ComplexModel):
            i = Integer
            s = String

        class SomeService(ServiceBase):
            @srpc(SomeComplexModel, _returns=SomeComplexModel)
            def some_call(scm):
                return SomeComplexModel(i=5,s='5x')

        app = Application([SomeService], 'tns', Wsdl11(), HttpRpc(), HttpRpc())

        from rpclib.server.wsgi import WsgiMethodContext

        ctx = WsgiMethodContext(app,{
            'QUERY_STRING': '',
            'PATH_INFO': '/some_call',
        }, 'some-content-type')

        from rpclib.server import ServerBase

        server = ServerBase(app)

        try:
            server.get_in_object(ctx)
            server.get_out_object(ctx)
            server.get_out_string(ctx)
        except ValueError:
            pass
        else:
            raise Exception("Must Fail")



if __name__ == '__main__':
    unittest.main()
