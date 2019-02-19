#!/usr/bin/env python

import logging
logging.basicConfig(level=logging.DEBUG)

from spyne import Application, rpc, ServiceBase, \
    Integer, Unicode

from spyne import Iterable

from spyne.protocol.soap import Soap11

from spyne.server.twisted import TwistedWebResource

from twisted.internet import reactor
from twisted.web.server import Site

class HelloWorldService(ServiceBase):
    @rpc(Unicode, Integer, _returns=Iterable(Unicode))
    def say_hello(ctx, name, times):
        for i in range(times):
            yield 'Hello, %s' % name

application = Application([HelloWorldService],
    tns='spyne.examples.hello',
    in_protocol=Soap11(validator='lxml'),
    out_protocol=Soap11()
)

if __name__ == '__main__':
    resource = TwistedWebResource(application)
    site = Site(resource)

    reactor.listenTCP(8000, site, interface='0.0.0.0')
    reactor.run()


