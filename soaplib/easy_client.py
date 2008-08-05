from soaplib.serializers.clazz import ClassSerializer
from soaplib.serializers.primitive import *
from soaplib.soap import *
from soaplib.util import split_url
from soaplib.etimport import ElementTree as et

import new, datetime, httplib

_builtin = {
    int : Integer,
    str : String,
    datetime.datetime : DateTime,
    float : Float,
    bool : Boolean,
}

class caller(object):
    def __init__(self,host,namespace,method):
        self.method = method
        self.host = host
        self.namespace = namespace
        
    def __call__(self,data,raw=False):
        e = data.to_xml(data,data.__class__.__name__)
        envelope = make_soap_envelope(e)
        body = et.tostring(envelope)
        methodName = '\"%s\"'%self.method
        httpHeaders = {"Content-Length":len(body),
                      "Content-type":'text/xml; charset="UTF-8"',
                      "Accept":"application/soap+xml, application/dime, multipart/related, text/*",
                      'User-Agent':'Soaplib/1.0',
                      'SOAPAction':methodName
                      }
        scheme,host,path = split_url(self.host)
        if scheme == "http":
            conn = httplib.HTTPConnection(host)
        elif scheme == "https":
            conn = httplib.HTTPSConnection(host)
        else:
            raise RuntimeError("Unsupported URI connection scheme: %s" % scheme)

        conn.request("POST",path,body=body,headers=httpHeaders)
        response = conn.getresponse()
        raw_data = response.read()
        
        retval = et.fromstring(raw_data)
        d = retval.find('{http://schemas.xmlsoap.org/soap/envelope/}Body').getchildren()[0]
        
        if raw:
            return d
        return objectify(d)

class DocumentClient(object):
   
    def __init__(self,host,methods,namespace=None):
        for method in methods:
            setattr(self,method,caller(host,namespace,method))
			
def get_serializer(value):
    _type = type(value)
    if value is None:
        return Null
    elif hasattr(value,'to_xml') and hasattr(value,'from_xml'):
        # this object can act as it's own serializer
        return value
    elif _builtin.has_key(_type):
        # found primitive: string, int, etc.
        return _builtin[_type]
    elif _type == list:
        # must assume that all the elements in the list are of the same type
        # and use the same serializer
        if not len(value):
            return Null
        else:
            return Array(get_serializer(value[0]))
    else:
        raise Exception("Could not find serializer for [%s]"%value)

def denamespace(tag):
    if tag.find('}') > -1:
        tag = tag.replace("{","")
        return tag.split('}')
    return None, tag
    
def objectify(element):
    class ElementWrapper(object):
        def __init__(self,element):
            self.__element = element
            self.__tags = {}
            for child in element.getchildren():
                ns,tag = denamespace(child.tag)
                if self.__tags.has_key(tag):
                    self.__tags[tag].append(child)
                else:
                    self.__tags[tag] = child
                    
                if hasattr(self,tag):
                    spot = getattr(self,tag)
                    if type(spot) != list:
                        spot = [spot]
                    #spot.append(objectify(child))
                    if len(child.getchildren()):
                        spot.append(new.classobj(tag,(ElementWrapper,),{})(child))
                    else:
                        spot.append(child.text)
                    setattr(self,tag,spot)
                    setattr(self,'__islist__',True)
                elif len(child.getchildren()):
                    setattr(self,tag,new.classobj(tag,(ElementWrapper,),{})(child))
                else:
                    setattr(self,denamespace(child.tag)[1],child.text) # marshall the type here!

        def __getitem__(self,index):
            if len(self.__tags.items()) == 1:
                # this *could* be an array
                k = self.__tags.keys()[0]
                return getattr(self,k)[index]
            if index == 0:
                return self
            raise StopIteration
            
    ns,tag = denamespace(element.tag)
    return new.classobj(tag,(ElementWrapper,),{})(element)
            
 
def make(__type_name,**kwargs):
    serializer = new.classobj(__type_name,(ClassSerializer,),{})
    namespace = None
	
    setattr(serializer,'soap_members',{})
    setattr(serializer,'namespace',namespace)
    for k,v in kwargs.items():
        serializer.soap_members[k] = get_serializer(v)
    o = serializer()
    for k,v in kwargs.items():
        setattr(o,k,v)
    return o
    
if __name__ == '__main__':
	echoInteger = make('echoInteger',i=34)
	print et.tostring(echoInteger.to_xml(echoInteger,'echoInteger'))
	
	c = DocumentClient('http://localhost:9753/',['echoInteger','echoSimpleClass','echoSimpleClassArray'])
	print c.echoInteger(make('echoInteger',i=3)).retval
	
	print c.echoSimpleClass(make('echoSimpleClass',sc=make('SimpleClass',i=34,s='bobo'))).retval.s
	
	d = c.echoSimpleClassArray(make('echoSimpleClassArray',
	                sca=[
                        make('SimpleClass',i=34,s='jasdf'),
                        make('SimpleClass',i=34,s='bobo'),
                        make('SimpleClass',i=34,s='poo'), 
	                    ]
	                ))
	print '*'*80
	for sc in d.retval:
	    print sc.s
	
