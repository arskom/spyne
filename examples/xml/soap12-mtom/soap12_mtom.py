#!/usr/bin/env python

import logging
logger = logging.getLogger(__name__)

import os
logging.basicConfig(level=logging.DEBUG)
logging.getLogger('spyne.protocol.xml').setLevel(logging.DEBUG)

from spyne.application import Application
from spyne.decorator import rpc
from spyne.service import ServiceBase
from spyne.model.complex import ComplexModel
from spyne.model.binary import ByteArray
from spyne.model.primitive import Unicode
from spyne.server.wsgi import WsgiApplication
from spyne.protocol.soap import Soap12


tns = 'http://gib.gov.tr/vedop3/eFatura'


class documentResponse(ComplexModel):
    msg = Unicode
    hash = ByteArray


class GIBSoapService(ServiceBase):
    @rpc(Unicode(sub_name="fileName"), ByteArray(sub_name='binaryData'),
                          ByteArray(sub_name="hash"), _returns=documentResponse)
    def documentRequest(ctx, file_name, file_data, data_hash):
        incoming_invoice_dir = os.getcwd()

        logger.info("file_name  %r" % file_name)
        logger.info("file_hash: %r" % data_hash)

        path = os.path.join(incoming_invoice_dir, file_name)

        f = open(path, 'wb')
        for data in file_data:
            f.write(data)
        logger.info("File written: %r" % file_name)
        f.close()

        resp = documentResponse()
        resp.msg = "Document was written successfully"
        resp.hash = data_hash

        return resp


application = Application([GIBSoapService], tns=tns,
                          in_protocol=Soap12(),
                          out_protocol=Soap12())


gib_application = WsgiApplication(application)


from wsgiref.simple_server import make_server


server = make_server('0.0.0.0', 8000, gib_application)
server.serve_forever()
