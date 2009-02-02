from soaplib.etimport import ElementTree

'''
Global XML namespace dictionary
'''
ns={
    'wsdl':'http://schemas.xmlsoap.org/wsdl/',
    'soap':'http://schemas.xmlsoap.org/wsdl/soap/',
    'xs': 'http://www.w3.org/2001/XMLSchema',
    'xsi': 'http://www.w3.org/1999/XMLSchema-instance',
    'plnk':'http://schemas.xmlsoap.org/ws/2003/05/partner-link/',
    'SOAP-ENC':'http://schemas.xmlsoap.org/soap/encoding/',
    'SOAP-ENV':'http://schemas.xmlsoap.org/soap/envelope/',
}

def qualify(string, namespace):
    '''
    Apply an XML namespace qaulifier to an input string
    '''
    if namespace == None:
        return string
    return "{%s}%s" % (namespace, string)


def create_xml_element(name, default_ns=None, extended_map={}):
    '''
    Factory method to create a new XML element
    @param default_ns The default namespace to use for the element.
    @param extended_map A mapping of any additional namespaces to add.
    '''
    namespace_map = { None: default_ns } if default_ns is not None else {}
    namespace_map.update(ns)
    namespace_map.update(extended_map)
    return ElementTree.Element(name, nsmap=namespace_map)
    
    
def create_xml_subelement(parent, name):
    '''
    Factory method to create a new XML subelement
    '''
    return ElementTree.SubElement(parent, name)
    