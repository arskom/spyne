
.. _manual-helloworld:

Hello World
===========

This example uses the stock simple wsgi webserver to deploy this service. You
should probably use a full-fledged server when deploying your service for
production purposes.

Defining a Spyne Service
------------------------

Here we introduce the fundamental mechanisms Spyne offers to expose your
services.

The Soap version of this example is available here: http://github.com/arskom/spyne/blob/master/examples/helloworld_soap.py

Dissecting this example: Application is the glue between one or more service
definitions, interface and protocol choices. ::

    from spyne.application import Application

The ``@srpc`` decorator exposes methods as remote procedure calls and declares
the data types it accepts and returns. The 's' prefix is short for 'static' 
(or stateless, if you will) -- the function receives no implicit arguments.
By contrast, the ``@rpc`` decorator passes a :class:`spyne.MethodContext`
instance as first argument to the user code. ::

    from spyne.decorator import srpc

:class:`spyne.service.Service` is the base class for all service
definitions. ::

    from spyne.service import Service

The names of the needed types for implementing this service should be
self-explanatory. ::

    from spyne.model.complex import Iterable
    from spyne.model.primitive import UnsignedInteger
    from spyne.model.primitive import String

Our server is going to use HTTP as transport, so we import the
``WsgiApplication`` from the `:mod:`spyne.server.wsgi` module. It's going to
wrap the ``Application`` instance. ::

    from spyne.server.wsgi import WsgiApplication

We start by defining our service. The class name will be made public in the
wsdl document unless explicitly overridden with `__service_name__` class
attribute. ::

    class HelloWorldService(Service):

The ``@srpc`` decorator flags each method as a remote procedure call and
defines the types and order of the soap parameters, as well as the type of the
return value. This method takes in a string and an integer and returns an
iterable of strings, just like that: ::

        @srpc(String, UnsignedInteger, _returns=Iterable(String))

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

We are going to use the ubiquitious Http protocol as transport, using a
Wsgi-compliant http server. This example uses Python's stock Wsgi server. Spyne
has been tested with several other web servers, yet, any Wsgi-compliant server
should work.

This is the required import: ::

    from wsgiref.simple_server import make_server

Here, we configure the python logger to show debugging output. We have to
specifically enable the debug output from the soap handler because the
Xml pretty_printing code should be run only when explicitly enabled for
performance reasons. ::

    if __name__=='__main__':
        logging.basicConfig(level=logging.DEBUG)
        logging.getLogger('spyne.protocol.xml').setLevel(logging.DEBUG)

We glue the service definition, input and output protocols
under the "targetNamespace" 'spyne.examples.hello.soap': ::

        app = Application([HelloWorldService], 'spyne.examples.hello.http',
                in_protocol=Soap11(validator='lxml'),
                out_protocol=Soap11(),
            )

In this example, the input validator is on, which means e.g. no negative values
will be let in for the ``times`` argument of the ``say_hello`` function,
because it is marked as ``UnsignedInteger``. For the Soap 1.1 protocol
(actually, for any XML-based protocol), the recommended validator is
``'lxml'`` which uses libxml's native schema validator. It's a fast and robust
option that won't tolerate the slightest anomaly in the request document.

We then wrap the Spyne application with its wsgi wrapper: ::

        wsgi_app = WsgiApplication(app)

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

Now that the server implementation is done, you can run it. Now it's time to
actually make a request to our server to see it working.

You can test your service using suds. Suds is a separate project for
implementing pure-python soap clients. To learn more visit the project's page:
https://fedorahosted.org/suds/. You can simply install it using
``easy_install suds``.

So, here's a three-line script that illustrates how you can use suds to test
your new Spyne service: ::

    from suds.client import Client
    hello_client = Client('http://localhost:8000/?wsdl')
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

The corresponding response document would be: ::

    <?xml version='1.0' encoding='UTF-8'?>
    <senv:Envelope xmlns:tns="spyne.examples.hello.soap" xmlns:senv="http://schemas.xmlsoap.org/soap/envelope/">
      <senv:Body>
        <tns:say_helloResponse>
          <tns:say_helloResult>
            <tns:string>Hello, Dave</tns:string>
            <tns:string>Hello, Dave</tns:string>
            <tns:string>Hello, Dave</tns:string>
            <tns:string>Hello, Dave</tns:string>
            <tns:string>Hello, Dave</tns:string>
          </tns:say_helloResult>
        </tns:say_helloResponse>
      </senv:Body>
    </senv:Envelope>


Deploying the service using HttpRpc/Json
--------------------------------------------

This time, we will use a Http as request protocol, and Json as response
protocol. 

This example is available here: http://github.com/arskom/spyne/blob/master/examples/helloworld_http.py

We will just need to change the Application definition as
follows: ::

    application = Application([HelloWorldService], 'spyne.examples.hello.http',
          in_protocol=HttpRpc(validator='soft'),
          out_protocol=JsonDocument(),
      )

For HttpRpc, the only available validator is ``'soft'``. It is Spyne's own
validation engine that works for all protocols that support it (which
includes every implementation that comes bundled with Spyne).

Same as before, we then wrap the Spyne application with its wsgi wrapper: ::

      wsgi_app = WsgiApplication(application)

We now register the WSGI application as the handler to the wsgi server, and run
the http server: ::

      server = make_server('127.0.0.1', 8000, wsgi_app)

      logging.info("listening to http://127.0.0.1:8000")
      logging.info("wsdl is at: http://localhost:8000/?wsdl")

      server.serve_forever()

Once we run our daemon, we can test it using any Http client. Let's try: ::

    $ curl -s http://localhost:8000/say_hello?name=Dave\&times=3 | python -m json.tool
    [
        "Hello, Dave", 
        "Hello, Dave", 
        "Hello, Dave"
    ]

Spyne tries to make it as easy as possible to work with multiple protocols by
being as configurable as possible without having to alter user code.

What's next?
^^^^^^^^^^^^

Now that you know how to put a simple Spyne service together, let's continue by
reading the :ref:`manual-types` tutorial that will walk you through how native
Python types and Spyne markers interact.
