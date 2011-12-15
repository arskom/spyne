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
        print("Error: example server code requires Python >= 2.5")

    application = Application([DocumentArchiver], 'rpclib.examples.binary',
                interface=Wsdl11(), in_protocol=HttpRpc(), out_protocol=HttpRpc())

    logging.basicConfig(level=logging.DEBUG)

    server = make_server('127.0.0.1', 7789, WsgiApplication(application))
    print("listening to http://127.0.0.1:7789")
    print("wsdl is at: http://localhost:7789/?wsdl")

    server.serve_forever()
