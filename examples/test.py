
from rpclib.model.complex import ComplexModel
from rpclib.model.primitive import String
from rpclib.service import ServiceBase
from rpclib.application import Application
from rpclib.decorator import rpc
from rpclib.interface.wsdl import Wsdl11
from rpclib.protocol.soap import Soap11
from rpclib.server.wsgi import WsgiApplication
from rpclib.util.wsgi_wrapper import run_twisted

class state_only(ComplexModel):
    state = String

class testt(ServiceBase):
    @rpc(String, String, _returns=state_only)
    def testf(ctx, first, second):
        result = state_only()
        result.state = "test"
        return result

application = Application([testt], 'tns',
            interface=Wsdl11(), in_protocol=Soap11(), out_protocol=Soap11())

if __name__ == '__main__':
    wsgi_app = WsgiApplication(application)

    print 'listening on 0.0.0.0:7789'
    print 'wsdl is at: http://0.0.0.0:7789/app/?wsdl'

    run_twisted( ( (wsgi_app, "app"),), 7789)
