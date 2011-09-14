
.. _manual-helloworld:

Hello World
===========

This example uses the stock simple wsgi webserver to deploy this service. You
should probably use a full-fledged server when deploying your
service for production purposes.

Defining an Rpclib Service
--------------------------

This example is available here: http://github.com/arskom/rpclib/blob/master/examples/helloworld_soap.py.
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
        logging.getLogger('rpclib.protocol.soap.soap11').setLevel(logging.DEBUG)

        application = Application([HelloWorldService], 'rpclib.examples.hello.soap',
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
function gets a rpclib.MethodContext instance as first argument. ::

    from rpclib.decorator import srpc

We are going to expose the service definitions using the Wsdl 1.1 document
standard. The methods will use Soap 1.1 protocol to communicate with the outside
world. They're instantiated and passed to the Application constructor. You need
to pass fresh instances to each application instance. ::

    from rpclib.interface.wsdl import Wsdl11
    from rpclib.protocol.soap import Soap11

For the sake of this tutorial, we are going to use HttpRpc as well. It's a
rest-like protocol, but it doesn't care about HTTP verbs (yet). ::

    from rpclib.protocol.http import HttpRpc

The HttpRpc serializer does not support complex types. So we will use the
XmlObject serializer as the out_protocol to prevent the clients from dealing
with Soap cruft. ::

    from rpclib.protocol.http import XmlObject

ServiceBase is the base class for all service definitions. ::

    from rpclib.service import ServiceBase

The names of the needed types for implementing this service should be
self-explanatory. ::

    from rpclib.model.complex import Iterable
    from rpclib.model.primitive import Integer
    from rpclib.model.primitive import String

Our server is going to use HTTP as transport, so we import the WsgiApplication
from the server.wsgi module. It's going to wrap the application instance. ::

    from rpclib.server.wsgi import WsgiApplication

We start by defining our service. The class name will be made public in the
wsdl document unless explicitly overridden with `__service_name__` class
attribute. ::

    class HelloWorldService(ServiceBase):

The srpc decorator flags each method as a remote procedure call and defines the
types and order of the soap parameters, as well as the type of the return value.
This method takes in a string and an integer and returns an iterable of strings,
just like that: ::

        @srpc(String, Integer, _returns=Iterable(String))

The method itself has nothing special about it whatsoever. All input variables
and return types are standard python objects::

        def say_hello(name, times):
            for i in xrange(times):
                yield 'Hello, %s' % name

When returning an iterable, you can use any type of python iterable. Here, we
chose to use generators.

Deploying the service using SOAP
--------------------------------

Now that we have defined our service, we are ready to share it with the outside
world.

We are going to use the ubiquitious Http protocol as a transport, using a
Wsgi-compliant http server. This example uses Python's stock simple wsgi web
server. Rpclib has been tested with several other web servers. Any
WSGI-compliant server should work.

This is the required import. ::

    if __name__=='__main__':
        from wsgiref.simple_server import make_server

Here, we configure the python logger to show debugging output. We have to
specifically enable the debug output from the soap handler. That's because the
xml formatting code is run only when explicitly enabled ror performance
reasons. ::

        logging.basicConfig(level=logging.DEBUG)
        logging.getLogger('rpclib.protocol.soap.soap11').setLevel(logging.DEBUG)

We glue the service definition, interface document and input and output protocols
under the targetNamespace 'rpclib.examples.hello.soap'. ::

        application = Application([HelloWorldService], 'rpclib.examples.hello.soap',
                    interface=Wsdl11(), in_protocol=Soap11(), out_protocol=Soap11())

We then wrap the rpclib application with its wsgi wrapper and register it as the
handler to the wsgi server, and run the http server. ::

        server = make_server('127.0.0.1', 7789, WsgiApplication(application))

        print "listening to http://127.0.0.1:7789"
        print "wsdl is at: http://localhost:7789/?wsdl"

        server.serve_forever()

Here's how you can test your service using suds. ::

    from suds.client import Client
    hello_client = Client('http://localhost:7789/?wsdl')
    result = hello_client.service.say_hello("Dave", 5)
    print result

The script's output would be as follows: ::

    (stringArray){
        string[] =
            "Hello, Dave",
            "Hello, Dave",
            "Hello, Dave",
            "Hello, Dave",
            "Hello, Dave",
        }

Suds is a separate project for building pure-python soap clients. To learn more
visit the project's page: https://fedorahosted.org/suds/. You can simply install
it using `easy_install suds`.

Deploying service using HttpRpc
-------------------------------

This example is available here: http://github.com/arskom/rpclib/blob/master/examples/helloworld_http.py.

The only difference between the SOAP and the HTTP version is the application
instantiation line: ::

        application = Application([HelloWorldService], 'rpclib.examples.hello.http',
                interface=Wsdl11(), in_protocol=HttpRpc(), out_protocol=XmlObject())

We still want to keep Xml as the output protocol as the HttpRpc protocol is
not able to handle complex types.

Here's how you can test your service using wget. ::

    wget "http://localhost:7789/say_hello?times=5&name=Dave" -qO -

If you have HtmlTidy installed, you can use this command to get a more readable
output. ::

    wget "http://localhost:7789/say_hello?times=5&name=Dave" -qO - | tidy -xml -indent

The command's output would be as follows: ::

    <?xml version='1.0' encoding='utf8'?>
    <ns1:say_helloResponse xmlns:ns1="rpclib.examples.hello.http"
    xmlns:ns0="http://schemas.xmlsoap.org/soap/envelope/">
      <ns1:say_helloResult>
        <ns1:string>Hello, Dave</ns1:string>
        <ns1:string>Hello, Dave</ns1:string>
        <ns1:string>Hello, Dave</ns1:string>
        <ns1:string>Hello, Dave</ns1:string>
        <ns1:string>Hello, Dave</ns1:string>
      </ns1:say_helloResult>
    </ns1:say_helloResponse>

What's next?
------------

See the next :ref:`manual-user-manager` tutorial that will walk you through
defining complex objects and using events.
