Hello World
===========

This example uses the simple wsgi webserver included with rpclib to deploy this service.

Declaring a Rpclib Service
--------------------------

This example is available here: http://github.com/arskom/rpclib/blob/master/examples/helloworld.py

::

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
            '''
            Docstrings for service methods appear as documentation in the wsdl
            <b>what fun</b>
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

Dissecting this example: Application is the glue between one or more service definitions,
interface and protocol choices. ::

    from rpclib.application import Application

The srpc decorator exposes methods as remote procedure calls and declares the
data types it accepts and returns. The 's' prefix is short for static. It means
no implicit argument will be passed to the function. In the @rpc case, the
function gets a rpclib.MethodContext instance as first argument.::

    from rpclib.decorator import srpc

We are going to expose the services using the Wsdl 1.1 document standard. The
methods will use Soap 1.1 protocol to communicate with the outside world. Here
we have to import them to give them to the application instantiation. ::

    from rpclib.interface.wsdl import Wsdl11
    from rpclib.protocol.soap import Soap11

ServiceBase is the base class for all soap service definitions. ::

    from rpclib.service import ServiceBase

Import the needed types for this service. The names should be self-explanatory. ::

    from rpclib.model.complex import Iterable
    from rpclib.model.primitive import Integer
    from rpclib.model.primitive import String

Import the transport class. We're writing a server that's going to use HTTP as
transport, so we import the WsgiApplication from the server.wsgi module.

    from rpclib.server.wsgi import WsgiApplication

We start by defining our service. The class name will be publicly seen in the
wsdl document unless explicitly overridden with __service_name__ class
attribute. ::

    class HelloWorldService(ServiceBase):

The srpc decorator flags each method as a soap method, and defines the types
and order of the soap parameters, as well as the type of the return value.
This method takes in a String, an Integer and returns an iterable of Strings,
hence Iterable(String).::

        @srpc(String, Integer, _returns=Iterable(String))

The method itself has nothing special about it whatsoever. All input variables
and return types are standard python objects::

        def say_hello(name, times):
            for i in xrange(times):
                yield 'Hello, %s' % name


You can use any type of python iterable. Here, we chose to use generators.

Deploying the service
---------------------

Now that we have defined our service, we are ready to share it with the outside
world. Rpclib has been tested with several other web servers, This example uses
the python's stock simple wsgi web server; any WSGI-compliant server *should*
work.

This is the required import. ::

    if __name__=='__main__':
        from wsgiref.simple_server import make_server


We configure the python logger to show debugging output. We have to specifically
enable the debug output from the soap handler. That's because the xml formatting
code is enabled only when explicitly requested for performance reasons. ::

        logging.basicConfig(level=logging.DEBUG)
        logging.getLogger('rpclib.protocol.soap._base').setLevel(logging.DEBUG)

We glue the service definition, interface document and input and output protocol
standards, under the targetNamespace 'rpclib.examples.hello.vanilla'. ::

        application = Application([HelloWorldService], 'rpclib.examples.hello.vanilla',
                    interface=Wsdl11(), in_protocol=Soap11(), out_protocol=Soap11())

We then wrap the rpclib application with its wsgi wrapper and register it as the
handler to the wsgi server, and run the http server. ::

        server = make_server('127.0.0.1', 7789, WsgiApplication(application))

        print "listening to http://127.0.0.1:7789"
        print "wsdl is at: http://localhost:7789/?wsdl"

        server.serve_forever()

Here's how you can test your service using suds.::

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


Suds is a separate project for building lightweight (albeit a bit slow)
pure-python soap clients. To learn more visit the project's page:
https://fedorahosted.org/suds/
