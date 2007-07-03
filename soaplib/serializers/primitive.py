import cElementTree as ElementTree
import datetime
import re
import cStringIO 

import pytz
from pytz.reference import FixedOffset

#######################################################
# Utility Functions
#######################################################

string_encoding = 'utf-8'

_utc_re = re.compile('[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}.?[0-9]{0,6}Z')
_offset_re = re.compile('[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3,9}[\+|\-][0-9]{2}:?[0-9]{2}.?[0-9]{0,6}')
_local_re = re.compile('[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}.?[0-9]{0,6}')
_local_trunk_re = re.compile('[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}.?[0-9]{0,6}')

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
    
    def parse_date(s):
        return s.split('-')
    
    def utc(text):
        text = text[0:-1]
        d,t = text.split('T')
        
        y,m,d = parse_date(d)
        
        if  t.find('.') > -1:
            t,rest = t.split(".")
        else:
            rest = '0'
        # pad the microseconds out appropriately
        rest = rest[0:5]
        rest = rest+'0'*(6-len(rest))
        
        hr,mi,se = t.split(':')
        
        dt = datetime.datetime(int(y),int(m),int(d),int(hr),int(mi),int(se),int(rest),pytz.utc)
        return dt

    def offset(text):
        date,t = text.split('T')
        y,m,d = parse_date(date)

        sep = '+'
        if t.find('-') > -1:
            sep = '-'
        
        t,offset = t.split(sep)
        
        if offset.find(':') > -1:
            offset_hours,offset_min = offset.split(':')
            offset_hours = int(offset_hours)
            offset_min = int(offset_min)
        else:
            offset_hours = int(offset[0:1])
            offset_min = int(offset[2:3])
        
        if t.find('.') > 1:
            t,rest = t.split(".")
        else:
            rest = '0'
        # pad the microseconds out appropriately
        rest = rest[0:6]
        rest = rest+'0'*(6-len(rest))

        hr,mi,se = t.split(':')        
        offset_hours, offset_min

        offset_min = offset_min + 60*offset_hours
        if sep == '-':
            offset_min = -1 * offset_min
        dt = datetime.datetime(int(y),int(m),int(d),int(hr),int(mi),int(se),int(rest),FixedOffset(offset_min,{}))

        return dt

    def local(text):
        date,time = text.split('T')
        y,m,d = parse_date(date)

        micro = 0
        if time.find('.') > -1:
            rest = time.split('.')[-1]
            rest = rest[0:6]
            rest = rest+'0'*(6-len(rest))
            micro = rest
        hr,mi,se = time.split('.')[0].split(':')
        return datetime.datetime(int(y),int(m),int(d),int(hr),int(mi),int(se),int(micro))
        
    if _utc_re.match(text):
        d = utc(text)
        return d
    elif _offset_re.match(text):
        return offset(text)
    elif _local_re.match(text) or _local_trunk_re.match(text):
        return local(text)
    else:
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
    retval = ElementTree.Element(name)
    if value == None:
        return Null.to_xml(value,name)
    if type(value) == unicode:
        retval.text = value
    else: 
        retval.text = unicode(value,string_encoding)
    retval.set('xsi:type',typ)
    return retval

def _generic_to_xml(value,name,typ):
    retval = ElementTree.Element(name)
    if value:
        retval.text = value
    retval.set('xsi:type',typ)
    return retval

class Any:

    @classmethod
    def to_xml(cls,value,name='retval'):
        if type(value) == str:
            value = ElementTree.fromstring(value)
        e = ElementTree.Element(name)
        e.set('xmlns','')
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
            return 'xs:anyType'
        return 'anyType'

    @classmethod
    def add_to_schema(cls,added_params):
        pass

class String:

    @classmethod
    def to_xml(cls,value,name='retval'):
        e = _unicode_to_xml(value,name,cls.get_datatype(True))
        e.set('xmlns','')
        return e
        
    @classmethod
    def from_xml(cls,element):
        return _element_to_unicode(element)

    @classmethod
    def get_datatype(cls,withNamespace=False):
        if withNamespace:
            return 'xs:string'
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
    def to_xml(cls, value, name='SOAP-ENV:Fault'):
        
        fault = ElementTree.Element(name)
        ElementTree.SubElement(fault, 'faultcode').text = value.faultcode
        ElementTree.SubElement(fault, 'faultstring').text = value.faultstring
        detail = ElementTree.SubElement(fault, 'detail').text = value.detail
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
        complexTypeNode = ElementTree.Element('complexType')
        complexTypeNode.set('name', cls.get_datatype())        
        sequenceNode = ElementTree.SubElement(complexTypeNode, 'sequence')
        faultTypeElem = ElementTree.SubElement(sequenceNode,'element')
        faultTypeElem.set('name','detail')
        faultTypeElem.set('type','xs:string')
        faultTypeElem = ElementTree.SubElement(sequenceNode,'element')
        faultTypeElem.set('name','message')
        faultTypeElem.set('type','xs:string')
    
        schema_dict[cls.get_datatype()] = complexTypeNode
        
        typeElementItem = ElementTree.Element('element')
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
        e.set('xmlns','')
        return e
    
    @classmethod
    def from_xml(cls,element):
        return _element_to_integer(element)

    @classmethod
    def get_datatype(cls,withNamespace=False):
        if withNamespace:
            return 'xs:int'
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
        e.set('xmlns','')
        return e
    
    @classmethod
    def from_xml(cls,element):
        return _element_to_datetime(element)            

    @classmethod
    def get_datatype(cls,withNamespace=False):
        if withNamespace:
            return 'xs:dateTime'
        return 'dateTime'

    @classmethod
    def add_to_schema(cls,added_params):
        pass

class Float:

    @classmethod
    def to_xml(cls,value,name='retval'):
        e = _generic_to_xml(str(value),name,cls.get_datatype(True))    
        e.set('xmlns','')
        return e
    
    @classmethod
    def from_xml(cls,element):
        return _element_to_float(element)

    @classmethod
    def get_datatype(cls,withNamespace=False):
        if withNamespace:
            return 'xs:float'
        return 'float'

    @classmethod
    def add_to_schema(cls,added_params):
        pass

class Null:

    @classmethod
    def to_xml(cls,value,name='retval'):
        element = ElementTree.Element(name)
        element.set('xs:null','1')
        return element
    
    @classmethod
    def from_xml(cls,element):
        return None

    @classmethod
    def get_datatype(cls,withNamespace=False):
        if withNamespace:
            return 'xs:null'
        return 'null'

    @classmethod
    def add_to_schema(cls,added_params):
        pass

class Boolean:
    
    @classmethod
    def to_xml(cls,value,name='retval'):
        e = _generic_to_xml(str(value).lower(),name,cls.get_datatype(True))    
        e.set('xmlns','')
        return e
    
    @classmethod
    def from_xml(cls,element):
        s = _element_to_string(element)
        if s and s.lower()[0] == 't':
            return True
        return False

    @classmethod
    def get_datatype(cls,withNamespace=False):
        if withNamespace:
            return 'xs:boolean'
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
        res = ElementTree.Element(name)
        typ = self.get_datatype(True)
        res.set('xmlns','') 
        if values == None:
            values = []
        res.set('xsi:type',self.get_datatype(True))
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

            complexTypeNode = ElementTree.Element("xs:complexType")
            complexTypeNode.set('name',self.get_datatype(False))

            sequenceNode = ElementTree.SubElement(complexTypeNode, 'xs:sequence')
            elementNode = ElementTree.SubElement(sequenceNode, 'xs:element')
            elementNode.set('minOccurs','0')
            elementNode.set('maxOccurs','unbounded')
            elementNode.set('type',self.serializer.get_datatype(True))
            elementNode.set('name',self.serializer.get_datatype(False))

            typeElement = ElementTree.Element("xs:element")            
            typeElement.set('name',typ)
            typeElement.set('type',self.get_datatype(True))
            
            schema_dict['%sElement'%(self.get_datatype(True))] = typeElement
            schema_dict[self.get_datatype(True)] = complexTypeNode

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
        element = ElementTree.Element(name)
        for k,v in data.items():
            item = ElementTree.SubElement(element,'%sItem'%self.get_datatype())
            key = ElementTree.SubElement(item,'key')
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
            itemNode = ElementTree.Element('complexType')
            itemNode.set('name','%sItem'%typ)

            sequence = ElementTree.SubElement(itemNode,'sequence')

            key_node = ElementTree.SubElement(sequence,'element')
            key_node.set('name','key')
            key_node.set('minOccurs','1')
            key_node.set('type','xs:string')

            value_node = ElementTree.SubElement(sequence,'element')
            value_node.set('name','value')
            value_node.set('minOccurs','1')
            value_node.set('type',self.serializer.get_datatype(True))

            complexTypeNode = ElementTree.Element("complexType")
            complexTypeNode.set('name',typ)

            sequenceNode = ElementTree.SubElement(complexTypeNode, 'sequence')
            elementNode = ElementTree.SubElement(sequenceNode, 'element')
            elementNode.set('minOccurs','0')
            elementNode.set('maxOccurs','unbounded')
            elementNode.set('name','%sItem'%typ)
            elementNode.set('type','tns:%sItem'%typ)

            schema_dict[self.get_datatype(True)] = complexTypeNode
            schema_dict['tns:%sItem'%typ] = itemNode 

            typeElement = ElementTree.Element("element")
            typeElement.set('name',typ)
            typeElement.set('type',self.get_datatype(True))
            schema_dict['%sElement'%(self.get_datatype(True))] = typeElement

            typeElementItem = ElementTree.Element("element")
            typeElementItem.set('name','%sItem'%typ)
            typeElementItem.set('type','%sItem'%self.get_datatype(True))            
            schema_dict['%sElementItem'%(self.get_datatype(True))] = typeElementItem            


