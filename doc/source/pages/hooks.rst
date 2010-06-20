
Hooks
=====

This example is an enhanced version of the HelloWorld example that uses service
'hooks' to apply cross-cutting behavior to the service. In this example, the
service hooks are used to gather performance information on both the method
execution as well as the duration of the entire call, including serialization
and deserialization. The available hooks are:

    * on_call 

        This is the first thing called in the service

    * on_wsdl 

        Called before the wsdl is requested

    * on_wsdl_exception 

        Called after an exception was thrown when generating the wsdl (shouldn't happen very much)

    * on_method_exec 

        Called right before the service method is executed

    * on_results 

        Called right after the service method is executed

    * on_exception 

        Called after an exception occurred in either the service method or in serialization

    * on_return 

        This is the very last thing called before the wsgi app exits

These method can be used to easily apply cross-cutting functionality accross all
methods in the service to do things like database transaction management,
logging and measuring performance. This example also employs the threadlocal
request (soaplib.wsgi_soap.request) object to hold the data points for this
request. ::
    
    from soaplib.wsgi_soap import SimpleWSGISoapApp
    from soaplib.service import rpc
    from soaplib.serializers.primitive import String, Integer, Array
    
    from soaplib.wsgi_soap import request
    from time import time
    
    class HelloWorldService(SimpleWSGISoapApp):
        
        @rpc(String,Integer,_returns=Array(String))
        def say_hello(self,name,times):
            results = []
            for i in range(0,times):
                results.append('Hello, %s'%name)
            return results
        
        def on_call(self,environ):
            request.additional['call_start'] = time()
    
        def on_method_exec(self,environ,body,py_params,soap_params):
            request.additional['method_start'] = time()
    
        def on_results(self,environ,py_results,soap_results,http_headers):
            request.additional['method_end'] = time()
    
        def on_return(self,environ,returnString):
            call_start = request.additional['call_start']
            call_end = time()
            method_start = request.additional['method_start']
            method_end = request.additional['method_end']
            
            print 'Method took [%s] - total execution time[%s]'%(method_end-method_start,call_end-call_start)
            
    
    def make_client():
        from soaplib.client import make_service_client
        clent = make_service_client('http://localhost:7889/',HelloWorldService())
        return client
        
    if __name__=='__main__':
        from cherrypy._cpwsgiserver import CherryPyWSGIServer
        server = CherryPyWSGIServer(('localhost',7889),HelloWorldService())
        server.start()
    

Running this produces:

Method took [0.000195980072021] - total execution time[0.00652194023132]
Method took [0.000250101089478] - total execution time[0.00567507743835]
Method took [0.000144004821777] - total execution time[0.00521206855774]
Method took [0.000141859054565] - total execution time[0.00512409210205]
Method took [0.00377607345581] - total execution time[0.00511980056763]
Method took [0.00118803977966] - total execution time[0.00673604011536]
Method took [0.000146150588989] - total execution time[0.00157499313354]
Method took [0.0231170654297] - total execution time[0.0245010852814]
Method took [0.000166893005371] - total execution time[0.01802110672]


These may be helpful in finding bottlenecks in process, but this technique can
also be used to commit/rollback transactions or do setup/teardown operations for
all methods in a service.

