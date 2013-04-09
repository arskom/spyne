
import logging
logger = logging.getLogger(__name__)

from spyne.protocol.http import HttpRpc
from spyne.protocol.json import JsonDocument
from spyne.server.wsgi import WsgiApplication

from template.application import MyApplication
from template.db import TableModel

from template.entity.user import UserManagerService

from wsgiref.simple_server import make_server

def main():
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('spyne.protocol.xml').setLevel(logging.DEBUG)
    logging.getLogger('sqlalchemy.engine.base.Engine').setLevel(logging.DEBUG)

    application = MyApplication([UserManagerService],
                'spyne.examples.user_manager',
                in_protocol=HttpRpc(validator='soft'),
                out_protocol=JsonDocument(skip_depth=1),
            )

    wsgi_app = WsgiApplication(application)
    server = make_server('127.0.0.1', 8000, wsgi_app)

    TableModel.Attributes.sqla_metadata.create_all(checkfirst=True)
    logging.info("listening to http://127.0.0.1:8000")
    logging.info("wsdl is at: http://localhost:8000/?wsdl")

    return server.serve_forever()
