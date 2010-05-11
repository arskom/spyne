Simple Client
=============

Soaplib provides a couple different ways of calling remote SOAP web services.
The most straightforward is by creating a service 'stub', which contains all the
operations in the service. We have already seen this in the HelloWorld example. ::

    >>> from soaplib.client import make_service_client
    >>> client = make_service_client('http://localhost:7789/',HelloWorldService())
    >>> print client.say_hello("Dave",5)
    ['Hello, Dave','Hello, Dave','Hello, Dave','Hello, Dave','Hello, Dave']

In this case, the 'HelloWorldService?' served as both as the server and client
stub implementation, but the client only requires that the method definitions
and decorators match those in the remote service. The 'make_service_client' is a
convenience method that wraps the 'ServiceClient?' class.

Non-soaplib Client 
==================

By default a soaplib webservice uses the full module+class name as the namespace
of the service, but when calling non-soaplib services, this probably won't be
the case. The '@soapmethod' decorator has additional keyword arguments that
allow the user to specify the message names and namespaces for each method. The
easiest way to specify the namespace of a message is by using the ElementTree
module's QName syntax (ie. '{namespace}name'). ::

    class StockQuoteService(SimpleWSGISoapApp):
    
        @soapmethod(    String,
                        _returns=Float,
                        _inMessage='{http://quickstart.samples/xsd}getPrice',
                        _outMessage='{http://quickstart.samples/xsd}getPriceResponse',
                        _outVariableName='return')
        def getPrice(self,symbol):
            pass

This example is a simple client to access the simple stock quote service which
ships as a sample from the Apache Axis2 project. The target namespace (tns) can
also be specified at the service level to apply to all messages in a given
service. Note: specifying the namespace using the ElementTree QName syntax
overrides the namespace at the class level. ::

    class StockQuoteService(SimpleWSGISoapApp):
        __tns__ = 'http://quickstart.samples/xsd'
    
        @soapmethod(    String,
                        _returns=Float,
                        _inMessage='getPrice',
                        _outMessage='getPriceResponse',
                        _outVariableName='return')
        def getPrice(self,symbol):
            pass

It just so happens that the Axis2 and soaplib message naming conventions are the
same ( using the method name for the input message, and method + 'Response' for
the output message), so specifying them explicitly is not needed. This service
can alternatively be written as::

    class StockQuoteService(SimpleWSGISoapApp):
        __tns__ = 'http://quickstart.samples/xsd'
    
        @soapmethod(    String,
                        _returns=Float,
                        _outVariableName='return')
        def getPrice(self,symbol):
            pass

Note: the output variable names are still different, soaplib uses 'retval',
Apache Axis2 uses 'return'.
