Hello World
===========
This example uses the CherryPy webserver to deploy this service.

Declaring a Soaplib Service
---------------------------

::

    from soaplib.wsgi_soap import SimpleWSGISoapApp
    from soaplib.service import soapmethod
    from soaplib.serializers.primitive import String, Integer, Array
    
    class HelloWorldService(SimpleWSGISoapApp):
    
        @soapmethod(String,Integer,_returns=Array(String))
        def say_hello(self,name,times):
            results = []
            for i in range(0,times):
                results.append('Hello, %s'%name)
            return results
            
    if __name__=='__main__':
        from cherrypy._cpwsgiserver import CherryPyWSGIServer
        # this example uses CherryPy2.2, use cherrypy.wsgiserver.CherryPyWSGIServer for CherryPy 3.0
        server = CherryPyWSGIServer(('localhost',7789),HelloWorldService())
        server.start()

Dissecting this example: SimpleWSGISoapApp is the base class for WSGI soap services. ::

    from soaplib.wsgi_soap import SimpleWSGISoapApp

The soapmethod decorator exposes methods as soap method and declares the
data types it accepts and returns. ::

    from soaplib.service import soapmethod

Import the serializers for this method (more on serializers later)::

    from soaplib.serializers.primitive import String, Integer, Array

Extending SimpleWSGISoapApp is an easy way to soap service that can
be deployed as a WSGI application.::

    class HelloWorldService(SimpleWSGISoapApp):

The soapmethod decorator flags each method as a soap method, and defines
the types and order of the soap parameters, as well as the return value.
This method takes in a String, an Integer and returns an 
Array of Strings -> Array(String).::

    @soapmethod(String,Integer,_returns=Array(String))

The method itself has nothing special about it whatsoever. All input 
variables and return types are standard python objects::

    def say_hello(self,name,times):
        results = []
        for i in range(0,times):
            results.append('Hello, %s'%name)
        return results

Deploying the service 
---------------------

oaplib has been tested with several other web servers, This example uses the
CherryPy WSGI web server to and any WSGI-compliant server *should* work.::
    
    if __name__=='__main__':
        from cherrypy._cpwsgiserver import CherryPyWSGIServer
        server = CherryPyWSGIServer(('localhost',7789),HelloWorldService())
        server.start()

Calling this service ::

    >>> from soaplib.client import make_service_client
    >>> from helloworld import HelloWorldService
    >>> client = make_service_client('http://localhost:7789/',HelloWorldService())
    >>> print client.say_hello("Dave",5)
    
    ['Hello, Dave','Hello, Dave','Hello, Dave','Hello, Dave','Hello, Dave']

soaplib.client.make_service_client is a utility method to construct a callable
client to the remote web service. make_service_client takes the url of the
remote functionality, as well as a _stub_ of the remote service. As in this
case, the _stub_ can be the instance of the remote functionality, however the
requirements are that it just have the same method signatures and definitions as
the server implementation.
