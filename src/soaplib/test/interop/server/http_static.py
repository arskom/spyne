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

from twisted.python import log

from soaplib.test.interop.server._service import application
from soaplib.util.server import run_twisted
from soaplib.server import wsgi

port = 9754
url = 'app'

def main(argv):
    observer = log.PythonLoggingObserver('twisted')
    log.startLoggingWithObserver(observer.emit, setStdout=False)

    wsgi_application = wsgi.Application(application)

    return run_twisted( [ (wsgi_application, url) ], port )

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
