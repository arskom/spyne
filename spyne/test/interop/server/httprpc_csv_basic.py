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
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('spyne.protocol.xml')
logger.setLevel(logging.DEBUG)

from spyne.test.interop.server import get_open_port
from spyne.application import Application
from spyne.interface.wsdl import Wsdl11
from spyne.protocol.csv import OutCsv
from spyne.protocol.http import HttpRpc
from spyne.server.wsgi import WsgiApplication
from spyne.test.interop.server._service import services

httprpc_csv_application = Application(services,
        'spyne.test.interop.server.httprpc.csv', in_protocol=HttpRpc(), out_protocol=OutCsv())


host = '127.0.0.1'
port = [0]


if __name__ == '__main__':
    try:
        from wsgiref.simple_server import make_server
        from wsgiref.validate import validator

        if port[0] == 0:
            port[0] = get_open_port()

        wsgi_application = WsgiApplication(httprpc_csv_application)
        server = make_server(host, port[0], validator(wsgi_application))

        logger.info('Starting interop server at %s:%s.' % ('0.0.0.0', port[0]))
        logger.info('WSDL is at: /?wsdl')
        server.serve_forever()

    except ImportError:
        print("Error: example server code requires Python >= 2.5")
