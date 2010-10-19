
Hello World
===========
This example uses the simple wsgi webserver included with soaplib to deploy this service.

Declaring a Soaplib Service
---------------------------

::

    from soaplib.service import DefinitionBase
    from soaplib.service import rpc,
    from soaplib.model.primitive import String, Integer
    from soaplib.model.clazz import Array
    from soaplib.pattern.server.wsgi import Application


    class HelloWorldService(SimpleWSGISoapApp):
        @rpc(String,Integer,_returns=Array(String))
        def say_hello(self,name,times):
            results = []
            for i in range(0,times):
                results.append('Hello, %s'%name)
            return results

    if __name__=='__main__':
        try:
            from wsgiref.simple_server import make_server
            server = make_server('localhost', 7789, Application([HelloWorldService], 'tns'))
            server.serve_forever()
        except ImportError:
            print "Error: example server code requires Python >= 2.5"

Dissecting this example: DefinitionBase is the base class for all soap services. ::

    from soaplib.service import DefinitionBase

The rpc decorator exposes methods as soap method and declares the
data types it accepts and returns. ::

    from soaplib.service import rpc

Import the type for this method (more on type later)::

    from soaplib.model.primitive import String, Integer
    from soaplib.model.clazz import Array

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

soaplib has been tested with several other web servers, This example uses the
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
