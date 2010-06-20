
#
# soaplib - Copyright (C) Soaplib contributors.
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

from lxml import etree

from soaplib import nsmap

from soaplib.serializers import Base
from soaplib.serializers import SchemaInfo
from soaplib.serializers import nillable_element
from soaplib.serializers import nillable_value

from soaplib.serializers.primitive import Array

class ClassSerializerMeta(type):
    '''
    This is the metaclass that populates ClassSerializer instances with
    the appropriate datatypes for (de)serialization
    '''

    def __init__(cls, cls_name, cls_bases, cls_dict):
        '''
        This initializes the class, and sets all the appropriate
        types onto the class for serialization.  This implementation
        assumes that all attributes assigned to this class  are internal
        serializers for this class
        '''

        cls._type_info = {}
        cls.__type_name__ = cls.__name__
        cls.set_namespace(cls.__module__)
        
        for k, v in cls_dict.items():
            if k == '__namespace__':
                cls.set_namespace(v)

            elif k == '__type_name__':
                cls.__type_name__ = v
                
            elif not k.startswith('__'):
                subc = False
                try:
                    if issubclass(v,Base):
                        subc = True
                except:
                    pass
                    
                if subc:
                    cls._type_info[k] = v
                    if v is Array:
                        #print "%-30s" % cls_name, "%-30s" % k, v, v.serializer
                        if v.serializer is None:
                            raise Exception(
                                "%s.%s is an array of what?" % (cls.get_type_name(), k))

class NonExtendingClass(object):
    def __setattr__(self,k,v):
        if not hasattr(self,k) and getattr(self, 'NO_EXTENSION', False):
            raise Exception("'%s' object is not extendable at this point in "
                            "code.\nInvalid member '%s'" %
                                                  (self.__class__.__name__, k) )
        object.__setattr__(self,k,v)

class ClassSerializerBase(NonExtendingClass, Base):
    def __init__(self, **kwargs):
        cls = self.__class__

        for k in cls._type_info.keys():
            setattr(self, k, kwargs.get(k, None))

        self.NO_EXTENSION=True

    @nillable_value
    @classmethod
    def to_xml(cls, value, name='retval'):
        element = etree.Element("{%s}%s" % (cls._type_info.namespace, name))

        for k, v in cls._type_info.items():
            subvalue = getattr(value, k, None)
            subelement = v.to_xml(subvalue, name="{%s}%s" %
                                                 (cls._type_info.namespace, k))
            element.append(subelement)

        return element

    @nillable_element
    @classmethod
    def from_xml(cls, element):
        children = element.getchildren()
        d = {}
        for c in children:
            name = c.tag.split('}')[-1]
            if not name in d:
                d[name] = []
            d[name].append(c)

        for k,v in d.items():
            member = cls._type_info.get(k)
            if member is None:
                raise Exception('the %s object does not have a "%s" member' %
                                                              (cls.__name__,k))

            value = member.from_xml(*v)
            setattr(cls, k, value)

        return cls

    @classmethod
    def add_to_schema(cls, schema_dict):
        try:
            schema_dict[cls.get_namespace_prefix()].complex[cls.get_type_name()]
            
        except KeyError:
            complex_type = etree.Element("{%(xs)s}complexType" % nsmap)
            complex_type.set('name',cls.get_type_name())

            sequence = etree.SubElement(complex_type, '{%(xs)s}sequence'% nsmap)

            for k, v in cls._type_info.items():
                member = etree.SubElement(sequence, '{%(xs)s}element' % nsmap)
                member.set('name', k)
                member.set('minOccurs', '0')
                member.set('type', v.get_type_name_ns())

            element = etree.Element('{%(xs)s}element' % nsmap)
            element.set('name',cls.get_type_name())
            element.set('type',cls.get_type_name_ns())

            ns_dict = schema_dict.get(cls.get_namespace_prefix(), SchemaInfo())
            ns_dict.simple[cls.get_type_name()] = element
            ns_dict.complex[cls.get_type_name()] = complex_type
            schema_dict[cls.get_namespace_prefix()] = ns_dict
            
            for k, v in cls._type_info.items():
                v.add_to_schema(schema_dict)

class ClassSerializer(ClassSerializerBase):
    __metaclass__ = ClassSerializerMeta
