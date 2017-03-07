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

import unittest

from spyne.test.protocol._test_dictdoc import TDictDocumentTest
from spyne.protocol.yaml import YamlDocument

from spyne import MethodContext
from spyne.application import Application
from spyne.decorator import srpc
from spyne.service import Service
from spyne.server import ServerBase

from spyne.protocol.yaml import yaml
yaml.dumps = yaml.dump
yaml.loads = yaml.load

TestYamlDocument = TDictDocumentTest(yaml, YamlDocument, YamlDocument().out_kwargs)


class Test(unittest.TestCase):
    def test_invalid_input(self):
        class SomeService(Service):
            @srpc()
            def yay():
                pass

        app = Application([SomeService], 'tns',
                                in_protocol=YamlDocument(),
                                out_protocol=YamlDocument())

        server = ServerBase(app)

        initial_ctx = MethodContext(server, MethodContext.SERVER)
        initial_ctx.in_string = [b'{']
        ctx, = server.generate_contexts(initial_ctx)
        assert ctx.in_error.faultcode == 'Client.YamlDecodeError'


if __name__ == '__main__':
    unittest.main()
