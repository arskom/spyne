
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

A simpler variation of this example is available here: http://github.com/arskom/spyne/blob/master/examples/helloworld_http.py

Dissecting this example: Application is the glue between one or more service definitions,
interface and protocol choices. ::

    from spyne.application import Application

The ``@srpc`` decorator exposes methods as remote procedure calls and declares
the data types it accepts and returns. The 's' prefix is short for 'static' --
the function receives no implicit arguments. By contrast, the ``@rpc``
decorator passes a :class:`spyne.MethodContext` instance as first argument to
the user code. ::

    from spyne.decorator import srpc

ServiceBase is the base class for all service definitions. ::

    from spyne.service import ServiceBase

The names of the needed types for implementing this service should be
self-explanatory. ::

    from spyne.model.complex import Iterable
    from spyne.model.primitive import Integer
    from spyne.model.primitive import String

Our server is going to use HTTP as transport, so we import the WsgiApplication
from the `:mod:`spyne.server.wsgi` module. It's going to wrap the application
instance. ::

    from spyne.server.wsgi import WsgiApplication

We start by defining our service. The class name will be made public in the
wsdl document unless explicitly overridden with `__service_name__` class
attribute. ::

    class HelloWorldService(ServiceBase):

The srpc decorator flags each method as a remote procedure call and defines the
types and order of the soap parameters, as well as the type of the return value.
This method takes in a string and an integer and returns an iterable of strings,
just like that: ::

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

We are going to use the ubiquitious Http protocol as a transport, using a
Wsgi-compliant http server. This example uses Python's stock Wsgi web server.
Spyne has been tested with several other web servers, yet, any
Wsgi-compliant server should work.

This is the required import: ::

    from wsgiref.simple_server import make_server

Here, we configure the python logger to show debugging output. We have to
specifically enable the debug output from the soap handler. That's because the
xml formatting code is run only when explicitly enabled for performance
reasons. ::

    if __name__=='__main__':
        logging.basicConfig(level=logging.DEBUG)
        logging.getLogger('spyne.protocol.xml').setLevel(logging.DEBUG)

We glue the service definition, input and output protocols
under the targetNamespace 'spyne.examples.hello.soap': ::

    application = Application([HelloWorldService], 'spyne.examples.hello.http',
          in_protocol=Soap11(validator='soft'),
          out_protocol=Soap11(),
      )

In this example, the input validator is on, which means e.g. no negative values
will be let in for the ``times`` argument of the say_hello function, because it
is marked as ``UnsignedInteger``. For Soap11, the recommended validator is
``'lxml'`` which is lxml's native schema validator. It's a fast and robust
option that won't tolerate the slightest anomaly in the request document.

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

You can test your service using suds. Suds is a separate project for
implementing pure-python soap clients. To learn more visit the project's page:
https://fedorahosted.org/suds/. You can simply install it using
``easy_install suds``.

So, here's how you can use suds to test your new Spyne service:

::

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
            <tns:string>Hello, Jérôme</tns:string>
            <tns:string>Hello, Jérôme</tns:string>
            <tns:string>Hello, Jérôme</tns:string>
            <tns:string>Hello, Jérôme</tns:string>
            <tns:string>Hello, Jérôme</tns:string>
          </tns:say_helloResult>
        </tns:say_helloResponse>
      </senv:Body>
    </senv:Envelope>


Deploying the service using the HttpRpc/Json
--------------------------------------------

This time, we will use a Http as request protocol, and Json as response
protocol. We will just need to change the Application definition as
follows: ::

    application = Application([HelloWorldService], 'spyne.examples.hello.http',

For HttpRpc, the only available validator is ``'soft'``. It is Spyne's own
validation engine that works for all protocols that support it (which
include every implementation that comes bundled with Spyne).

          in_protocol=HttpRpc(validator='soft'),

The skip_depth parameter to JsonDocument simplifies the reponse dict by
skipping outer response structures that are redundant when the client keeps
track of which reponse document corresponds to which request.

          out_protocol=JsonDocument(skip_depth=1),
      )

We then wrap the Spyne application with its wsgi wrapper: ::

      wsgi_app = WsgiApplication(application)

We now register the WSGI application as the handler to the wsgi server, and run
the http server: ::

      server = make_server('127.0.0.1', 8000, wsgi_app)

      logging.info("listening to http://127.0.0.1:8000")
      logging.info("wsdl is at: http://localhost:8000/?wsdl")

      server.serve_forever()

Once we run our daemon, we can test it using any Http client. Let's try:

    $ curl -s http://localhost:8000/say_hello?name=Dave\&times=3 | python -m json.tool
    [
        "Hello, Dave", 
        "Hello, Dave", 
        "Hello, Dave"
    ]

If we had passed ``skip_depth=0`` to the output protocol, we'd have a
slightly different response:

    $ curl -s http://localhost:8000/say_hello?name=Dave\&times=3 | python -m json.tool
    {
        "say_helloResponse": {
            "say_helloResult": {
                "string": [
                    "Hello, Dave",
                    "Hello, Dave",
                    "Hello, Dave"
                ]
            }
        }
    }

Please note how this corresponds to the structure in the Soap response. Spyne
tries to make it as easy as possible to work with multiple protocols by being
as configurable as possible without having to alter user code.

What's next?
^^^^^^^^^^^^

See the :ref:`manual-user-manager` tutorial that will walk you through
defining complex objects and using events.
