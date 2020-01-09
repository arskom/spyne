
'''
This is a simple HelloWorld example showing how the NullServer works. The
NullServer is meant to be used mainly for testing.
'''

import logging
logging.basicConfig(level=logging.INFO)

from pprint import pprint

from spyne.application import Application
from spyne.protocol.soap import Soap11
from spyne.server.null import NullServer

from spyne.decorator import rpc
from spyne.service import Service
from spyne.model.complex import Iterable
from spyne.model.primitive import Integer
from spyne.model.primitive import Unicode


class HelloWorldService(Service):
    @rpc(Unicode, Integer, _returns=Iterable(Unicode))
    def say_hello(ctx, name, times):
        for i in range(times):
            yield u'Hello, %s' % name


if __name__=='__main__':
    application = Application([HelloWorldService], 'spyne.examples.hello.soap',
                in_protocol=Soap11(validator='lxml'),
                out_protocol=Soap11(pretty_print=True),
            )

    # disables context markers. set logging level to logging.INFO to enable
    # them.
    logging.getLogger('spyne.server.null').setLevel(logging.CRITICAL)

    print("With serialization")
    print("==================")
    print()

    null = NullServer(application, ostr=True)
    ret_stream = null.service.say_hello('Dave', 5)
    ret_string = ''.join(i.decode() for i in ret_stream)
    print(ret_string)
    print()

    print("Without serialization")
    print("=====================")
    print()

    null = NullServer(application, ostr=False)
    ret = null.service.say_hello('Dave', 5)
    # because the return value is a generator, we need to iterate over it to
    # see the actual return values.
    pprint(list(ret))
