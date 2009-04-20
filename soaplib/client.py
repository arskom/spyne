from soaplib.etimport import ElementTree

import httplib
from soaplib.soap import from_soap, make_soap_envelope, collapse_swa, apply_mtom
from soaplib.util import split_url, create_relates_to_header
from soaplib.serializers.primitive import Fault
from cStringIO import StringIO

import sys

# This sets the HTTP version string sent to the server to 1.0
# preventing the response from bein 'chunked'.  This is done
# because of a know bug in python (#900744).  Rather than apply 
# the patch to all the installed systems, it is simpler to set this
# version string, to be later removed in python 2.5
#
httplib.HTTPConnection._http_vsn_str = 'HTTP/1.0'

_debug = False
_out = sys.stdout

def debug(is_on,out=sys.stdout):
    '''
    This is a utility method for debugging client request and responses
    @param boolean for turning debug on or off
    @param filelike object to write to
    '''
    global _out, _debug
    _out = out
    _debug = is_on

def dump(host,path,headers,envelope):
    '''
    Debugging method for dumping request information to a file or stdout
    @param host server host
    @param path server path
    @param headers http headers
    @param envelope soap envelope
    '''
    global _out, _debug
    if not _debug: return

    def writeln(text):
        _out.write(text)
        _out.write('\r\n')
        _out.flush()
        
    writeln('-------------------------------------------------')
    writeln('Host: '+host)
    writeln('Path: '+path)
    writeln('Headers:')
    for k,v in headers.items():
        writeln('    %s -> %s'%(k.ljust(20),v))
    writeln('Envelope:')
    writeln(envelope)
    writeln('-------------------------------------------------')
    
_err_format =     '''
Parameter Do Not Match: 
+ Arguments Passed In: 
%s 
+ Parameters Required: 
%s'''

class SimpleSoapClient(object):
    '''
    SimpleSoapClient is the lowest level http soap client in soaplib,
    and represents a single remote soap method.  This class can be 
    used by itself by passing it the url information and MethodDescriptor, 
    but is most frequently used by the ServiceClient object.
    '''

    def __init__(self,host,path,descriptor,scheme="http"):
        '''
        @param remote host
        @param remote path
        @param MethodDescriptor of the remote method being called
        @param remote scheme
        '''
        self.host = host
        self.path = path
        self.descriptor = descriptor
        self.scheme = scheme

    def __call__(self,*args,**kwargs):
        '''
        This method executes the http request to the remote web service.  With
        the exception of 'headers', 'msgid', and 'mtom'; all keyword arguments 
        to this method are put in the http header.  The 'headers' keyword is to
        denote a list of elements to be included in the soap header, 'msgid'
        is a convenience keyword used in async web services which creates a
        WS-Addressing messageid header to be included in the soap headers, and
        'mtom' enables the Message Transmission Optimization Mechanism.

        @param the arguments to the remote method
        @param the keyword arguments 
        '''
        if len(args) != len(self.descriptor.inMessage.params):
            argstring = '\r\n'.join(['    '+str(arg) for arg in args])
            paramstring = '\r\n'.join(['    '+str(p[0]) for p in self.descriptor.inMessage.params])
            err_msg = _err_format%(argstring,paramstring)
            raise Exception(err_msg)
        
        msg = self.descriptor.inMessage.to_xml(*args)

        # grab the soap headers passed into this call
        headers = kwargs.get('headers',[])
        mtom = kwargs.get('mtom',False)
        msgid = kwargs.get('msgid')
        if msgid:
            # special case for the msgid field as a convenience 
            # when dealing with async callback methods
            headers.append(create_relates_to_header(msgid))

        tns = self.descriptor.inMessage.ns
        envelope = make_soap_envelope(msg, tns, header_elements=headers)

        body = ElementTree.tostring(envelope)
        methodName = '\"%s\"'%self.descriptor.soapAction
        httpHeaders = {"Content-Length":len(body),
                      "Content-type":'text/xml; charset="UTF-8"',
                      "Accept":"application/soap+xml, application/dime, multipart/related, text/*",
                      'User-Agent':'Soaplib/1.0',
                      'SOAPAction':methodName
                      }
                      
        for k,v in kwargs.items():
            # add all the other keywords to the http headers
            if k not in ('headers','msgid','mtom'):
                httpHeaders[k]=v

        if mtom:
            httpHeaders, body = apply_mtom( httpHeaders, body,
                                            self.descriptor.inMessage.params,
                                            args )
 
        dump(self.host,self.path,httpHeaders,body)               

        if self.scheme == "http": 
            conn = httplib.HTTPConnection(self.host)
        elif self.scheme == "https":
            conn = httplib.HTTPSConnection(self.host)
        else:
            raise RuntimeError("Unsupported URI connection scheme: %s" % scheme)
            
        conn.request("POST",self.path,body=body,headers=httpHeaders)
        response = conn.getresponse()
        data = response.read() 
        
        dump(self.host,self.path,dict(response.getheaders()),data)
        
        contenttype = response.getheader('Content-Type')
        data = collapse_swa(contenttype, data)
        
        conn.close()
        if str(response.status) not in['200','202']:
            # consider everything NOT 200 or 202 as an error response
            
            if str(response.status) == '500': 
                fault = None
                try:
                    payload, headers = from_soap(data)
                    fault = Fault.from_xml(payload)
                except:
                    trace = StringIO()
                    import traceback
                    traceback.print_exc(file=trace)
                    
                    fault = Exception('Unable to read response \n  %s %s \n %s \n %s'%(response.status,response.reason,trace.getvalue(),data))
                raise fault
            else:
                raise Exception('%s %s'%(response.status,response.reason))

        if not self.descriptor.outMessage.params:
            return 

        payload, headers = from_soap(data)
        results = self.descriptor.outMessage.from_xml(payload)
        return results[0] 

class ServiceClient(object):
    '''
    This class is a simple, convenient class for calling remote web services.
    @param host the host of the SOAP service being called
    @param path the path to the web service
    @param impl the SimpleWSGISoapApp which defines the remote service
    @param mtom whether or not to send attachments using MTOM
    '''

    def __init__(self,host,path,server_impl, scheme="http"):
        if host.startswith("http://"):
            host = host[6:]
            
        self.server = server_impl
        for method in self.server.methods():
            setattr(self,method.name,SimpleSoapClient(host,path,method,scheme))

def make_service_client(url,impl):
    scheme,host,path = split_url(url)
    return ServiceClient(host,path,impl, scheme)
