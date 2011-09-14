#!/usr/bin/env python
# encoding: utf8
#
# rpclib - Copyright (C) Rpclib contributors
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

import os
import logging

from tempfile import mkstemp

from rpclib.application import Application
from rpclib.decorator import rpc
from rpclib.decorator import srpc
from rpclib.interface.wsdl import Wsdl11
from rpclib.model.binary import ByteArray
from rpclib.model.fault import Fault
from rpclib.model.primitive import String
from rpclib.protocol.http import HttpRpc
from rpclib.service import ServiceBase
from rpclib.server.wsgi import WsgiApplication

class DocumentArchiver(ServiceBase):
    @rpc(ByteArray, _returns=String)
    def put(ctx, content):
        '''This method accepts an Attachment object, and returns the filename
        of the archived file.
        '''
        if content is None:
            raise Fault("Client.BadRequest")

        fd, fname = mkstemp()
        os.close(fd)

        f = open(fname, 'wb')

        for chunk in content:
            f.write(chunk)
        f.close()

        return fname

    @srpc(String, _returns=ByteArray)
    def get(file_path):
        '''This method loads a document from the specified file path
        and returns it. If the path isn't found, an exception is
        raised.
        '''

        if file_path is None:
            raise Fault("Client", "file_path is mandatory")

        if not os.path.exists(file_path):
            raise Fault("Client.FileName", "File '%s' not found" % file_path)

        document = open(file_path, 'rb').read()


        # the service automatically loads the data from the file.
        # alternatively, The data could be manually loaded into memory
        # and loaded into the Attachment like:
        #   document = Attachment(data=data_from_file)
        return [document]

if __name__=='__main__':
    try:
        from wsgiref.simple_server import make_server
    except ImportError:
        print "Error: example server code requires Python >= 2.5"

    application = Application([DocumentArchiver], 'rpclib.examples.binary',
                interface=Wsdl11(), in_protocol=HttpRpc(), out_protocol=HttpRpc())

    logging.basicConfig(level=logging.DEBUG)

    server = make_server('127.0.0.1', 7789, WsgiApplication(application))
    print "listening to http://127.0.0.1:7789"
    print "wsdl is at: http://localhost:7789/?wsdl"

    server.serve_forever()
