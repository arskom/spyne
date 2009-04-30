from soaplib.wsgi_soap import SimpleWSGISoapApp
from soaplib.service import soapmethod
from soaplib.serializers.primitive import String, Integer, Array

'''
This example shows how to override the variable names for fun and profit.
This is very useful for situations that require the use of variable names
that are python keywords like, from, to, import, return, etc.
'''

class EmailManager(SimpleWSGISoapApp):
    
    @soapmethod(String,String,String,
                _inVariableNames={'_to':'to','_from':'from','_message':'message'},
                _outVariableName='return')    
    def sendEmail(self,_to,_from,message):
        # do email sending here
        return 'sent!'

if __name__=='__main__':
    try:
        from wsgiref.simple_server import make_server
        server = make_server('localhost', 7789, EmailManager())
        server.serve_forever()
    except ImportError:
        print "Error: example server code requires Python >= 2.5"
