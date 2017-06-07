#!/usr/bin/env python

from __future__ import absolute_import

from spyne import Service, rpc, Application, Fault
from spyne.server.null import NullServer
from spyne.util.color import G


class SomeService(Service):
    @rpc()
    def server_exception(ctx):
        raise Exception("boo!")

    @rpc()
    def server_fault(ctx):
        raise Fault("Server", "boo and you know it!")

    @rpc()
    def client_fault(ctx):
        raise Fault("Client", "zzzz...")


server = NullServer(Application([SomeService], 'spyne.examples.logging'))


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)

    logging.info(G("all fault tracebacks are logged"))
    logging.getLogger('spyne.application').setLevel(logging.DEBUG)

    try:
        server.service.server_exception()
    except:
        pass
    try:
        server.service.server_fault()
    except:
        pass
    try:
        server.service.client_fault()
    except:
        pass

    logging.info(G("client fault tracebacks are hidden"))
    logging.getLogger('spyne.application.client').setLevel(logging.CRITICAL)
    try:
        server.service.server_fault()
    except:
        pass
    try:
        server.service.client_fault()
    except:
        pass
