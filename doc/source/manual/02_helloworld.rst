
.. _manual-helloworld:

Hello World
===========

This example uses the stock simple wsgi webserver to deploy this service. You
should probably use a full-fledged server when deploying your service for
production purposes.

Defining a Spyne Service
--------------------------

Here we introduce the fundamental mechanisms Spyne offers to expose your
services.

The simpler version of this example is available here: http://github.com/arskom/spyne/blob/master/examples/helloworld_soap.py

Dissecting this example: Application is the glue between one or more service definitions,
interface and protocol choices. ::

    from spyne.application import Application

The srpc decorator exposes methods as remote procedure calls and declares the
data types it accepts and returns. The 's' prefix is short for static. It means
no implicit argument will be passed to the function. In the @rpc case, the
function gets a spyne.MethodContext instance as first argument. ::

    from spyne.decorator import srpc

The methods will use Soap 1.1 protocol to communicate with the outside
world. They're instantiated and passed to the Application constructor. You need
to pass fresh instances to each application instance. ::

    from spyne.protocol.soap import Soap11

ServiceBase is the base class for all service definitions. ::

    from spyne.service import ServiceBase

The names of the needed types for implementing this service should be
self-explanatory. ::

    from spyne.model.complex import Iterable
    from spyne.model.primitive import Integer
    from spyne.model.primitive import String

Our server is going to use HTTP as transport, so we import the WsgiApplication
from the server.wsgi module. It's going to wrap the application instance. ::

    from spyne.server.wsgi import WsgiApplication

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

Deploying the service using Soap via Wsgi
-----------------------------------------

Now that we have defined our service, we are ready to share it with the outside
world.

We are going to use the ubiquitious Http protocol as a transport, using a
Wsgi-compliant http server. This example uses Python's stock simple wsgi web
server. Spyne has been tested with several other web servers. Any
WSGI-compliant server should work.

This is the required import: ::

    if __name__=='__main__':
        from wsgiref.simple_server import make_server

Here, we configure the python logger to show debugging output. We have to
specifically enable the debug output from the soap handler. That's because the
xml formatting code is run only when explicitly enabled for performance
reasons. ::

        logging.basicConfig(level=logging.DEBUG)
        logging.getLogger('spyne.protocol.xml').setLevel(logging.DEBUG)

We glue the service definition, input and output protocols
under the targetNamespace 'spyne.examples.hello.soap': ::

        application = Application([HelloWorldService], 'spyne.examples.hello.soap',
                                        in_protocol=Soap11(), out_protocol=Soap11())

We then wrap the spyne application with its wsgi wrapper: ::

        wsgi_app = WsgiApplication(application)

The above two lines can be replaced with an easier-to-use function that covers
this common use case: ::

        from spyne.util.simple import wsgi_soap_application
        wsgi_app = wsgi_soap_application([HelloWorldService], 'spyne.examples.hello.soap')

We now register the WSGI application as the handler to the wsgi server, and run
the http server: ::

        server = make_server('127.0.0.1', 7789, wsgi_app)

        print "listening to http://127.0.0.1:7789"
        print "wsdl is at: http://localhost:7789/?wsdl"

        server.serve_forever()

.. NOTE::
    * **Django users:** See django wrapper example: https://github.com/arskom/spyne/blob/master/examples/django
    * **Twisted users:** See the these examples that illustrate two ways of
      deploying a Spyne application using Twisted: http://github.com/arskom/spyne/blob/master/examples/twisted

You can test your service using suds. Suds is a separate project for implementing
pure-python soap clients. To learn more visit the project's page:
https://fedorahosted.org/suds/. You can simply install it using
``easy_install suds``.

So here's how you can use suds to test your new spyne service:

::

    from suds.client import Client
    hello_client = Client('http://localhost:7789/?wsdl')
    print hello_client.service.say_hello("Dave", 5)

The script's output would be as follows: ::

    (stringArray){
        string[] =
            "Hello, Dave",
            "Hello, Dave",
            "Hello, Dave",
            "Hello, Dave",
            "Hello, Dave",
        }


Deploying service using HttpRpc via Wsgi
----------------------------------------

This example is available here: http://github.com/arskom/spyne/blob/master/examples/helloworld_http.py.

For the sake of this tutorial, we are going to use HttpRpc as well. HttpRpc is
a Rest-like protocol, but it doesn't care about HTTP verbs (yet). ::

    from spyne.protocol.http import HttpRpc

The HttpRpc serializer does not support complex types. So we will use the
XmlDocument serializer as the out_protocol to prevent the clients from dealing
with Soap cruft. ::

    from spyne.protocol.http import XmlDocument

Besides the imports, the only difference between the SOAP and the HTTP version
is the application instantiation line: ::

        application = Application([HelloWorldService], 'spyne.examples.hello.http',
                                    in_protocol=HttpRpc(), out_protocol=XmlDocument())

Here's how you can test your service using curl: ::

    curl "http://localhost:7789/say_hello?times=5&name=Dave"

If you have HtmlTidy installed, you can use this command to get a more readable
output. ::

    curl "http://localhost:7789/say_hello?times=5&name=Dave" | tidy -xml -indent

The command's output would be as follows: ::

    <?xml version='1.0' encoding='utf8'?>
    <ns1:say_helloResponse xmlns:ns1="spyne.examples.hello.http"
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
^^^^^^^^^^^^

See the :ref:`manual-user-manager` tutorial that will walk you through
defining complex objects and using events.
