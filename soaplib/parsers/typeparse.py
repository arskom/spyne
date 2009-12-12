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
import inspect
import urllib2 as ulib
import os.path as path

from soaplib.etimport import ElementTree
from soaplib.serializers.clazz import ClassSerializer, ClassSerializerMeta
from soaplib.serializers.primitive import String, DateTime, Integer, Boolean, Float, Array, Any, Repeating, Optional
from soaplib.serializers.binary import Attachment

schnamespace = 'http://www.w3.org/2001/XMLSchema'
schqname = '{%s}' % schnamespace

sequence = '%ssequence' % schqname
choice = '%schoice' % schqname
all = '%sall' % schqname
ctype = '%scomplexType' % schqname
ccontent = '%scomplexContent' % schqname
crestrict = '%srestriction' % schqname
stype = '%ssimpleType' % schqname
scelement = '%selement' % schqname
scattr = '%sattribute' % schqname
scany = '%sany' % schqname

builtinobj = [String, DateTime, Integer, Boolean, Float, Array, Any, Attachment]

serializers = {
    'String': String,
    'DateTime': DateTime,
    'Integer': Integer,
    'Boolean': Boolean,
    'Float': Float,
    'Array': Array,
    'Any': Any,
    'Attachment': Attachment,
}

builtins = {
    '%sstring' % schqname: String,
    '%sint' % schqname: Integer,
    '%sdateTime' % schqname: DateTime,    
    '%sfloat' % schqname: Float,
    '%sboolean' % schqname: Boolean,
    '%sbase64Binary' % schqname: Attachment,
}

class ElementType(object):
    def __init__(self, name, type):
        self.name = name
        self.type = type

class HierDict(dict):
    def __init__(self, parent=None, **kwargs):
        self._parent = parent
        super(HierDict, self).__init__(**kwargs)

    def __getitem__(self, name):
        try:
            return super(HierDict,self).__getitem__(name)
        except KeyError, e:
            if self._parent is None:
                raise
            return self._parent[name]

class TypeParser(object):
    """
        The main TypeParser class parses a given xml schema and 
        produces soaplib ClassSerializers for types found

        Maintains a catalog of parsed elements in elements 
        and of parsed types in ctypes.  If warn is True print
        a warning about unsupported types that are encountered
        during  the parse.
    """
    def __init__(self, document=None, spacer='    ', warn=True, global_ctypes={}, global_elements={}):
        """
            SPACER should move
            init TypeParser
            document - an ElementTree element corresponding
            to the root of the xml schema to parse.
        """
        #global catalogue stores all types
        self.ctypes = HierDict(global_ctypes)
        #global catalogue stores all elements
        self.elements = HierDict(global_elements)
        self.spacer = spacer
        if document is not None:
            self._process_document(document, warn)

    def _process_document(self, document, warn=True):
        self.document = document
        self.nsmap = document.nsmap
        self.tns = None
        self.unsupported = set()
        self.process()
        if warn is True and len(self.unsupported) > 0:
            print "The following schema features not currently supported by soaplib were encountered \
during the parse: \n%s" % "\n".join(self.unsupported) 
            print "---------------------------------------------------------------------------"

    def process(self):
        """
        Begin processing of the supplied document
        
        First processes found complex types, with extract_complex,
        then process found top-level elements with extract_element.
        """
        self.tns = self.document.get('targetNamespace')
        for el in self.document.findall('%scomplexType' % schqname):
            self.extract_complex(el)
        for el in self.document.findall(scelement):
            #pull out top level elements (e.g. used for messages
            #in doc literal).
            self.extract_element(el)
        self.rewire_arrays()

    def extract_element(self, element):
        """ 
        Create an element object based on the supplied element.
        The resulting element is stored in elements and returned.
        """
        typename = element.get('type')
        if typename is not None:
            typ = self.get_class(self.extract_typename(typename))
            klass = self.get_element_class(element.get('name'), typename)
            klass.type = typ
        else:
            #element contains an inline complex type.
            typelist = []
            for child in element.getchildren():
                typelist += self.extract_complex(child, element)
            for (typename, typevalue) in typelist:
                klass = self.get_element_class(element.get('name'), typename)
                klass.type = typevalue
        return [(None, klass)]

    def extract_complex(self, element, parent=None, inuse=False):
        """ 
        Create an complex object based on the supplied element.

        The resulting object is stored in ctypes and returned if created.
        parent - if supplied the parent object can be used to create a class,
            this is used for inline complextypes which are unnamed.  The resulting
            class is created as <nameofparentelement>+CT.
        inuse - if inuse is True the extracted type is flagged as used by another type
            types that are not used e.g. messages are not marked and are not 
            written out by the typeparser.  This prevents add_userResponse being
            created as a ClassSerializer.
        """
        #if element.tag == ccontent:
        #    typelist = []
        #    for child in element.getchildren():
        #        typelist += self.extract_complex(child, inuse=True)
        #    return typelist
        #print 'complexType', element, element.get('name'), parent
        if element.tag == ctype:
            name = element.get('name')
            if name is None:
                name = parent.get('name') + 'CT'
            klass = self.get_class(name, inuse=inuse)
            #attempt to detect a nested array type here 
            #and tag it as an array, we can then later replace the
            #types with their array types in a second parse
            try:
                children = element.xpath('./xs:sequence/xs:element', namespaces={'xs': schnamespace})
                children.extend(element.xpath('./xs:choice/xs:element', namespaces={'xs': schnamespace}))
                if len(children) == 1 and (children[0].get('maxOccurs') == 'unbounded' or 
                    children[0].get('maxOccurs') > 0):
                    child = children[0]
                    typelist = self.extract_complex(child, inuse=True)
                    #items in a soaplib Array are named according to their datatype, 
                    #if this isn't the case we're just have a Repeating wrapped in 
                    #a class so don't tag
                    childtype = typelist.pop()
                    if childtype[0] == childtype[1].serializer.get_datatype():
                        #we have an array so tag it for repointing after we've finished parsing.
                        klass.arraytag = (childtype[0], Array(childtype[1].serializer))
            except Exception, e:
                print e
            typelist = []
            for child in element.getchildren():
                typelist += self.extract_complex(child, inuse=True)
            for (typename, typevalue) in typelist:
                setattr(klass.types, typename, typevalue)
            #reassign metaclass: as dynamically building the class
            #means the metaclass code is run before the types have
            #been set so we re-call it here.
            ClassSerializerMeta.__init__(klass, name, ClassSerializer, {})
            return [(None, klass)]
        elif element.tag == choice:
            typelist = []
            for child in element.getchildren():
                for stype in self.extract_complex(child, inuse=True):
                    if isinstance(stype[1], Optional):
                        typelist.append(stype)
                    else:
                        typelist.append((stype[0], Optional(stype[1])))
            return typelist
        elif element.tag == sequence or element.tag == all:
            typelist = []
            for child in element.getchildren():
                typelist += self.extract_complex(child, inuse=True)
            return typelist
        elif element.tag == scelement:
            minoccurs = element.get('minOccurs')
            etype = element.get('type')
            #cope with nested ctypes
            if etype is None:
                child = element.getchildren()[0]
                typelist = self.extract_complex(child, inuse=True, parent=element)
                try:                
                    (typename, typevalue) = typelist[0]
                    if minoccurs == '0':
                        typevalue = Optional(typevalue)
                    return [(element.get('name'), typevalue)]
                except:
                    return []
            #use qualify_type to search the built-ins using a qname
            #print builtins
            if self.qualify_type(etype) in builtins:
                serializer = builtins[self.qualify_type(etype)]
            else:
                try:
                    serializer = self.get_class(self.extract_typename(etype), inuse=True)
                except Exception,e:
                    print "Exception: %s" % e
                    print "Could not get serializer for type: %s" % etype
                    return []
            #check for array
            
            maxoccurs = element.get('maxOccurs')
            if maxoccurs > 0 or maxoccurs == 'unbounded':
                return [(element.get('name'), Repeating(serializer))]
            else:
                if minoccurs == '0':
                    return [(element.get('name'), Optional(serializer))]
                else:
                    return [(element.get('name'), serializer)]
        elif element.tag == scany:
            if element.get('name'):
                return [(element.get('name'), Any)]
            else:
                return [('any', Any)]
        elif element.tag == stype:
            #yes this is as bad as at looks, we to be able
            #to support restrictions for us
            #to do any better though.
            child = element.getchildren()[0]
            etype = child.get('base')
            if etype in builtins:
                serializer = builtins[etype]
            else:
                try:
                    serializer = self.get_class(self.extract_typename(etype))
                except Exception,e:
                    return []
            return [(element.get('name'), serializer)]
        elif element.tag == scattr:
            self.unsupported.add('attributes')
            return []
        else:
            try:
                if str(element.tag()) == '<!---->':
                    #ignore xml comments
                    return []
            except:
                pass
        self.unsupported.add(element.tag)
        return []

    @classmethod
    def extract_typename(cls,name):
        """
            Split a typename e.g. returning the unqualified name,
            this can be used to create classnames.
        """
        try:
            return name.split(':')[1]
        except:
            return name

    def qualify_type(self, typestr):
        """
            Extract a full qname e.g. {http://example}elementname and return.
            This method is used to extract builtins, contrast with extract_typename.
        """
        try:            
            spl = typestr.split(':')        
            ns = self.nsmap[spl[0]]
            return "{%s}%s" % (ns, spl[1])
        except:
            return "{%s}%s" % (self.tns, typestr)

    def get_class(self, name, inuse=False):
        """
            return a ClassSerializer named name, if the class hasn't previously
            been request create a new class, otherwise return the cached class.
        """
        try:
            klass = self.ctypes["{%s}%s" % (self.tns, name)]
        except:
            typeklass = new.classobj('types', (), {})
            klass = new.classobj(name, (ClassSerializer, object), {'types': typeklass, '__name__': name})
            self.ctypes["{%s}%s" % (self.tns, name)] = klass
        if not getattr(klass, 'inuse', False):
            klass.inuse = inuse
        return klass

    def get_element_class(self, name, type):
        """
            return an ElementType object named name, if this element has
            been previously request return the cached ElementType.
        """
        qname = "{%s}%s" % (self.tns, name)
        try:
            return self.elements[qname]
        except:
            klass = ElementType(name, type)
            self.elements[qname] = klass
            return klass

    def rewire_arrays(self):
        """
            Find all tagged elements and replace the objects with the actual array.
            This step finds all complextypes that are just Arrays such as StringArray
            and treats them correct e.g. Array(String)
        """
        for (k,v) in self.ctypes.items():
            for t in [t for t in dir(v.types) if not t.startswith('_')]:
                value = getattr(v.types, t)
                if hasattr(value, 'arraytag'):
                    setattr(v.types, t, value.arraytag[1])
                    #this type has now been converted to an array and so doesn't need
                    #to be written out
                    value.inuse = False

    def tofile(self, filename):
        """ 
            Write out a python file mapping the parsed xmlschema
            to filename.
        """
        f = open(filename, 'w')
        self.write_imports(f)
        self.write_body(f)
        f.close()

    def write_body(self, f):
        """
            Maintains a dictionary writedict which holds all written
            classes to prevent repeats.
        """
        writedict = {}
        for (k,v) in self.ctypes.items():
            self.write_class(writedict, v, f)
        self.write_elements(f)
    
    def write_imports(self, f):
        """ write the header python imports to f """
        f.write('from soaplib.serializers.clazz import ClassSerializer\n')
        f.write('from soaplib.serializers.primitive import String, DateTime, Integer, Boolean, Float, Array, Any, Repeating\n')
        f.write('from soaplib.serializers.binary import Attachment\n\n')
        
    def write_class(self, writedict, klass, f):
        """ 
            write out the supplied class (klass) to file f.

            writedict - A dictionary of already written classes,
                ensuring each class is only written once.
            The actual writing is done by print_class this, write class
            ensures that all subclasses get written out.
        """
        if self.is_primitive(klass):
            "%s is primitive" % klass
            return
        name = klass.__name__
        if writedict.has_key(name):
            return
        klass = self.ctypes["{%s}%s" % (self.tns, name)]
        if klass.inuse != True:
            return
        for subclass in [mvalue for (mname, mvalue) in inspect.getmembers(klass.types) 
            if  not mname.startswith('__')]:
            #special case to get types out of arrays/repeatings
            if hasattr(subclass, 'serializer'):
                subclass = subclass.serializer
            self.write_class(writedict, subclass, f)
        self.print_class(name, klass, f)
        writedict[name] = 1

    @classmethod
    def is_primitive(cls, obj):
        """ return if the obj supplied is a builtin soaplib object """
        if obj in builtinobj or obj.__class__ in builtinobj:
            #check arrays as they may contain unprimitive types
            try:        
                if obj.__class__ == Array:
                    if obj.serializer in builtinobj:
                        return True
                    else:
                        return False        
            except:
                pass
            return True
        return False

    def print_class(self, name, klass, f):
        """ 
            Writes klass with name to f
        """
        f.write("class %s(ClassSerializer):\n" % name)
        if self.tns:
            f.write("%s__tns__ = '%s'\n" % (self.spacer, self.tns))
        f.write("%sclass types(object):\n" % self.spacer)
        types = [(name, value) for (name, value) in inspect.getmembers(klass.types)
            if not name.startswith('__')]
        #add a pass if no serializers
        if len(types) == 0:
            f.write("%s%spass\n" % (self.spacer, self.spacer))
        for tname, tvalue in types:
            f.write("%s%s%s = %s\n" % (self.spacer, self.spacer, tname, tvalue.print_class()))
        f.write("\n")
    
    def write_elements(self, f):
        """ 
            Write out the dictionary of elements collected from
            the parsed xmlschema.
        """
        f.write("elementdict={\n")
        for (k,v) in self.elements.items():
            if v.type.inuse:
                f.write("%s'%s': %s,\n" % (self.spacer, k, v.type.__name__))
        f.write("}\n")
        
    @classmethod
    def from_url(cls, url):
        """ return a new TypeParser with XSD parsed from the given url """
        f = ulib.urlopen(url)
        d = f.read()
        f.close()
        return cls.from_string(d)

    @classmethod
    def from_string(cls, xml):
        """ return a new TypeParser with XSD parsed from the supplied xml """
        element = ElementTree.fromstring(xml)
        return TypeParser(element)        

def run():
    """ 
        Script for xsd2py, need to setup the script in setup.py
        Run 'xsd2py -h' for command line options.
    """
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-f", "--file", dest="filename",
                  help="read xsd from FILE", metavar="FILE")
    parser.add_option("-u", "--url", dest="url",
                  help="read xsd from URL(not implemented)", metavar="URL")
    parser.add_option("-o", "--output", dest="output",
                  help="output filename.", metavar="OUTPUT", default='xsdtypes.py')
    parser.add_option("-m", "--mapping", dest="mapping",
                  help="Specify any xsd to soaplib type mappings(space seperated).", metavar="MAPPING", default=None)
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
    tp = TypeParser.from_url(url)
    tp.tofile(path.abspath(options.output))
