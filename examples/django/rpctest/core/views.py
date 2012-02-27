from rpclib.server.django import DjangoApplication
from rpclib.model.primitive import String, Integer
from rpclib.model.complex import Iterable
from rpclib.service import ServiceBase
from rpclib.interface.wsdl import Wsdl11
from rpclib.protocol.soap import Soap11
from rpclib.application import Application
from rpclib.decorator import rpc

class HelloWorldService(ServiceBase):
    @rpc(String, Integer, _returns=Iterable(String))
    def say_hello(ctx, name, times):
        for i in xrange(times):
            yield 'Hello, %s' % name

hello_world_service = DjangoApplication(Application([HelloWorldService],
        'some.tns',
        interface=Wsdl11(),
        in_protocol=Soap11(),
        out_protocol=Soap11()
    ))
