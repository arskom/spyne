#!/usr/bin/env python
#
# rpclib - Copyright (C) 2009 Aaron Bickell, Jamie Kirkpatrick
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

from tempfile import mkstemp

from rpclib.application import Application
from rpclib.decorator import srpc
from rpclib.interface.wsdl import Wsdl11
from rpclib.protocol.soap import Soap11
from rpclib.service import ServiceBase
from rpclib.model.primitive import String
from rpclib.model.binary import Attachment
from rpclib.server.wsgi import WsgiApplication

class DocumentArchiver(ServiceBase):
    @srpc(Attachment, _returns=String)
    def archive_document(document):
        '''This method accepts an Attachment object, and returns
        the filename of the archived file
        '''
        fd, fname = mkstemp()
        os.close(fd)

        document.file_name = fname
        document.save_to_file()

        return fname

    @srpc(String, _returns=Attachment)
    def get_archived_document(file_path):
        '''This method loads a document from the specified file path
        and returns it.  If the path isn't found, an exception is
        raised.
        '''

        if not os.path.exists(file_path):
            raise Exception("File [%s] not found"%file_path)

        document = Attachment(file_name=file_path)
        # the service automatically loads the data from the file.
        # alternatively, The data could be manually loaded into memory
        # and loaded into the Attachment like:
        #   document = Attachment(data=data_from_file)
        return document

if __name__=='__main__':
    try:
        from wsgiref.simple_server import make_server
    except ImportError:
        print "Error: example server code requires Python >= 2.5"

    application = Application([DocumentArchiver], 'rpclib.examples.binary',
                interface=Wsdl11(), in_protocol=Soap11(), out_protocol=Soap11())

    server = make_server('127.0.0.1', 7789, WsgiApplication(application))

    print "listening to http://127.0.0.1:7789"
    print "wsdl is at: http://localhost:7789/?wsdl"

    server.serve_forever()
