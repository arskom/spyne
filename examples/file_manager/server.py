#!/usr/bin/env python
# encoding: utf8
#
# Copyright © Burak Arslan <burak at arskom dot com dot tr>,
#             Arskom Ltd. http://www.arskom.com.tr
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    1. Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#    2. Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#    3. Neither the name of the owner nor the names of its contributors may be
#       used to endorse or promote products derived from this software without
#       specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
# OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

import logging
logger = logging.getLogger(__name__)
import os

from werkzeug.wsgi import DispatcherMiddleware
from werkzeug.exceptions import NotFound
from werkzeug.serving import run_simple

from spyne.application import Application
from spyne.decorator import rpc
from spyne.service import Service
from spyne.error import ResourceNotFoundError
from spyne.error import ValidationError
from spyne.model.binary import ByteArray
from spyne.model.binary import File
from spyne.model.primitive import Unicode
from spyne.model.primitive import Mandatory
from spyne.server.wsgi import WsgiApplication
from spyne.protocol.http import HttpRpc


BLOCK_SIZE = 8192
port = 9000


class FileServices(Service):
    @rpc(Mandatory.Unicode, _returns=ByteArray)
    def get(ctx, file_name):
        path = os.path.join(os.path.abspath('./files'), file_name)
        if not path.startswith(os.path.abspath('./files')):
            raise ValidationError(file_name)

        try:
            f = open(path, 'r')
        except IOError:
            raise ResourceNotFoundError(file_name)

        ctx.transport.resp_headers['Content-Disposition'] = (
                                         'attachment; filename=%s;' % file_name)

        data = f.read(BLOCK_SIZE)
        while len(data) > 0:
            yield data

            data = f.read(BLOCK_SIZE)

        f.close()

    @rpc(Unicode, Unicode, File.customize(min_occurs=1, nullable=False), _returns=Unicode)
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
    logging.getLogger('spyne.wsgi').setLevel(logging.DEBUG)

    filemgr_app = WsgiApplication(Application([FileServices],
            tns='spyne.examples.file_manager',
            in_protocol=HttpRpc(validator='soft'),
            out_protocol=HttpRpc()
        ))

    try:
        os.makedirs('./files')
    except OSError:
        pass

    wsgi_app = DispatcherMiddleware(NotFound(), {'/filemgr': filemgr_app})

    logger.info("navigate to: http://localhost:9000/index.html")
    return run_simple('localhost', port, wsgi_app, static_files={'/': 'static'},
                                                                  threaded=True)

if __name__ == '__main__':
    import sys
    sys.exit(main())
