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

from soaplib.test.interop.server._service import application

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('soaplib.wsgi')
logger.setLevel(logging.DEBUG)

if __name__ == '__main__':
    try:
        from wsgiref.simple_server import make_server
        server = make_server('127.0.0.1', 9753, application)
        print 'Starting interop server at -- %s:%s' % ('127.0.0.1', 9753)
        server.serve_forever()

    except ImportError:
        print "Error: example server code requires Python >= 2.5"
