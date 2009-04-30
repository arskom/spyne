#!/usr/bin/env python

from soaplib.wsgi_soap import SimpleWSGISoapApp
from soaplib.service import soapmethod
from soaplib.serializers.primitive import String, Integer, Array
from soaplib.serializers.binary import Attachment

class HelloWorldService(SimpleWSGISoapApp):

    @soapmethod(Attachment,Integer,_returns=Array(String), _mtom=True)
    def say_hello(self,name,times):
        results = []
        for i in range(0,times):
            results.append('Hello, %s'%name.data)
        return results
        
if __name__=='__main__':
    try:
        from wsgiref.simple_server import make_server
        server = make_server('localhost', 7789, HelloWorldService())
        server.serve_forever()
    except ImportError:
        print "Error: example server code requires Python >= 2.5"
