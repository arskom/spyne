from soaplib.xml import *
import datetime
import re
import cStringIO 

import pytz
from pytz import FixedOffset

#######################################################
# Utility Functions
#######################################################

string_encoding = 'utf-8'

_datetime_pattern = r'(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})[T ](?P<hr>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})(?P<fractional_sec>\.\d+)?'
_local_re = re.compile(_datetime_pattern)
_utc_re = re.compile(_datetime_pattern + 'Z')
_offset_re = re.compile(_datetime_pattern + r'(?P<tz_hr>[+-]\d{2}):(?P<tz_min>\d{2})')

def _is_null_element(element):
    for k in element.keys():
        if k.endswith('null'):
            return True
    return False

def _element_to_datetime(element):
    # expect ISO formatted dates
    # 
    text = element.text
    if not text:
        return None
    
    def parse_date(date_match, tz=None):
        fields = date_match.groupdict(0)
        year, month, day, hr, min, sec = [ int(fields[x]) for x in 
           ("year", "month", "day", "hr", "min", "sec")]
        # use of decimal module here (rather than float) might be better
        # here, if willing to require python 2.4 or higher
        microsec = int(float(fields.get("fractional_sec", 0)) * 10**6)
        return datetime.datetime(year, month, day, hr, min, sec, microsec, tz)
    
    match = _utc_re.match(text)
    if match:
        return parse_date(match, tz=pytz.utc)
    match = _offset_re.match(text)
    if match:
        tz_hr, tz_min = [int(match.group(x)) for x in "tz_hr", "tz_min"]
        return parse_date(match, tz=FixedOffset(tz_hr*60 + tz_min, {}))
    match = _local_re.match(text)
    if match:
        return parse_date(match)
    raise Exception("DateTime [%s] not in known format"%text)

def _element_to_string(element):
    text = element.text
    if text:
        return text.decode(string_encoding)
    else:
        return None

def _element_to_integer(element):
    i = element.text
    if not i:
        return None
    try: 
        return int(str(i))
    except: 
        try: return long(i)
        except: return None

def _element_to_float(element):
    f = element.text
    if f is None:
        return None
    return float(f)

def _element_to_unicode(element):
    u = element.text
    if not u:
        return None
    try:
       u = str(u)
       return u.encode(string_encoding)
    except:
       return u

def _unicode_to_xml(value,name,typ):
    retval = create_xml_element(name)
    if value == None:
        return Null.to_xml(value,name)
    if type(value) == unicode:
        retval.text = value
    else: 
        retval.text = unicode(value,string_encoding)
    retval.set(qualify('type', ns['xsi']),typ)
    return retval

def _generic_to_xml(value,name,typ):
    retval = create_xml_element(name)
    if value:
        retval.text = value
    retval.set(qualify('type', ns['xsi']),typ)
    return retval

class Any:

    @classmethod
    def to_xml(cls,value,name='retval'):
        if type(value) == str:
            value = ElementTree.fromstring(value)
        e = create_xml_element(name)
        e.append(value) 
        return e 
        
    @classmethod
    def from_xml(cls,element):
        children = element.getchildren()
        if children:
            return element.getchildren()[0]
        return None

    @classmethod
    def get_datatype(cls,withNamespace=False):
        if withNamespace:
            return qualify('anyType', ns['xs'])
        return 'anyType'

    @classmethod
    def add_to_schema(cls,added_params):
        pass

class String:

    @classmethod
    def to_xml(cls,value,name='retval'):
        e = _unicode_to_xml(value,name,cls.get_datatype(True))
        return e
        
    @classmethod
    def from_xml(cls,element):
        return _element_to_unicode(element)

    @classmethod
    def get_datatype(cls,withNamespace=False):
        if withNamespace:
            return qualify('string', ns['xs'])
        return 'string'

    @classmethod
    def add_to_schema(cls,added_params):
        pass

class Fault(Exception):

    def __init__(self, faultcode = 'Server', faultstring = None, detail = None, name = 'ExceptionFault'):
        self.faultcode = faultcode
        self.faultstring = faultstring
        self.detail = detail
        self.name = name

    @classmethod
    def to_xml(cls, value, name=qualify("Fault", ns["SOAP-ENV"])):
        fault = create_xml_element(name)
        create_xml_subelement(fault, 'faultcode').text = value.faultcode
        create_xml_subelement(fault, 'faultstring').text = value.faultstring
        detail = create_xml_subelement(fault, 'detail').text = value.detail
        return fault


    @classmethod
    def from_xml(cls, element):
        code = _element_to_string(element.find('faultcode'))
        string = _element_to_string(element.find('faultstring'))
        detail_element = element.find('detail')
        if detail_element:
            if len(detail_element.getchildren()):
                detail = ElementTree.tostring(detail_element)
            else:
                detail = _element_to_string(element.find('detail'))
        else:
            detail = ''
        return Fault(faultcode = code, faultstring = string, detail = detail)
        
    @classmethod
    def get_datatype(cls,withNamespace=False):
        t = 'ExceptionFaultType'
        if withNamespace:
            return 'tns:%s'%t
        return t

    @classmethod
    def add_to_schema(cls,schema_dict):   
        complexTypeNode = create_xml_element('complexType')
        complexTypeNode.set('name', cls.get_datatype())        
        sequenceNode = create_xml_subelement(complexTypeNode, 'sequence')
        faultTypeElem = create_xml_subelement(sequenceNode,'element')
        faultTypeElem.set('name','detail')
        faultTypeElem.set('type','xs:string')
        faultTypeElem = create_xml_subelement(sequenceNode,'element')
        faultTypeElem.set('name','message')
        faultTypeElem.set('type','xs:string')
    
        schema_dict[cls.get_datatype()] = complexTypeNode
        
        typeElementItem = create_xml_element('element')
        typeElementItem.set('name', 'ExceptionFaultType')
        typeElementItem.set('type', cls.get_datatype(True))
        schema_dict['%sElement'%(cls.get_datatype(True))] = typeElementItem
        
    def __str__(self):
        io = cStringIO.StringIO()
        io.write("*"*80)
        io.write("\r\n")
        io.write(" Recieved soap fault \r\n")
        io.write(" FaultCode            %s \r\n"%self.faultcode)
        io.write(" FaultString          %s \r\n"%self.faultstring)
        io.write(" FaultDetail          \r\n")
        io.write(self.detail)
        return io.getvalue()

class Integer:

    @classmethod
    def to_xml(cls,value,name='retval'):
        e = _generic_to_xml(str(value),name,cls.get_datatype(True))
        return e
    
    @classmethod
    def from_xml(cls,element):
        return _element_to_integer(element)

    @classmethod
    def get_datatype(cls,withNamespace=False):
        if withNamespace:
            return qualify('int', ns['xs'])
        return 'int'

    @classmethod
    def add_to_schema(cls,added_params):
        pass

class DateTime:

    @classmethod
    def to_xml(cls,value,name='retval'):
        if type(value) == datetime.datetime:
            value = value.isoformat('T')
        e = _generic_to_xml(value,name,cls.get_datatype(True))    
        return e
    
    @classmethod
    def from_xml(cls,element):
        return _element_to_datetime(element)            

    @classmethod
    def get_datatype(cls,withNamespace=False):
        if withNamespace:
            return qualify('dateTime', ns['xs'])
        return 'dateTime'

    @classmethod
    def add_to_schema(cls,added_params):
        pass

class Float:

    @classmethod
    def to_xml(cls,value,name='retval'):
        e = _generic_to_xml(str(value),name,cls.get_datatype(True))
        return e
    
    @classmethod
    def from_xml(cls,element):
        return _element_to_float(element)

    @classmethod
    def get_datatype(cls,withNamespace=False):
        if withNamespace:
            return qualify('float', ns['xs'])
        return 'float'

    @classmethod
    def add_to_schema(cls,added_params):
        pass

class Null:

    @classmethod
    def to_xml(cls,value,name='retval'):
        element = create_xml_element(name)
        element.set(qualify('null', ns['xs']),'1')
        return element
    
    @classmethod
    def from_xml(cls,element):
        return None

    @classmethod
    def get_datatype(cls,withNamespace=False):
        if withNamespace:
            return qualify('null', ns['xs'])
        return 'null'

    @classmethod
    def add_to_schema(cls,added_params):
        pass

class Boolean:
    
    @classmethod
    def to_xml(cls,value,name='retval'):
        # applied patch from Julius Volz
        #e = _generic_to_xml(str(value).lower(),name,cls.get_datatype(True))    
        if value == None:
            return Null.to_xml('',name)
        else:
            e = _generic_to_xml(str(bool(value)).lower(),name,cls.get_datatype(True))
        return e
    
    @classmethod
    def from_xml(cls,element):
        s = _element_to_string(element)
        if s == None: 
            return None
        if s and s.lower()[0] == 't':
            return True
        return False

    @classmethod
    def get_datatype(cls,withNamespace=False):
        if withNamespace:
            return qualify('boolean', ns['xs'])
        return 'boolean'

    @classmethod
    def add_to_schema(cls,added_params):
        pass
    
class Array:
    
    def __init__(self,serializer,type_name=None,namespace='tns'):
        self.serializer = serializer
        self.namespace = namespace
        if not type_name:
            self.type_name = '%sArray'%self.serializer.get_datatype()
        else:
            self.type_name = type_name

    def to_xml(self,values,name='retval'):
        res = create_xml_element(name)
        typ = self.get_datatype(True)
        if values == None:
            values = []
        res.set(qualify('type', ns['xsi']),self.get_datatype(True))
        for value in values:
            serializer = self.serializer
            if value == None:
                serializer = Null
            res.append(
                serializer.to_xml(value,name=serializer.get_datatype(False))
            )
        return res    

    def from_xml(self,element):
        results = []
        for child in element.getchildren():
            results.append(self.serializer.from_xml(child))
        return results

    def get_datatype(self,withNamespace=False):
        if withNamespace:
            return '%s:%s'%(self.namespace,self.type_name)
        return self.type_name

    def add_to_schema(self,schema_dict):
        typ = self.get_datatype()
        
        self.serializer.add_to_schema(schema_dict)

        if not schema_dict.has_key(typ):

            tag = qualify('complexType', ns['xs'])
            complexTypeNode = create_xml_element(tag)
            complexTypeNode.set('name',self.get_datatype(False))

            sequenceNode = create_xml_subelement(
                complexTypeNode, 
                qualify('sequence', ns['xs'])
            )
            elementNode = create_xml_subelement(
                sequenceNode, 
                qualify('element', ns['xs'])
            )
            elementNode.set('minOccurs','0')
            elementNode.set('maxOccurs','unbounded')
            elementNode.set('type',self.serializer.get_datatype(True))
            elementNode.set('name',self.serializer.get_datatype(False))

            tag = qualify('element', ns['xs'])
            typeElement = create_xml_element(tag)         
            typeElement.set('name',typ)
            typeElement.set('type',self.get_datatype(True))
            
            schema_dict['%sElement'%(self.get_datatype(True))] = typeElement
            schema_dict[self.get_datatype(True)] = complexTypeNode

class Repeating(object):

    def __init__(self,serializer,type_name=None,namespace='tns'):
        self.serializer = serializer
        
    def to_xml(self,values,name='retval'):
        if values == None:
            values = []
        res = []
        for value in values:
            serializer = self.serializer
            if value == None:
                serializer = Null
            res.append(
                serializer.to_xml(value,name=name)
            )
        return res    

    def from_xml(self,*elements):
        results = []
        for child in elements:
            results.append(self.serializer.from_xml(child))
        return results    
        
    def add_to_schema(self,schema_dict):
        raise Exception("The Repeating serializer is experimental and not supported for wsdl generation")
        
###################################################################
# Deprecated Functionality
###################################################################
class SoapFault(Fault):
    def __init__(self,*args,**kwargs):
        from warnings import warn
        warn("The SoapFault class will be deprecated, use the 'Fault' class",DeprecationWarning)
        Fault.__init__(self,*args,**kwargs)

class Map:

    def __init__(self,serializer):
        from warnings import warn
        warn("The Map serializer will be deprecated, use the 'Any' class",DeprecationWarning)
        self.serializer = serializer

    def to_xml(self,data, name='xsd:retval'):
        element = create_xml_element(name)
        for k,v in data.items():
            item = create_xml_subelement(element,'%sItem'%self.get_datatype())
            key = create_xml_subelement(item,'key')
            key.text = k
            ser = self.serializer
            if v == None:
                ser = Null
            item.append(ser.to_xml(v,'value'))
        return element

    def from_xml(self,element):
        data = {}
        for item in element.getchildren():
            value = item.find('value')
            key = item.find('key')
            assert(len(item.getchildren()) == 2)

            children = item.getchildren()
            if children[0].tag.lower().endswith('key'):
                key = children[0]
                value = children[1]
            else:
                key = children[1]
                value = children[0]
            if _is_null_element(value):
                data[key.text] = Null.from_xml(value)
            else:
                data[key.text] = self.serializer.from_xml(value)
        return data

    def get_datatype(self,withNamespace=False):
        typ = self.serializer.get_datatype()
        if withNamespace:
            if hasattr(self.serializer,'prefix'):
                return '%s:%sMap'%(self.serializer.prefix,typ)
            else:
                return 'tns:%sMap'%(typ)
        return '%sMap'%typ

    def add_to_schema(self,schema_dict):
        typ = self.get_datatype()
        self.serializer.add_to_schema(schema_dict)

        if not schema_dict.has_key(typ):

            # items
            itemNode = create_xml_element('complexType')
            itemNode.set('name','%sItem'%typ)

            sequence = create_xml_subelement(itemNode,'sequence')

            key_node = create_xml_subelement(sequence,'element')
            key_node.set('name','key')
            key_node.set('minOccurs','1')
            key_node.set('type','xs:string')

            value_node = create_xml_subelement(sequence,'element')
            value_node.set('name','value')
            value_node.set('minOccurs','1')
            value_node.set('type',self.serializer.get_datatype(True))

            complexTypeNode = create_xml_element("complexType")
            complexTypeNode.set('name',typ)

            sequenceNode = create_xml_subelement(complexTypeNode, 'sequence')
            elementNode = create_xml_subelement(sequenceNode, 'element')
            elementNode.set('minOccurs','0')
            elementNode.set('maxOccurs','unbounded')
            elementNode.set('name','%sItem'%typ)
            elementNode.set('type','tns:%sItem'%typ)

            schema_dict[self.get_datatype(True)] = complexTypeNode
            schema_dict['tns:%sItem'%typ] = itemNode 

            typeElement = create_xml_element("element")
            typeElement.set('name',typ)
            typeElement.set('type',self.get_datatype(True))
            schema_dict['%sElement'%(self.get_datatype(True))] = typeElement

            typeElementItem = create_xml_element("element")
            typeElementItem.set('name','%sItem'%typ)
            typeElementItem.set('type','%sItem'%self.get_datatype(True))            
            schema_dict['%sElementItem'%(self.get_datatype(True))] = typeElementItem            


