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

"""pod being plain old data"""

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('spyne.protocol.xml')
logger.setLevel(logging.DEBUG)

from spyne.test.interop.server import get_open_port
from spyne.application import Application
from spyne.test.interop.server._service import services
from spyne.protocol.http import HttpRpc
from spyne.server.twisted import TwistedWebResource

httprpc_soap_application = Application(services,
                                'spyne.test.interop.server.httprpc.pod',
                                in_protocol=HttpRpc(), out_protocol=HttpRpc())

host = '127.0.0.1'
port = [0]

def main(argv):
    from twisted.web.server import Site
    from twisted.internet import reactor
    from twisted.python import log
    observer = log.PythonLoggingObserver('twisted')
    log.startLoggingWithObserver(observer.emit, setStdout=False)

    if port[0] == 0:
        port[0] = get_open_port()

    wr = TwistedWebResource(httprpc_soap_application)
    site = Site(wr)

    reactor.listenTCP(port[0], site)
    logging.info("listening on: %s:%d" % (host,port[0]))

    return reactor.run()


if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
