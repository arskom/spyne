from soaplib.wsgi_soap import SimpleWSGISoapApp
from soaplib.service import soapmethod
from soaplib.serializers.primitive import String, Integer, Array
from soaplib.serializers.binary import Attachment
from soaplib.util import get_callback_info

from threading import Thread
from tempfile import mkstemp
import time

'''
This is a very simple async service that sleeps for a specified 
number of seconds and then call back the caller with a message.
This kicks off a new Thread for each request, which is not recommended
for a real-world application.  Soaplib does not provide any thread
management or scheduling mechanism, the service is responsible for the
execution of the async. process.
'''

class SleepingService(SimpleWSGISoapApp):
    
    @soapmethod(Integer,_isAsync=True)
    def sleep(self,seconds):
        msgid, replyto = get_callback_info()
        
        def run():
            time.sleep(seconds)
            
            client = create_service_client(replyto, self)
            client.woke_up('good morning',msgid=msgid)

        Thread(target=run).start()

    @soapmethod(String,_isCallback=True)
    def woke_up(self,message):
        pass
        
if __name__=='__main__':
    try:
        from wsgiref.simple_server import make_server
        server = make_server('localhost', 7789, SleepingService())
        server.serve_forever()
    except ImportError:
        print "Error: example server code requires Python >= 2.5"