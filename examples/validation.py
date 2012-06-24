
from datetime import datetime
from spyne.model.primitive import Integer,Unicode
from spyne.decorator import srpc
from spyne.service import ServiceBase

class NameOfMonthService(ServiceBase):
  @srpc(Integer(ge=1,le=12), _returns=Unicode)
  def get_name_of_month(month):
    return datetime(2000,month,1).strftime("%B")


from spyne.application import Application
from spyne.protocol.http import HttpRpc

rest = Application([NameOfMonthService],
        tns='spyne.examples.multiprot',
        in_protocol=HttpRpc(validator='soft'),
        out_protocol=HttpRpc()
    )

import logging

from spyne.server.wsgi import WsgiApplication
from wsgiref.simple_server import make_server

host = '127.0.0.1'
port = 9912

server = make_server(host, port, WsgiApplication(rest))


logging.basicConfig(level=logging.DEBUG)
logging.info("listening to http://%s:%d" % (host,port))

server.serve_forever()
