from soaplib.wsgi_soap import SimpleWSGISoapApp
from soaplib.service import soapmethod
from soaplib.serializers.primitive import String, Integer, Array

from wsgiref.simple_server import make_server

'''
This is a simple HelloWorld example to show the basics of writing
a webservice using soaplib, starting a server, and creating a service
client. 
'''

class HelloWorldService(SimpleWSGISoapApp):
    
    @soapmethod(String,Integer,_returns=Array(String))
    def say_hello(self,name,times):
    	'''
        Docstrings for service methods appear as documentation in the wsdl
        <b>what fun</b>
	@param name the name to say hello to
	@param the number of times to say hello
	@return the completed array
    	'''
        results = []
        for i in range(0,times):
            results.append('Hello, %s'%name)
        return results

def make_client():
    from soaplib.client import make_service_client
    client = make_service_client('http://localhost:7889/',HelloWorldService())
    return client
    
if __name__=='__main__':
    server = make_server('localhost', 7889, HelloWorldService())
    server.serve_forever()
