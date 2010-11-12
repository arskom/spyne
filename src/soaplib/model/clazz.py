
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

from soaplib.model import Base
from soaplib.model import nillable_element
from soaplib.model import nillable_value

from soaplib.util.odict import odict as TypeInfo

class ClassSerializerMeta(type(Base)):
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

        if extends is None:
            for b in cls_bases:
                base_types = getattr(b, "_type_info", None)

                if not (base_types is None):
                    if not (extends is None or cls_dict["__extends__"] is b):
                        raise Exception("WSDL 1.1 does not support multiple "
                                        "inheritance")

                    try:
                        if len(base_types) > 0 and issubclass(b, Base):
                            cls_dict["__extends__"] = extends = b
                    except:
                        logger.error(repr(extends))
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

class ClassSerializerBase(Base):
    """
    If you want to make a better class type, this is what you should
    inherit from
    """

    def __init__(self, **kwargs):
        super(ClassSerializerBase,self).__init__()

        self.__reset_members(self.__class__, kwargs)

    def __reset_members(self, cls, kwargs):
        extends = getattr(cls, "__extends__", None)
        if not (extends is None):
            self.__reset_members(extends, kwargs)

        for k in cls._type_info.keys():
            setattr(self, k, kwargs.get(k, None))

    def __len__(self):
        return len(self._type_info)

    def __getitem__(self,i):
        return getattr(self, self._type_info.keys()[i], None)

    @classmethod
    def get_serialization_instance(cls, value):
        # if the instance is a list, convert it to a cls instance.
        # this is only useful when deserializing descriptor.in_message as it's
        # the only time when the member order is not arbitrary (as the members
        # are declared and passed around as sequences of arguments, unlike
        # dictionaries in a regular class definition).
        if isinstance(value, list) or isinstance(value, tuple):
            assert len(value) <= len(cls._type_info)

            inst = cls()

            keys = cls._type_info.keys()
            for i in range(len(value)):
                setattr(inst, keys[i], value[i])

        elif isinstance(value, dict):
            inst = cls()

            for k in cls._type_info:
                setattr(inst, k, value.get(k,None))

        else:
            inst = value

        return inst

    @classmethod
    def get_deserialization_instance(cls):
        return cls()

    @classmethod
    def get_members(cls, inst, parent):
        parent_cls = getattr(cls, '__extends__', None)
        if not (parent_cls is None):
            parent_cls.get_members(inst, parent)

        for k, v in cls._type_info.items():
            mo = v.Attributes.max_occurs
            subvalue = getattr(inst, k, None)

            if mo == 'unbounded' or mo > 1:
                if subvalue != None:
                    for sv in subvalue:
                        v.to_xml(sv, cls.get_namespace(), parent, k)

            else:
                v.to_xml(subvalue, cls.get_namespace(), parent, k)

    @classmethod
    @nillable_value
    def to_xml(cls, value, tns, parent_elt, name=None):
        if name is None:
            name = cls.get_type_name()

        element = etree.SubElement(parent_elt, "{%s}%s" % (tns, name))

        inst = cls.get_serialization_instance(value)

        cls.get_members(inst, element)

    @staticmethod
    def get_flat_type_info(clz, retval={}):
        parent = getattr(clz, '__extends__', None)
        if parent != None:
            get_flat_type_info(parent, retval)

        retval.update(clz._type_info)

        return retval

    @classmethod
    @nillable_element
    def from_xml(cls, element):
        inst = cls.get_deserialization_instance()

        # FIXME: the result of this method should be cached when build_wsdl is
        #        called (thus _type_info becomes immutable, by definition).
        flat_type_info = ClassSerializerBase.get_flat_type_info(cls)

        # initialize instance
        for k in flat_type_info:
            setattr(inst, k, None)

        # parse input to set incoming data to related attributes.
        for c in element:
            if isinstance(c, etree._Comment):
                continue

            key = c.tag.split('}')[-1]

            member = flat_type_info.get(key, None)
            if member is None:
                continue

            mo = member.Attributes.max_occurs
            if mo == 'unbounded' or mo > 1:
                value = getattr(inst, key, None)
                if value is None:
                    value = []

                value.append(member.from_xml(c))
                setattr(inst, key, value)

            else:
                setattr(inst, key, member.from_xml(c))

        return inst

    @staticmethod
    def resolve_namespace(cls, default_ns):
        if getattr(cls, '__extends__', None) != None:
            cls.__extends__.resolve_namespace(cls.__extends__, default_ns)

        Base.resolve_namespace(cls, default_ns)

        for k, v in cls._type_info.items():
            if v.__type_name__ is Base.Empty:
                v.__namespace__ = cls.get_namespace()
                v.__type_name__ = "%s_%sType" % (cls.get_type_name(), k)

            if v != cls:
                v.resolve_namespace(v, default_ns)

    @classmethod
    def add_to_schema(cls, schema_entries):
        if cls.get_type_name() is Base.Empty:
            (child,) = cls._type_info.values()
            cls.__type_name__ = '%sArray' % child.get_type_name()

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
                extension.set('base', cls.__extends__.get_type_name_ns(
                                                            schema_entries.app))
                sequence_parent = extension

            sequence = etree.SubElement(sequence_parent, '{%s}sequence' %
                                                                soaplib.ns_xsd)

            for k, v in cls._type_info.items():
                if v != cls:
                    v.add_to_schema(schema_entries)

                member = etree.SubElement(sequence, '{%s}element' %
                                                                soaplib.ns_xsd)
                member.set('name', k)
                member.set('type', v.get_type_name_ns(schema_entries.app))

                if v.Attributes.min_occurs != 1: # 1 is the xml schema default
                    member.set('minOccurs', str(v.Attributes.min_occurs))
                if v.Attributes.max_occurs != 1: # 1 is the xml schema default
                    member.set('maxOccurs', str(v.Attributes.max_occurs))

                # True is the xml schema default
                if bool(v.Attributes.nillable) == True:
                    member.set('nillable', 'true')

            schema_entries.add_complex_type(cls, complex_type)

            # simple node
            element = etree.Element('{%s}element' % soaplib.ns_xsd)
            element.set('name',cls.get_type_name())
            element.set('type',cls.get_type_name_ns(schema_entries.app))

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
    (see soaplib.model.base.Base)
    """

    __metaclass__ = ClassSerializerMeta

class Array(ClassSerializer):
    def __new__(cls, serializer, ** kwargs):
        retval = cls.customize(**kwargs)

        # hack to default to unbounded arrays when the user didn't specify
        # max_occurs. We should find a better way.
        if serializer.Attributes.max_occurs == 1:
            serializer = serializer.customize(max_occurs='unbounded')

        if serializer.get_type_name() is Base.Empty:
            member_name = serializer.__base_type__.get_type_name()
            if cls.__type_name__ is None:
                cls.__type_name__ = Base.Empty # to be resolved later

        else:
            member_name = serializer.get_type_name()
            if cls.__type_name__ is None:
                cls.__type_name__ = '%sArray' % serializer.get_type_name()

        retval.__type_name__ = '%sArray' % member_name
        retval._type_info = {member_name: serializer}

        return retval

    # the array belongs to its child's namespace, it doesn't have its own
    # namespace.
    @staticmethod
    def resolve_namespace(cls, default_ns):
        (serializer,) = cls._type_info.values()

        serializer.resolve_namespace(serializer, default_ns)

        if cls.__namespace__ is None:
            cls.__namespace__ = serializer.get_namespace()

        if cls.__namespace__ in soaplib.const_prefmap:
            cls.__namespace__ = default_ns

        ClassSerializer.resolve_namespace(cls, default_ns)

    @classmethod
    def get_serialization_instance(cls, value):
        inst = ClassSerializer.__new__(Array)

        (member_name,) = cls._type_info.keys()
        setattr(inst, member_name, value)

        return inst

    @classmethod
    @nillable_element
    def from_xml(cls, element):
        (serializer,) = cls._type_info.values()

        for child in element.getchildren():
            yield retval.append(serializer.from_xml(child))

from soaplib.model.exception import Fault