from spyne.application import Application
from spyne.protocol.msgpack import MessagePackRpc
from spyne.service import ServiceBase
from spyne.decorator import srpc
from spyne.model.primitive import Unicode

class RadianteRPC(ServiceBase):    
    @srpc(_returns=Unicode)
    def whoami():
        return "Hello I am Seldon!"

app = Application(
    [RadianteRPC],
    tns="radiante.rpc",
    in_protocol=MessagePackRpc(validator="soft"),
    out_protocol=MessagePackRpc()
)

import logging
logging.basicConfig(level=logging.DEBUG)
