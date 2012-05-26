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

import json
import logging
logging.basicConfig(level=logging.DEBUG)

import unittest

from rpclib import MethodContext
from rpclib.application import Application
from rpclib.decorator import srpc
from rpclib.model.primitive import Integer
from rpclib.model.primitive import Unicode
from rpclib.model.primitive import DateTime
from rpclib.model.primitive import Mandatory
from rpclib.model.complex import ComplexModel
from rpclib.model.complex import Iterable
from rpclib.interface.wsdl import Wsdl11
from rpclib.protocol.json import JsonObject
from rpclib.service import ServiceBase
from rpclib.server import ServerBase

from rpclib.util.xml import get_xml_as_object
from lxml import etree

class Test(unittest.TestCase):
    def test_empty_string(self):
        class a(ComplexModel):
            b = Unicode

        elt = etree.fromstring('<a><b/></a>')
        o = get_xml_as_object(elt, a)

        assert o.b == ''

if __name__ == '__main__':
    unittest.main()
