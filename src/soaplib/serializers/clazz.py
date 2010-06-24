
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

import soaplib

_ns_xs = soaplib.nsmap['xs']

from soaplib.serializers import Base
from soaplib.serializers import nillable_element
from soaplib.serializers import nillable_value

from soaplib.serializers.primitive import Array

class ClassSerializerMeta(type):
    '''
    This is the metaclass that populates ClassSerializer instances with
    the appropriate datatypes for (de)serialization
    '''

    def __new__(cls, cls_name, cls_bases, cls_dict):
        '''
        This initializes the class, and sets all the appropriate types onto the
        class for serialization.
        '''

        cls_dict["__type_name__"] = cls_name

        if not ('_type_info' in cls_dict):
            cls_dict['_type_info'] = _type_info = {}

            for k, v in cls_dict.items():
                if not k.startswith('__'):
                    subc = False
                    try:
                        if issubclass(v,Base):
                            subc = True
                    except:
                        pass

                    if subc:
                        _type_info[k] = v
                        if v is Array and v.serializer is None:
                            raise Exception("%s.%s is an array of what?" %
                                                                  (cls_name, k))

        return type.__new__(cls, cls_name, cls_bases, cls_dict)

class NonExtendingClass(object):
    def __setattr__(self,k,v):
        if not hasattr(self,k) and getattr(self, '__NO_EXTENSION', False):
            raise Exception("'%s' object is not extendable at this point in "
                            "code.\nInvalid member '%s'" %
                                                  (self.__class__.__name__, k) )
        object.__setattr__(self,k,v)

class ClassSerializerBase(NonExtendingClass, Base):
    def __init__(self, **kwargs):
        cls = self.__class__

        for k in cls._type_info.keys():
            setattr(self, k, kwargs.get(k, None))

        self.__NO_EXTENSION=True

    @classmethod
    @nillable_value
    def to_xml(cls, value, name='retval'):
        element = etree.Element("{%s}%s" % (cls.get_namespace(), name))

        for k, v in cls._type_info.items():
            subvalue = getattr(value, k, None)
            print k, subvalue
            subelement = v.to_xml(subvalue, name="{%s}%s" %
                                                 (cls.get_namespace(), k))
            element.append(subelement)

        return element

    @classmethod
    @nillable_element
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
    def add_to_schema(cls, schema_entries):
        if not schema_entries.has_class(cls):
            # complex node
            complex_type = etree.Element("{%s}complexType" % _ns_xs)
            complex_type.set('name',cls.get_type_name())

            sequence = etree.SubElement(complex_type, '{%s}sequence'% _ns_xs)

            for k, v in cls._type_info.items():
                member = etree.SubElement(sequence, '{%s}element' % _ns_xs)
                member.set('name', k)
                member.set('minOccurs', '0')
                member.set('type', v.get_type_name_ns())

            schema_entries.add_complex_node(cls, complex_type)

            # simple node
            element = etree.Element('{%s}element' % _ns_xs)
            element.set('name',cls.get_type_name())
            element.set('type',cls.get_type_name_ns())

            schema_entries.add_simple_node(cls, element)

            # add member nodes
            for k, v in cls._type_info.items():
                v.add_to_schema(schema_entries)

class ClassSerializer(ClassSerializerBase):
    """
    The general complexType factory. Attempts to instantiate this class will
    result in *gasp* instances, contrary to primivites where a similar attempt
    will result in customized duplicates of the original class definition.
    Those who'd like to customize the class should use the customize method.
    (see soaplib.serializers.base.Base)
    """

    __metaclass__ = ClassSerializerMeta
