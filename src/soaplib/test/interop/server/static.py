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

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('soaplib.wsgi')
logger.setLevel(logging.DEBUG)

import os

import twisted.web.server
import twisted.web.static
from twisted.python import log
from twisted.web.wsgi import WSGIResource
from twisted.internet import reactor

from soaplib.test.interop.server._service import application

port = 9754
static_dir = os.path.abspath(".")
url = 'app'

def main(argv):
    observer = log.PythonLoggingObserver('twisted')
    log.startLoggingWithObserver(observer.emit,setStdout=False)

    logging.info("registering static folder %r on /" % static_dir)

    root = twisted.web.static.File(static_dir)

    resource = WSGIResource(reactor, reactor, application)
    logging.info("registering %r on /%s" % (application, url))
    root.putChild(url, resource)

    site = twisted.web.server.Site(root)

    reactor.listenTCP(port, site)
    logging.info("listening on: 0.0.0.0:%d" % port)
    logging.info('WSDL is at: /app/?wsdl')

    return reactor.run()

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
