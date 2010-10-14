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
logger = logging.getLogger('soaplib._base')
logger.setLevel(logging.DEBUG)

from soaplib.test.interop.server._service import application
from soaplib.server.zeromq import Server

if __name__ == '__main__':
    url = "tcp://*:5555"
    server = Server(application, url)
    logging.info("************************")
    logging.info("Use Ctrl+\\ to exit.")
    logging.info("See the 'I can't Ctrl-C my Python/Ruby application. Help!' "
                 "question in http://www.zeromq.org/area:faq for more info.")
    logging.info("listening on %r" % url)
    logging.info("************************")

    server.serve_forever()
