import cElementTree as ElementTree
from soaplib.serializers.primitive import Fault

class Message(object):
    
    def __init__(self,name,params,ns=None,typ=None):
        self.name = name
        self.params = params
        if typ == None:
            typ = name
        self.typ = typ
        self.ns = ns
        
    def to_xml(self,*data):
        if len(self.params):
            if len(data) != len(self.params):
                raise Exception("Parameter number mismatch expected [%s] got [%s]"%(len(self.params),len(data)))

        element = ElementTree.Element(self.name)
        if self.name.find('}') == -1 and self.ns:
            element.set('xmlns',self.ns)

        for i in range(0,len(self.params)):
            name,serializer = self.params[i]
            d = data[i]
            e = serializer.to_xml(d,name)
            element.append(e)
            
        return element
        
    def from_xml(self,element):
        results = []        
        children = element.getchildren()
        
        def find(name):
            # inner method for finding child node
            for c in children:
                if c.tag.split('}')[-1] == name:
                    return c
                
        for name, serializer in self.params:
            child = find(name)
            if child != None:
                results.append(serializer.from_xml(child))
            else:
                results.append(None)
        return results
        
    def add_to_schema(self,schemaDict):
        complexType = ElementTree.Element('xs:complexType')
        complexType.set('name',self.typ)
        
        sequence = ElementTree.SubElement(complexType,'xs:sequence')
        if self.params:
            for name,serializer in self.params:
                e = ElementTree.SubElement(sequence,'xs:element')
                e.set('name',name)
                e.set('type',serializer.get_datatype(True))
                
        element = ElementTree.Element('xs:element')
        element.set('name',self.typ)
        element.set('type','%s:%s'%('tns',self.typ))
        
        schemaDict[self.typ] = complexType
        schemaDict[self.typ+'Element'] = element
        
class MethodDescriptor:
    '''
    This class represents the method signature of a soap method, and is returned
    by the soapdocument, or soapmethod decorators.  
    '''

    def __init__(self, name, inMessage, outMessage, isCallback=False, isAsync=False):
        self.inMessage = inMessage
        self.outMessage = outMessage
        self.name = name
        self.isCallback = isCallback
        self.isAsync = isAsync

def from_soap(xml_string):
    '''
    Parses the xml string into the header and payload
    '''
    root = ElementTree.fromstring(xml_string)    
    body = None
    header = None

    # find the body and header elements
    for e in root.getchildren():
        name = e.tag.split('}')[-1].lower()
        if name == 'body':
            body = e
        elif name == 'header':
            header = e
    payload = None
    if len(body.getchildren()):
        payload = body.getchildren()[0]

    return payload, header

def make_soap_envelope(message, tns=None, header_elements=None):
    '''
    This method takes the results from a soap method call, and wraps them
    in the appropriate soap envelope with any specified headers

    @param the message of the soap envelope, either an element or list of elements
    @param any header elements to be included in the soap response
    @returns the envelope element
    '''
    
    envelope = ElementTree.Element('SOAP-ENV:Envelope')
    if tns:
        envelope.set('xmlns:tns',tns)
        envelope.set('xmlns',tns)

    envelope.set('xmlns:SOAP-ENV','http://schemas.xmlsoap.org/soap/envelope/')
    envelope.set('xmlns:xsi','http://www.w3.org/1999/XMLSchema-instance')
    envelope.set('xmlns:xs','http://www.w3.org/2001/XMLSchema')
    
    if header_elements:
        headerElement = ElementTree.SubElement(envelope,'SOAP-ENV:Header')
        
        for h in header_elements:
            headerElement.append(h)
   
    body = ElementTree.SubElement(envelope,'SOAP-ENV:Body')

    if type(message) == list:
        for m in message:
            body.append(m)
    elif message != None:
        body.append(message)

    return envelope

def make_soap_fault(faultString, faultCode='Server', detail=None):
    '''
    This method populates a soap fault message with the provided fault string and 
    details.  
    @param faultString the short description of the error
    @param detail the details of the exception, such as a stack trace
    @param faultCode defaults to 'Server', but can be overridden
    @returns the element corresponding to the fault message
    '''
    envelope = ElementTree.Element('SOAP-ENV:Envelope')
    envelope.set('xmlns:SOAP-ENV','http://schemas.xmlsoap.org/soap/envelope/')

    body = ElementTree.SubElement(envelope,'SOAP-ENV:Body')
    
    f = Fault(faultCode,faultString,detail)
    body.append(Fault.to_xml(f))

    return envelope
