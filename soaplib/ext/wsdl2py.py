import cElementTree as et
import urllib2
import new
from soaplib.soap import Message, MethodDescriptor
from soaplib.serializers import primitive
from soaplib.serializers.clazz import ClassSerializer
from soaplib.client import *

from warnings import warn
warn('This module is under active development and should not be used in a production scenario')


_primitives = {
    'xs:string':primitive.String,
    'xs:int':primitive.Integer,
    'xs:dateTime':primitive.DateTime,
    'xs:float':primitive.Float,
    'xs:boolean':primitive.Boolean,
    'string':primitive.String,
    'int':primitive.Integer,
    'dateTime':primitive.DateTime,
    'float':primitive.Float,
    'boolean':primitive.Boolean
}

_types = {}
_messages = {}
_methods = {}
_clients = {}
_service_name = ''
_location = ''

wsdl = 'http://schemas.xmlsoap.org/wsdl/'
xs = 'http://www.w3.org/2001/XMLSchema'

_serializers = {}
ns = 'test'

_type_elements = {}
    
def is_array(name):
    # need better checking for arrays
    #print _type_elements
    print _types
    if len(_type_elements[name]) == 1 and _type_elements[name][0].get('maxOccurs') == 'unbounded':
        return True
    return False

def get_serializer(name):
    print name
    print _types
    if _primitives.has_key(name):
        return _primitives[name]
        
    if not _serializers.has_key(name):
        name = name.split(':')[-1]
        
        if is_array(name):
            s = _types[name]
            inner_serializer = get_serializer( s.keys()[0] )
            class_serializer = primitive.Array(inner_serializer)
        else:
            s = _types[name]
            print s
            class_serializer = new.classobj(name,(ClassSerializer,),{})
            setattr(class_serializer,'soap_members',{})
            setattr(class_serializer,'namespace',None)
            for k,v in s.items():
                class_serializer.soap_members[k] = get_serializer(v)
        _serializers[name] = class_serializer
        
    return _serializers[name]

def qn(prefix,typ):
    return '{%s}%s'%(globals()[prefix],typ)

def handle_wsdl(wsdl):
    handle_types(wsdl.find(qn('wsdl','types')))
    handle_messages(wsdl.findall(qn('wsdl','message')))
    handle_portType(wsdl.find(qn('wsdl','portType')))
    handle_service(wsdl.find(qn('wsdl','service')))
    print _types
    
def handle_service(service):
    _service_name = service.get('name')
    location = service.getchildren()[0].getchildren()[0].get('location')
    _location = location
    
def handle_types(types):
    schema = types[0]
    elements = schema.findall(qn('xs','element'))
    for element in elements:
        for c in schema.findall(qn('xs','complexType')):
            if c.get('name') == element.get('name'):
                handle_element(element,c)
    for k in _types.keys():
        print get_serializer(k)
                        
def handle_element(element,complexType):
    parts = {}
    se = complexType.find(qn('xs','sequence')).findall(qn('xs','element'))
    name = element.get('name')
    _type_elements[name] = se
    print se
    for e in se:
        print 'adding',e.get('name')
        parts[e.get('name')] = e.get('type')
        #array = ''
        #if e.get('maxOccurs') == 'unbounded': # check for arrays?
        #    array = 'array'
        #print '     ',e.get('name'),e.get('type'), array
    print parts
    _types[name] = parts
    #_serializers = {}

def get_params(msg):
    print msg
    params = _types[msg]
    msg_params = []
    for k,v in params.items():
        if v.startswith('xs'):
            msg_params.append((k,_primitives[v]))
        else:
            print 'k,v',k,v
            v = v.split(':')[-1]
            msg_params.append((k,_serializers[v]))
            #print k,v
            #msg_params.append()
    return msg_params
    
def handle_messages(messages):
    print messages
    print "^"*80
    for m in messages:
        name = m.get('name')
        p = m.find(qn('wsdl','part'))
        _messages[name] = (p.get('element'),p.get('name'))
        params = get_params(name)
        print 'params',params
        
        msg_obj = Message(name,name,params)
        _messages[name] = msg_obj
        
def handle_portType(pt):
    operations = pt.findall(qn('wsdl','operation'))
    for operation in operations:
        name = operation.get('name')
        input = operation.find(qn('wsdl','input'))
        in_msg = input.get('message')
        in_name = input.get('name')
        
        output = operation.find(qn('wsdl','output'))
        if output != None:
            out_msg = output.get('message')
            out_name = output.get('name')
        else:
            out_msg = ''
            out_name = ''
               
        print '*'*80
        print _messages[in_msg.split(':')[-1]]
        print '  name  ',name
        print '  input ',in_msg,in_name
        print ' output ',out_msg,out_name
        
        method = MethodDescriptor(name,_messages[in_name],_messages[out_name])
        _methods[name] = method
    
def make_clients():
    print _service_name
    for name, method in _methods.items():
        _clients[name] = SimpleSoapClient('127.0.0.1:9753','/',method)
    service = new.classobj(_service_name,(object,),{})
    for operation, client in _clients.items():
        setattr(service,operation,client)
    return service
    
def run(url):
    content = urllib2.urlopen(url).read()
    wsdl = et.fromstring(content)
    handle_wsdl(wsdl)
    return make_clients()

if __name__ == "__main__":
    service = run('http://127.0.0.1:9753/service.wsdl')
    #print _serializers
    #a = _serializers['echoSimpleClass']
    #print a
    #print dir(a)
    #print dir(a.soap_members)
    
    #print '*'*80
    #r = a()
    #r.sc = _serializers['SimpleClass']()
    #r.sc.i = 15
    #r.sc.s = 'af'
    #print _type_elements
    nc = _serializers['NestedClass']()
    nc.s = 'blah'
    #print dir(nc)
    simple = _serializers['SimpleClass']()
    simple.i = 13
    simple.s = 'ab'
    nc.simple = [simple]
    print service.echoNestedClass(nc).s
    print service.echoSimpleClass(simple).i
