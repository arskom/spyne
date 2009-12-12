#
# soaplib - Copyright (C) 2009 Aaron Bickell, Jamie Kirkpatrick
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301
#

import new
import traceback
import os.path as path
from string import Template
import urllib2 as ulib

from soaplib.etimport import ElementTree
from soaplib.serializers.clazz import ClassSerializer
from soaplib.parsers.typeparse import TypeParser, schqname
from soaplib.wsgi_soap import SimpleWSGISoapApp
from soaplib.service import soapmethod, getTNS
import soaplib.soap as soap

wsdlns = 'http://schemas.xmlsoap.org/wsdl/'
wsdlqname = "{%s}" % wsdlns
soapns = 'http://schemas.xmlsoap.org/wsdl/soap/'
soapqname = "{%s}" % soapns

headerstr = '''
from soaplib.serializers.clazz import ClassSerializer
from soaplib.serializers.primitive import String, DateTime, Integer, Boolean, Float, Array, Any
from soaplib.serializers.binary import Attachment
from soaplib.wsgi_soap import SimpleWSGISoapApp
from soaplib.service import soapmethod

from $xsdmodule import *

'''

""" Extraction storage types below, these are used as intermediaries
    to get the data out of the wsdl.
"""
class Message(object):
    def __init__(self, name, ctype=None, element=None):
        self.name = name
        self.ctype = ctype
        self.element = element
    @property
    def typ(self):
        if self.element is None:
            return self.ctype
        else:
            return self.element

class Port(object):
    def __init__(self, name):
        self.name = name
        self.operations = {}

class Operation(object):
    def __init__(self, name, input, output, faults=[], documentation=''):
        self.name = name
        self.input = input
        self.output = output
        self.faults = faults
        self.documentation = documentation

class Binding(object):
    def __init__(self, name, style, transport, type):
        self.name = name
        self.style = style
        self.transport = transport
        self.type = type
        self.operations = {}

class BindingOperation(object):
    def __init__(self, name, soapaction, input, output, faults):
        self.name = name    
        self.soapaction = soapaction
        self.input = input
        self.output = output
        self.faults = faults

class WSDLParser(object):
    """
        The main wsdl parser object.  Produces SimpleWSGISoapApps for the 
        process WSDL.
    """
    def __init__(self, document, url, spacer='    ', warn=True):
        """
            init method, takes an elementtree element corresponding the root
            of the wsdl document and the url of wsdl document (used to retrieve
            relative documents imported by the wsdl).
            warn=False deactivates the unsupported features warning.
        """
        #global catalogue stores all types
        self.url = url
        self.tps = list()
        self.ctypes = {}
        self.elements = {}
        self.messagecat = {}
        self.portcat = {}
        self.bindingcat = {}   
        #catalogue of services
        self.services = {}     
        self.unsupported = set()
        self.document = document
        self.nsmap = document.nsmap
        self.baseurl = path.dirname(url)
        self.tns = self.gettns(document)
        self.spacer = spacer
        self.importwsdl(document)
        self.importtypes(document)
        self.retrievemessages(document)
        self.processports(document)
        self.processbindings(document)
        self.buildservices()
        if warn is True and len(self.unsupported) > 0:
            print "The following wsdl features not currently supported by soaplib were encountered \
during the parse: \n%s" % "\n".join(self.unsupported) 
            print "---------------------------------------------------------------------------"
    
    def gettns(self, document):
        """ return the target namespace of the document"""
        return document.get('targetNamespace')

    def importwsdl(self, document):
        """ 
            Processes any wsdl documents imported by document 
            (messages are sometimes held in a seperate document, for example).
            Recusively calls WsdlParser to descend through imports
        """
        reimport = 0
        for imp in document.findall('%simport' % wsdlqname):
            url = str(imp.get('location'))
            #work out if relative or absolute url
            if '://' not in url:
                #relative
                url = path.join(path.dirname(self.url), url)
            f = ulib.urlopen(url)
            d = f.read()
            f.close()
            root = ElementTree.fromstring(d)
            wp = WSDLParser(root, url)
            for cats in ['ctypes', 'elements', 'messagecat', 'portcat', 'bindingcat']:
                getattr(self, cats).update(getattr(wp, cats))
            document.remove(imp)
            for tp in wp.tps:
                self._add_tp(tp)
    
    def importtypes(self, document):
        """ 
            Processes any imported xmlschema in a wsdl:types element
            within document, returns a soaplib.parsers.typeparse.TypeParser
            containing the parsed schema. 
            
        """
        location = None
        for t in document.findall(wsdlqname+"types"):
            url = None            
            for s in t.findall(schqname+"schema"):
                for i in s.findall(schqname+"import"):
                    url = i.get('schemaLocation')
            if url is not None:
                #work out if relative or absolute url
                if '://' not in url:
                    #relative
                    url = path.join(path.dirname(self.url), url)
                f = ulib.urlopen(url)
                d = f.read()
                f.close()
                element = ElementTree.fromstring(d)
            else:
                #inline schema
                for element in t.findall(schqname+"schema"):
                    self._add_tp(TypeParser(element, global_ctypes=self.ctypes, global_elements=self.elements))
                return
            self._add_tp(TypeParser(element, global_ctypes=self.ctypes, global_elements=self.elements))
        return

    def _add_tp(self, typeparser):
        self.ctypes.update(typeparser.ctypes)
        self.elements.update(typeparser.elements)
        self.nsmap.update(typeparser.nsmap)
        self.tps.append(typeparser)
    
    def retrievemessages(self, document):
        """ 
            Process all message elements with document and place
            them in self.messagecat
        """            
        for message in document.findall(wsdlqname+'message'):
            name = message.get('name')
            ctype = None
            element = None            
            for part in message.findall(wsdlqname+'part'):
                element = self.striptype(part.get('element'))
                ctype = self.striptype(part.get('type'))
            self.messagecat[self.striptype(name)] = Message(name, ctype=ctype, element=element)

    def processports(self, document):
        """
            Process all port elements within document and place
            them in self.portcat
        """
        for port in document.findall(wsdlqname+'portType'):
            #stash the port
            name = port.get('name')
            portob = Port(name)
            self.portcat[self.striptype(name)] = portob
            for op in port.findall(wsdlqname+'operation'):
                opname = op.get('name')
                input = op.find(wsdlqname+'input')
                output = op.find(wsdlqname+'output')
                documentation = getattr(op.find(wsdlqname+'documentation'), 'text', None)
                faults = []
                for fault in op.findall(wsdlqname+'fault'):
                    faults.append(fault)
                opob = Operation(opname, input, output, faults, documentation)
                portob.operations[opname] = opob
    
    def processbindings(self, document):
        """
            Process all binding elements within document and place
            them in self.bindingcat
        """
        for binding in document.findall(wsdlqname+'binding'):
            name = binding.get('name')
            type = self.striptype(binding.get('type'))
            soapbinding = binding.find(soapqname+'binding')
            bindingob = Binding(name, soapbinding.get('style'), soapbinding.get('transport'), type)
            self.bindingcat[name] = bindingob
            for operation in binding.findall(wsdlqname+'operation'):
                #get soap action
                opname = operation.get('name')
                soapoperation = operation.find(soapqname+'operation')
                soapaction = soapoperation.get('soapAction')
                #read rest
                input = operation.find(wsdlqname+'input')
                output = operation.find(wsdlqname+'output')
                faults = []
                for fault in operation.findall(wsdlqname+'fault'):
                    faults.append(fault)
                #stash back
                opob = BindingOperation(opname, soapaction, input, output, faults)
                bindingob.operations[opname] = opob        
    
    def striptype(self, typestr):
        """ 
            Process a namespace:typename type and return the correct qname.
        """
        try:            
            spl = typestr.split(':')        
            ns = self.nsmap[spl[0]]
            return "{%s}%s" % (ns, spl[1])
        except:
            return "{%s}%s" % (self.tns, typestr)

    def buildservices(self):
        """
            build services from the bindings parsed in bindingcat
            and put the nearly built services in self.services
        """
        for binding in self.bindingcat.values():
            service = new.classobj(binding.name, (SimpleWSGISoapApp, object), {})
            self.services[binding.name] = service
            port = self.portcat[binding.type]
            for operation in port.operations.values():
                self.buildsoapmethod(service, operation)
                
    def buildsoapmethod(self, service, operation):
        """
            build a new soapmethod from the parsed operation and
            attach it to the service object.
        """
        inmessagexml = operation.input
        inmessage = self.messagecat.get(self.striptype(inmessagexml.get('message')), None)
        inparams = []
        intype = None    
        #messages are either based on types or elements    
        if inmessage.element is not None:
            intype = self.elements[inmessage.element].type
        elif inmessage.ctype is not None:
            intype = self.ctypes[inmessage.ctype]
        if intype is not None:
            #messages can be empty
            inparams = [(k,v) for (k,v) in intype.types.__dict__.items() 
                    if not k.startswith('_')]
        outmessagexml = operation.output
        outmessage = self.messagecat.get(self.striptype(outmessagexml.get('message')), None)
        outparams = []
        #messages are either based on types or elements        
        if outmessage.element is not None:
            outtype = self.elements[outmessage.element].type
        else:
            outtype = self.ctypes.get(outmessage.ctype, None)
        if outtype is not None:
            (returnname, returntypename, returntype) = self.unrollreturn(outtype)
            outparams = [(returnname, returntype)]
        ns = getTNS(service)
        insoapmessage = soap.Message(inmessage.name, inparams, ns=ns, typ=inmessage.typ)
        outsoapmessage = soap.Message(outmessage.name, outparams, ns=ns, 
            typ=outmessage.typ)
        def newmethod(*args, **kwargs):
            if kwargs.has_key('_soap_descriptor'):
                return soap.MethodDescriptor(operation.name, operation.name, insoapmessage,
                        outsoapmessage, '', False, False, False)
        newmethod.func_name = operation.name
        newmethod._is_soap_method = True
        newmethod.__doc__ = operation.documentation
        setattr(service, operation.name, newmethod)
    
    def unrollreturn(self, outtype):
        """
            Unroll the response type and extract the return
            value returning a triple of return valuename,
            return type name, and the return type itself
        """
        if len([v for (k,v) in outtype.types.__dict__.items() if not k.startswith('_')]) > 1:
            self.unsupported.add('Multiple return values')
        for (k,v) in outtype.types.__dict__.items():
            if not k.startswith('_'):
                return (k, v.print_class(), v)
        #if we get here we have no types
        raise Exception('No types found in %s' % k)

    def tofile(self, filename, config):
        """
            write the parsed wsdl out to filename.
            config is the options dictionary created by opt
            parse in run.
        """
        xsdmodule = config.schoutput.split('.')[0]
        template = Template(headerstr)
        tempdict = dict(xsdmodule = xsdmodule)
        #write out bindings        
        f = open(filename, 'w')
        f.write(template.substitute(tempdict))
        for (k,v) in self.services.items():
            #instantiate a service so we can extract method descriptors from it
            self.writeservice(v, f)
        f.close()
            
    def typetostring(self, t):
        """ 
            return the name of type t, needed as arrays need 
            special treatment.
        """
        return t.print_class()

    def writeservice(self, servcls, f):
        """
            write out the given service (servcls) out to the given file(f).
        """
        #instantiate servcls so we can extract its MethodDescriptors
        service = servcls()
        f.write("class %s(SimpleWSGISoapApp):\n" % servcls.__name__)
        for method in service._soap_methods:
            inmsgparams = method.inMessage.params
            paramlist = [self.typetostring(v) for (k,v) in inmsgparams]
            outmsgparams = method.outMessage.params
            if len(outmsgparams) > 0:
                returntype = outmsgparams[0]
                paramlist += ['_returns=%s' % self.typetostring(returntype[1])]
                if returntype[0] != '%sResult' % method.name:
                    paramlist += ['_outVariableName="%s"' % returntype[0]]
            if method.inMessage.name != method.name:
                paramlist += ['_inMessage=%s' % method.inMessage.name]
            if method.outMessage.name != '%sResponse'%method.name:
                paramlist += ['_outMessage=%s' % method.outMessage.name]
            f.write("%s@soapmethod(%s)\n" % (
                self.spacer, ', '.join(paramlist)
            ))
            arglist = ['self']
            arglist += [ k for (k,v) in inmsgparams ]
            f.write("%sdef %s(%s):\n" % (
                self.spacer, method.name,
                ", ".join(arglist)
            ))
            doc = getattr(getattr(service, method.name, None), '__doc__', None)
            if doc is not None:
                f.write('%s%s"""%s"""\n' % (self.spacer, self.spacer, doc))
            f.write("%s%spass\n\n" % (
                self.spacer, self.spacer
            ))
            
    @classmethod
    def from_url(cls, url):
        """ return a new WSDLParser with WSDL parsed from the given url """
        f = ulib.urlopen(url)
        d = f.read()
        f.close()
        return cls.from_string(d, url)

    @classmethod
    def from_string(cls, xml, url):
        """ 
            return a new WSDLParser with WSDL parsed from the supplied xml,
            the url is required incase of additional wsdl or schema files
            need to be fetched.
        """
        element = ElementTree.fromstring(xml)
        return WSDLParser(element, url)   
    
def run():
    """ 
        Script for wsdl2py, need to setup the script in setup.py
        Run 'wsdl2py -h' for command line options.
    """
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-f", "--file", dest="filename",
                  help="read wsdl from FILE", metavar="FILE")
    parser.add_option("-u", "--url", dest="url",
        help="read wsdl from URL", metavar="URL")
    parser.add_option("-o", "--output", dest="output",
        help="output filename.", metavar="OUTPUT", default='wsdlservice.py')
    parser.add_option("-s", "--schemaoutput", dest="schoutput",
        help="output filename for processed schema", metavar="SCHFILE", 
        default="xsdtypes.py")
    parser.add_option("-r", "--returnval", dest="ret",
        help="Specify the SOAP return value, (defaults to return).", 
        metavar="RETURN", default='return')
    parser.add_option("-m", "--mapping", dest="mapping",
        help="Specify any xsd to soaplib type mappings(space seperated).", 
        metavar="MAPPING", default=None)   
    (options, args) = parser.parse_args()
    if options.filename is None:
        url = options.url
    else:
        url = 'file://%s' % path.abspath(options.filename)
    if url is None:
        return parser.error("You must provide either a url or filename.")
    if options.mapping is not None:
        mappings = options.mapping.split(' ')
        for mapping in mappings:
            (name, value) = mapping.split('=')
            builtins[name] = serializers[value]
    wp = WSDLParser.from_url(url)
    #write out xsd
    f = open(path.abspath(options.schoutput), 'w')
    wp.tps[0].write_imports(f)
    for tp in wp.tps:
        tp.write_body(f)
    f.close()
    #write out wsdl
    wp.tofile(path.abspath(options.output), config=options)

