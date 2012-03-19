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

"""pod being plain old data"""

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('rpclib.protocol.xml')
logger.setLevel(logging.DEBUG)

from rpclib.application import Application
from rpclib.test.interop.server._service import services
from rpclib.protocol.http import HttpRpc
from rpclib.interface.wsdl import Wsdl11
from rpclib.server.twisted_ import TwistedWebResource

httprpc_soap_application = Application(services,
        'rpclib.test.interop.server.httprpc.pod', HttpRpc(), HttpRpc(), Wsdl11())

host = '127.0.0.1'
port = 9758

def main(argv):
    from twisted.python import log
    from twisted.web.server import Site
    from twisted.web.static import File
    from twisted.internet import reactor
    from twisted.python import log

    observer = log.PythonLoggingObserver('twisted')
    log.startLoggingWithObserver(observer.emit, setStdout=False)

    wr = TwistedWebResource(httprpc_soap_application)
    site = Site(wr)

    reactor.listenTCP(port, site)
    logging.info("listening on: %s:%d" % (host,port))

    return reactor.run()

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
