from soaplib.wsgi_soap import SimpleWSGISoapApp
from soaplib.service import soapmethod
from soaplib.serializers.primitive import String, Integer, Array
from soaplib.wsgi_soap import request

from time import time
from wsgiref.simple_server import make_server


'''
This example is an enhanced version of the HelloWorld example that
uses service 'hooks' to apply cross-cutting behavior to the service.
In this example, the service hooks are used to gather performance 
information on both the method execution as well as the duration 
of the entire call, including serialization and deserialization. The
available hooks are:

    * onCall
    * onWsdl
    * onWsdlException
    * onMethodExec
    * onResults
    * onException
    * onReturn
    
These method can be used to easily apply cross-cutting functionality
accross all methods in the service to do things like database transaction
management, logging and measuring performance.  This example also 
employs the threadlocal request (soaplib.wsgi_soap.request) object
to hold the data points for this request.
'''

class HelloWorldService(SimpleWSGISoapApp):
    
    @soapmethod(String,Integer,_returns=Array(String))
    def say_hello(self,name,times):
        results = []
        raise Exception("this is some crazy crap")
        for i in range(0,times):
            results.append('Hello, %s'%name)
        return results
    
    def onCall(self,environ):
        request.additional['call_start'] = time()

    def onMethodExec(self,environ,body,py_params,soap_params):
        request.additional['method_start'] = time()

    def onResults(self,environ,py_results,soap_results):
        request.additional['method_end'] = time()

    def onReturn(self,environ,returnString):
        call_start = request.additional['call_start']
        call_end = time()
        method_start = request.additional['method_start']
        method_end = request.additional['method_end']
        
        print 'Method took [%s] - total execution time[%s]'%(method_end-method_start,call_end-call_start)
        

def make_client():
    from soaplib.client import make_service_client
    client = make_service_client('http://localhost:7889/',HelloWorldService())
    return client
    
if __name__=='__main__':
    server = make_server('localhost', 7889, HelloWorldService())
    server.serve_forever()
