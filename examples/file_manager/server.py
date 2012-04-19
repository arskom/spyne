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

import logging
logger = logging.getLogger(__name__)
import os

from werkzeug.wsgi import DispatcherMiddleware
from werkzeug.exceptions import NotFound
from werkzeug.serving import run_simple

from rpclib.application import Application
from rpclib.decorator import rpc
from rpclib.service import ServiceBase
from rpclib.error import ResourceNotFoundError
from rpclib.error import ValidationError
from rpclib.model.binary import ByteArray
from rpclib.model.binary import File
from rpclib.model.primitive import Unicode
from rpclib.model.primitive import Mandatory
from rpclib.server.wsgi import WsgiApplication
from rpclib.protocol.http import HttpRpc


BLOCK_SIZE = 8192
port = 9000


class FileServices(ServiceBase):
    @rpc(Mandatory.Unicode, _returns=ByteArray)
    def get(ctx, file_name):
        try:
            f = open(file.path, 'r')
        except IOError:
            raise ResourceNotFoundError(file_name)

        data = f.read(BLOCK_SIZE)
        while len(data) > 0:
            yield data

            data = f.read(BLOCK_SIZE)

        f.close()

    @rpc(String, String, File.customize(min_occurs=1, nullable=False), _returns=Unicode)
    def add(ctx, person_type, action, file):
        logger.info("Person Type: %r" % person_type)
        logger.info("Action: %r" % action)

        path = os.path.join(os.path.abspath('./files'), file.name)
        if not path.startswith(os.path.abspath('./files')):
            raise ValidationError(file.name)

        f = open(path, 'w') # if this fails, the client will see an
                            # internal error.

        try:
            for data in file.data:
                f.write(data)

            logger.debug("File written: %r" % file.name)

            f.close()

        except:
            f.close()
            os.remove(file.name)
            logger.debug("File removed: %r" % file.name)
            raise # again, the client will see an internal error.

        return "Tamam."

def main():
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('rpclib.wsgi').setLevel(logging.DEBUG)

    filemgr_app = WsgiApplication(Application([FileServices],
        'rpclib.examples.file_manager', HttpRpc(validator='soft'), HttpRpc()))
    try:
        os.makedirs('./files')
    except OSError:
        pass

    wsgi_app = DispatcherMiddleware(NotFound(), {'/filemgr': filemgr_app})


    run_simple('localhost', port, wsgi_app, static_files={'/': 'static'},
                                                                  threaded=True)

if __name__ == '__main__':
    import sys
    sys.exit(main())
