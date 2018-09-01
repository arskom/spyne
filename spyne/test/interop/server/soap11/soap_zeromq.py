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

from spyne.test.interop.server import get_open_port
from spyne.test.interop.server.soap11.soap_http_basic import soap11_application

from spyne.server.zeromq import ZeroMQServer


host = '127.0.0.1'
port = [0]


def main():
    if port[0] == 0:
        port[0] = get_open_port()
    url = "tcp://%s:%d" % (host, port[0])

    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('spyne.protocol.xml').setLevel(logging.DEBUG)

    server = ZeroMQServer(soap11_application, url)
    logging.info("************************")
    logging.info("Use Ctrl+\\ to exit if Ctrl-C does not work.")
    logging.info("See the 'I can't Ctrl-C my Python/Ruby application. Help!' "
                 "question in http://www.zeromq.org/area:faq for more info.")
    logging.info("listening on %r" % url)
    logging.info("************************")

    server.serve_forever()


if __name__ == '__main__':
    main()