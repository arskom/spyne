
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

from soaplib.serializers import Base
from soaplib.serializers import nillable_element
from soaplib.serializers import nillable_value

from soaplib.serializers.primitive import Array

from soaplib.util.odict import odict as TypeInfo

class ClassSerializerMeta(type):
    '''
    This is the metaclass that populates ClassSerializer instances with
    the appropriate datatypes for (de)serialization.
    '''

    def __new__(cls, cls_name, cls_bases, cls_dict):
        '''
        This initializes the class, and sets all the appropriate types onto the
        class for serialization.
        '''

        type_name = cls_dict.get("__type_name__", None)
        if type_name is None:
            cls_dict["__type_name__"] = cls_name

        # get base class (if exists) and enforce single inheritance
        extends = cls_dict.get("__extends__", None)
        if cls_name == "ExtensionClass":
            print cls_name, cls_bases

        if extends is None:
            for b in cls_bases:
                base_types = getattr(b, "_type_info", None)

                if not (base_types is None):
                    assert extends is None or cls_dict["__extends__"] is b, \
                                "WSDL 1.1 does not support multiple inheritance"

                    try:
                        if len(base_types) > 0 and issubclass(b, Base):
                            cls_dict["__extends__"] = extends = b
                    except:
                        print extends
                        raise

        # populate soap members
        if not ('_type_info' in cls_dict):
            cls_dict['_type_info'] = _type_info = TypeInfo()

            for k,v in cls_dict.items():
                if not k.startswith('__'):
                    subc = False
                    try:
                        if issubclass(v,Base):
                            subc = True
                    except:
                        pass

                    if subc:
                        _type_info[k] = v
                        if issubclass(v, Array) and v.serializer is None:
                            raise Exception("%s.%s is an array of what?" %
                                                                  (cls_name, k))
        else:
            _type_info = cls_dict['_type_info']
            if not isinstance(_type_info, TypeInfo):
                cls_dict['_type_info'] = TypeInfo(_type_info)

        return type.__new__(cls, cls_name, cls_bases, cls_dict)

class NonExtendingClass(object):
    def __setattr__(self, k, v):
        if not hasattr(self,k) and getattr(self, '__NO_EXTENSION', False):
            raise Exception("'%s' object is not extendable at this point in "
                            "code.\nInvalid member '%s'" %
                                                  (self.__class__.__name__, k) )
        object.__setattr__(self,k,v)

class ClassSerializerBase(NonExtendingClass, Base):
    """
    If you want to make a better class serializer, this is what you should
    inherit from
    """

    def __init__(self, **kwargs):
        cls = self.__class__

        for k in cls._type_info.keys():
            setattr(self, k, kwargs.get(k, None))

        self.__NO_EXTENSION=True

    def __len__(self):
        return len(self._type_info)

    def __getitem__(self,i):
        return getattr(self, self._type_info.keys()[i], None)

    @classmethod
    @nillable_value
    def to_xml(cls, value, tns, name=None, element=None):
        if name is None:
            name = cls.get_type_name()

        if element is None:
            element = etree.Element("{%s}%s" % (cls.get_namespace(), name))

        if isinstance(value, list) or isinstance(value, tuple):
            assert len(value) <= len(cls._type_info)

            array = value
            value = cls()

            keys = cls._type_info.keys()
            for i in range(len(array)):
                setattr(value, keys[i], array[i])

        elif isinstance(value, dict):
            map = value
            value = cls()

            for k,v in map.items():
                if k in cls._type_info:
                    setattr(value, k, v)
                else:
                    raise KeyError(k)

        for k, v in cls._type_info.items():
            subvalue = getattr(value, k, None)
            subelement = v.to_xml(subvalue, cls.get_namespace(), k)
            element.append(subelement)

        clz = getattr(cls,'__extends__', None)
        while not (clz is None):
            clz.to_xml(value, tns, name, element)
            clz = getattr(clz,'__extends__', None)

        return element

    @classmethod
    @nillable_element
    def from_xml(cls, element):
        inst = cls()
        children = element.getchildren()

        for c in children:
            if isinstance(c, etree._Comment):
                continue
            key = c.tag.split('}')[-1]

            member = cls._type_info.get(key, None)
            clz = getattr(cls,'__extends__', None)
            while not (clz is None) and (member is None):
                member = clz._type_info.get(key, None)
                clz = getattr(clz,'__extends__', None)

            if member is None:
                raise Exception('the %s object does not have a "%s" member' %
                                                             (cls.__name__,key))

            value = member.from_xml(c)
            setattr(inst, key, value)

        return inst

    @classmethod
    def resolve_namespace(cls, default_ns):
        if getattr(cls, '__extends__', None) != None:
            cls.__extends__.resolve_namespace(default_ns)
            if not (cls.get_namespace() in soaplib.const_prefmap):
                default_ns = cls.get_namespace()

        if cls.__namespace__ is None:
            cls.__namespace__ = cls.__module__

            if (cls.__namespace__.startswith("soaplib") or
                                               cls.__namespace__ == '__main__'):
                cls.__namespace__ = default_ns

        for k, v in cls._type_info.items():
            if v.__type_name__ is Base.Empty:
                v.__namespace__ = cls.get_namespace()
                v.__type_name__ = "%s_%sType" % (cls.get_type_name(), k)

            v.resolve_namespace(cls.get_namespace())

    @classmethod
    def add_to_schema(cls, schema_entries):
        if not schema_entries.has_class(cls):
            if not (getattr(cls, '__extends__', None) is None):
                cls.__extends__.add_to_schema(schema_entries)

            complex_type = etree.Element("{%s}complexType" % soaplib.ns_xsd)
            complex_type.set('name',cls.get_type_name())

            sequence_parent = complex_type
            if not (getattr(cls, '__extends__', None) is None):
                cls.__extends__.add_to_schema(schema_entries)

                complex_content = etree.SubElement(complex_type,
                                          "{%s}complexContent" % soaplib.ns_xsd)
                extension = etree.SubElement(complex_content, "{%s}extension"
                                                               % soaplib.ns_xsd)
                extension.set('base', cls.__extends__.get_type_name_ns())
                sequence_parent = extension

            sequence = etree.SubElement(sequence_parent, '{%s}sequence' %
                                                                soaplib.ns_xsd)

            for k, v in cls._type_info.items():
                v.add_to_schema(schema_entries)

                member = etree.SubElement(sequence, '{%s}element' %
                                                                soaplib.ns_xsd)
                member.set('name', k)

                if v.Attributes.min_occurs != 1: # 1 is the default
                    member.set('minOccurs', str(v.Attributes.min_occurs))
                if v.Attributes.max_occurs != 1: # 1 is the default
                    member.set('maxOccurs', str(v.Attributes.max_occurs))

                member.set('type', v.get_type_name_ns())
                if bool(v.Attributes.nillable) == True:
                    member.set('nillable', 'true')
                else:
                    member.set('nillable', 'false')

            schema_entries.add_complex_type(cls, complex_type)

            # simple node
            element = etree.Element('{%s}element' % soaplib.ns_xsd)
            element.set('name',cls.get_type_name())
            element.set('type',cls.get_type_name_ns())

            schema_entries.add_element(cls, element)

    @staticmethod
    def produce(namespace, type_name, members):
        """
        Lets you create a class programmatically.
        """

        cls_dict = {}

        cls_dict['__namespace__'] = namespace
        cls_dict['__type_name__'] = type_name
        cls_dict['_type_info'] = TypeInfo(members)

        return ClassSerializerMeta(type_name, (ClassSerializer,), cls_dict)

class ClassSerializer(ClassSerializerBase):
    """
    The general complexType factory. The __call__ method of this class will
    return instances, contrary to primivites where the same call will result in
    customized duplicates of the original class definition.
    Those who'd like to customize the class should use the customize method.
    (see soaplib.serializers.base.Base)
    """

    __metaclass__ = ClassSerializerMeta
