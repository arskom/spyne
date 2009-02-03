from soaplib.etimport import ElementTree

class NamespaceLookup(object):
    '''
    Class to manage XML namespaces
    '''

    def __init__(self, tns = None):
        self.nsmap = {
            'wsdl':'http://schemas.xmlsoap.org/wsdl/',
            'soap':'http://schemas.xmlsoap.org/wsdl/soap/',
            'xs': 'http://www.w3.org/2001/XMLSchema',
            'xsi': 'http://www.w3.org/1999/XMLSchema-instance',
            'plnk':'http://schemas.xmlsoap.org/ws/2003/05/partner-link/',
            'SOAP-ENC':'http://schemas.xmlsoap.org/soap/encoding/',
            'SOAP-ENV':'http://schemas.xmlsoap.org/soap/envelope/',
        }
        if tns is not None:
            self.nsmap['tns'] = tns
            self.nsmap['typens'] = tns
        
    def get_all(self):
        '''
        Return all namespaces
        '''
        return self.nsmap
        
    def get(self, key):
        '''
        Lookup and return a given namespace
        '''
        ns = self.nsmap[key] if key in self.nsmap else ''
        return "{%s}" % ns
        
    def set(self, key, ns):
        '''
        Add a namespace to the map (replaces)
        '''
        self.nsmap[key] = ns

'''
Default namespace lookup
'''        
ns = NamespaceLookup()


def qualify(name, ns):
    '''
    Qualify an idenifier with a namespace
    '''
    return "{%s}%s" % (ns, name)


def create_xml_element(name, nslookup, default_ns=None):
    '''
    Factory method to create a new XML element
    @param default_ns The default namespace to use for the element.
    @param extended_map A mapping of any additional namespaces to add.
    '''
    namespace_map = { None: default_ns } if default_ns is not None else {}
    for key, value in nslookup.get_all().iteritems():
        if value != default_ns:
            namespace_map[key] = value
    return ElementTree.Element(name, nsmap=namespace_map)
    
    
def create_xml_subelement(parent, name):
    '''
    Factory method to create a new XML subelement
    '''
    if not name.startswith("{") and None in parent.nsmap:
        name = qualify(name, parent.nsmap[None])
    return ElementTree.SubElement(parent, name)
    
