Hello World
===========
This example uses the simple wsgi webserver included with rpclib to deploy this service.

Declaring a Rpclib Service
---------------------------
::

    #!/usr/bin/env python

    import logging

    from rpclib.application import Application
    from rpclib.decorator import srpc
    from rpclib.interface.wsdl import Wsdl11
    from rpclib.protocol.soap import Soap11
    from rpclib.service import ServiceBase
    from rpclib.model.complex import Iterable
    from rpclib.model.primitive import Integer
    from rpclib.model.primitive import String
    from rpclib.server.wsgi import WsgiApplication


    class HelloWorldService(ServiceBase):
        @srpc(String, Integer, _returns=Iterable(String))
        def say_hello(name, times):
            '''Docstrings for service methods appear as documentation in the wsdl
            <b>what fun.</b>

            @param name the name to say hello to
            @param the number of times to say hello
            @return the completed array
            '''

            for i in xrange(times):
                yield 'Hello, %s' % name

    if __name__=='__main__':
        try:
            from wsgiref.simple_server import make_server
        except ImportError:
            print "Error: example server code requires Python >= 2.5"

        logging.basicConfig(level=logging.DEBUG)
        logging.getLogger('rpclib.protocol.soap._base').setLevel(logging.DEBUG)

        application = Application([HelloWorldService], 'rpclib.examples.hello.vanilla',
                interface=Wsdl11(), in_protocol=Soap11(), out_protocol=Soap11())

        server = make_server('127.0.0.1', 7789, WsgiApplication(application))

        print "listening to http://127.0.0.1:7789"
        print "wsdl is at: http://localhost:7789/?wsdl"

        server.serve_forever()

Dissecting this example: ServiceBase is the base class for all soap services. ::

    from rpclib.service import ServiceBase

The rpc decorator exposes methods as remote procedure calls and declares the
data types it accepts and returns. ::

    from rpclib.decorator import srpc

Import the type for this method (more on type later)::

    from rpclib.model.primitive import String, Integer
    from rpclib.model.clazz import Array

Extending DefinitionBase is an easy way to create a soap service that can
be deployed as a WSGI application.::

    class HelloWorldService(DefinitionBase):

The rpc decorator flags each method as a soap method, and defines
the types and order of the soap parameters, as well as the return value.
This method takes in a String, an Integer and returns an
Array of Strings -> Array(String).::

    @rpc(String,Integer,_returns=Array(String))

The method itself has nothing special about it whatsoever. All input
variables and return types are standard python objects::

    def say_hello(self,name,times):
        results = []
        for i in range(0,times):
            results.append('Hello, %s'%name)
        return results

Deploying the service
---------------------

rpclib has been tested with several other web servers, This example uses the
simple wsgi web server; any WSGI-compliant server *should* work.::

    if __name__=='__main__':
        try:
            from wsgiref.simple_server import make_server
            server = make_server('localhost', 7789, Application([HelloWorldService], 'tns'))
            server.serve_forever()
        except ImportError:
            print "Error: example server code requires Python >= 2.5"

Calling this service ::

    >>> from suds.client import Client
    >>> hello_client = Client('http://localhost:7789/?wsdl')
    >>> result = hello_client.service.say_hello("Dave", 5)
    >>> print result

    (stringArray){
       string[] =
          "Hello, Dave",
          "Hello, Dave",
          "Hello, Dave",
          "Hello, Dave",
          "Hello, Dave",
     }


suds is a separate project for building lightweight soap clients in python to learn more
visit the project's page https://fedorahosted.org/suds/
