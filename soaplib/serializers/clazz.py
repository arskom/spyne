import inspect
import cElementTree as ElementTree

from primitive import Null

class ClassSerializerMeta(type):
    '''
    This is the metaclass that populates ClassSerializer instances with
    the appropriate datatypes for (de)serialization
    '''

    def __init__(cls, clsname, bases, dictionary):
        '''
        This initializes the class, and sets all the appropriate
        types onto the class for serialization.  This implemenation
        assumes that all attributes assigned to this class  are internal 
        serialzers for this class
        '''
        if not hasattr(cls,'types'):
            return
        types = cls.types
        members = dict(inspect.getmembers(types))
        cls.soap_members = {}
        cls.namespace = None
        
        for k,v in members.items():
            if k == '_namespace_':
                cls.namespace=v
                
            elif not k.startswith('__'):
                cls.soap_members[k] = v
        
        # COM bridge attributes that are otherwise harmless
        cls._public_methods_ = []
        cls._public_attrs_ = cls.soap_members.keys()

class ClassSerializer(object):
    __metaclass__ = ClassSerializerMeta

    def __init__(self):
        cls = self.__class__
        for k,v in cls.soap_members.items():
            setattr(self,k,None)

    @classmethod
    def to_xml(cls,value,name='retval'):
        if cls.namespace:
            name = '{%s}%s'%(cls.namespace,name)
        
        element = ElementTree.Element(name)
        if not cls.namespace:
            element.set('xmlns','')
            
        for k,v in cls.soap_members.items():
            member_value = getattr(value,k,None)    

            subvalue = getattr(value,k,None)
            if subvalue is None:
                v = Null
                
            subelement = v.to_xml(subvalue,name=k)
            element.append(subelement)

        return element

    @classmethod
    def from_xml(cls, element):
        obj = cls()
        children = element.getchildren()
        for child in children:
            tag = child.tag.split('}')[-1]
            member = cls.soap_members.get(tag)
            
            value = member.from_xml(child)
            setattr(obj,tag,value)
        return obj

    @classmethod
    def get_datatype(cls,withNamespace=False):
        if withNamespace:
            return 'tns:%s'%(cls.__name__)
        return cls.__name__
 
    @classmethod
    def add_to_schema(cls, schemaDict):
        
        if not schemaDict.has_key(cls.get_datatype(True)):
            for k,v in cls.soap_members.items():
                v.add_to_schema(schemaDict)

            schema_node = ElementTree.Element('xs:complexType')
            schema_node.set('name',cls.__name__)

            sequence_node = ElementTree.SubElement(schema_node,'xs:sequence')
            for k,v in cls.soap_members.items():
                member_node = ElementTree.SubElement(sequence_node,'xs:element')
                member_node.set('name',k)
                member_node.set('minOccurs','0')
                member_node.set('type',v.get_datatype(True))

            typeElement = ElementTree.Element("xs:element")
            typeElement.set('name',cls.__name__)
            typeElement.set('type','tns:'+cls.__name__)
            schemaDict[cls.get_datatype(True)+'Complex'] = schema_node
            schemaDict[cls.get_datatype(True)] = typeElement
