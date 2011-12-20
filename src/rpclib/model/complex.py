
#
# rpclib - Copyright (C) Rpclib contributors.
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

"""This module contains ComplexBase class and its helper objects that are
mainly container classes that organize other values.
"""

import logging
logger = logging.getLogger(__name__)

from rpclib.model import ModelBase
from rpclib.model import nillable_dict
from rpclib.model import nillable_string

from rpclib.util.odict import odict as TypeInfo
from rpclib.const import xml_ns as namespace


class _SimpleTypeInfoElement(object):
    __slots__ = ['path', 'parent', 'type']
    def __init__(self, path, parent, type_):
        self.path = path
        self.parent = parent
        self.type = type_


class XmlAttribute(ModelBase):
    """Items which are marshalled as attributes of the parent element."""

    def __init__(self, typ, use=None):
        self._typ = typ
        self._use = use

    def marshall(self, name, value, parent_elt):
        if value is not None:
            parent_elt.set(name, value)

    def describe(self, name, element):
        element.set('name', name)
        element.set('type', self._typ)
        if self._use:
            element.set('use', self._use)

class XmlAttributeRef(XmlAttribute):
    """Reference to stock XML attribute."""

    def __init__(self, ref, use=None):
        self._ref = ref
        self._use = use

    def describe(self, name, element):
        element.set('ref', self._ref)
        if self._use:
            element.set('use', self._use)

XMLAttribute = XmlAttribute
""" DEPRECATED! Use :class:`XmlAttribute` instead"""

XMLAttributeRef = XmlAttributeRef
""" DEPRECATED! Use :class:`XmlAttributeRef` instead"""

class SelfReference(object):
    pass

class ComplexModelMeta(type(ModelBase)):
    '''This is the metaclass that populates ComplexModel instances with the
    appropriate datatypes for (de)serialization.
    '''

    def __new__(cls, cls_name, cls_bases, cls_dict):
        '''This initializes the class, and registers attributes for
        serialization.
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
                        if len(base_types) > 0 and issubclass(b, ModelBase):
                            cls_dict["__extends__"] = extends = b
                    except:
                        logger.error(repr(extends))
                        raise

        # populate soap members
        if not ('_type_info' in cls_dict):
            cls_dict['_type_info'] = _type_info = TypeInfo()

            for k, v in cls_dict.items():
                if not k.startswith('__'):
                    attr = isinstance(v, XMLAttribute)
                    try:
                        subc = issubclass(v, ModelBase)
                    except:
                        subc = False

                    if subc:
                        _type_info[k] = v
                        if issubclass(v, Array) and v.serializer is None:
                            raise Exception("%s.%s is an array of what?" %
                                            (cls_name, k))
                    elif attr:
                        _type_info[k] = v

        else:
            _type_info = cls_dict['_type_info']
            if not isinstance(_type_info, TypeInfo):
                cls_dict['_type_info'] = TypeInfo(_type_info)

        return type(ModelBase).__new__(cls, cls_name, cls_bases, cls_dict)

    def __init__(self, cls_name, cls_bases, cls_dict):
        for k in cls_dict:
            if cls_dict[k] is SelfReference:
                cls_dict[k] = self
                self._type_info[k] = self

        type(ModelBase).__init__(self, cls_name, cls_bases, cls_dict)

class ComplexModelBase(ModelBase):
    """If you want to make a better class type, this is what you should inherit
    from.
    """

    def __init__(self, ** kwargs):
        super(ComplexModelBase, self).__init__()

        for k in self.get_flat_type_info(self.__class__).keys():
            setattr(self, k, kwargs.get(k, None))

    def __len__(self):
        return len(self._type_info)

    def __getitem__(self, i):
        return getattr(self, self._type_info.keys()[i], None)

    def __repr__(self):
        return "%s(%s)" % (self.get_type_name(), ', '.join(
                           ['%s=%r' % (k, getattr(self, k, None))
                                            for k in self.__class__._type_info]))

    @classmethod
    def get_serialization_instance(cls, value):
        """The value argument can be:
            * A list of native types aligned with cls._type_info.
            * A dict of native types
            * The native type itself.
        """
        # if the instance is a list, convert it to a cls instance.
        # this is only useful when deserializing method arguments for a client
        # request which is the only time when the member order is not arbitrary
        # (as the members are declared and passed around as sequences of
        # arguments, unlike dictionaries in a regular class definition).
        if isinstance(value, list) or isinstance(value, tuple):
            assert len(value) <= len(cls._type_info)

            inst = cls()

            keys = cls._type_info.keys()
            for i in range(len(value)):
                setattr(inst, keys[i], value[i])

        elif isinstance(value, dict):
            inst = cls()

            for k in cls._type_info:
                setattr(inst, k, value.get(k, None))

        else:
            inst = value

        return inst

    @classmethod
    def get_deserialization_instance(cls):
        """Get an empty native type so that the deserialization logic can set
        its attributes.
        """
        return cls()

    @classmethod
    def get_members_pairs(cls, inst):
        parent_cls = getattr(cls, '__extends__', None)
        if not (parent_cls is None):
            for r in parent_cls.get_members_pairs(inst, parent):
                yield r

        for k, v in cls._type_info.items():
            mo = v.Attributes.max_occurs
            subvalue = getattr(inst, k, None)

            if mo == 'unbounded' or mo > 1:
                if subvalue != None:
                    yield (k, [v.to_string(sv) for sv in subvalue])

            else:
                yield k, v.to_string(subvalue)

    @classmethod
    @nillable_dict
    def to_dict(cls, value):
        inst = cls.get_serialization_instance(value)

        return dict(cls.get_members_pairs(inst))

    @staticmethod
    def get_flat_type_info(cls, retval=None):
        """Returns a _type_info dict that includes members from all base classes.
        """

        if retval is None:
            retval = {}

        parent = getattr(cls, '__extends__', None)
        if parent != None:
            cls.get_flat_type_info(parent, retval)

        retval.update(cls._type_info)

        return retval

    @staticmethod
    def get_simple_type_info(cls, retval=None, prefix=None, parent=None):
        """Returns a _type_info dict that includes members from all base classes
        and whose types are only primitives.
        """
        from rpclib.model import SimpleModel
        from rpclib.model.binary import ByteArray

        if retval is None:
            retval = {}
        if prefix is None:
            prefix = []

        fti = cls.get_flat_type_info(cls)
        for k, v in fti.items():
            if getattr(v, 'get_flat_type_info', None) is None:
                new_prefix = list(prefix)
                new_prefix.append(k)
                key = '_'.join(new_prefix)
                value = retval.get(key, None)

                if value:
                    raise ValueError("%r.%s conflicts with %r" % (cls, k, value))

                else:
                    retval[key] = _SimpleTypeInfoElement(
                                        path=tuple(new_prefix), parent=parent, type_=v)

            else:
                new_prefix = list(prefix)
                new_prefix.append(k)
                v.get_simple_type_info(v, retval, new_prefix, parent=cls)

        return retval

    @classmethod
    @nillable_string
    def to_string(cls, value):
        raise Exception("Only primitives can be serialized to string.")

    @classmethod
    @nillable_string
    def from_string(cls, string):
        raise Exception("Only primitives can be deserialized from string.")

    @staticmethod
    def resolve_namespace(cls, default_ns):
        if getattr(cls, '__extends__', None) != None:
            cls.__extends__.resolve_namespace(cls.__extends__, default_ns)

        ModelBase.resolve_namespace(cls, default_ns)

        for k, v in cls._type_info.items():
            if v.__type_name__ is ModelBase.Empty:
                v.__namespace__ = cls.get_namespace()
                v.__type_name__ = "%s_%sType" % (cls.get_type_name(), k)

            if v != cls:
                v.resolve_namespace(v, default_ns)

    @staticmethod
    def produce(namespace, type_name, members):
        """Lets you create a class programmatically."""

        cls_dict = {}

        cls_dict['__namespace__'] = namespace
        cls_dict['__type_name__'] = type_name
        cls_dict['_type_info'] = TypeInfo(members)

        return ComplexModelMeta(type_name, (ComplexModel,), cls_dict)

    @staticmethod
    def alias(type_name, namespace, target):
        """Return an alias class for the given target class.

        This function is a variation on 'ComplexModel.produce'. The alias will
        borrow the target's _type_info.
        """

        cls_dict = {}

        cls_dict['__namespace__'] = namespace
        cls_dict['__type_name__'] = type_name
        cls_dict['_type_info'] = getattr(target, '_type_info', ())
        cls_dict['_target'] = target

        return ComplexModelMeta(type_name, (ClassAlias,), cls_dict)

class ComplexModel(ComplexModelBase):
    """The general complexType factory. The __call__ method of this class will
    return instances, contrary to primivites where the same call will result in
    customized duplicates of the original class definition.
    Those who'd like to customize the class should use the customize method.
    (see rpclib.model.base.ModelBase).
    """

    __metaclass__ = ComplexModelMeta

class Array(ComplexModel):
    """This class generates a ComplexModel child that has one attribute that has
    the same name as the serialized class. It's contained in a Python list.
    """

    def __new__(cls, serializer, ** kwargs):
        retval = cls.customize(**kwargs)

        # hack to default to unbounded arrays when the user didn't specify
        # max_occurs. We should find a better way.
        if serializer.Attributes.max_occurs == 1:
            serializer = serializer.customize(max_occurs='unbounded')

        if serializer.get_type_name() is ModelBase.Empty:
            member_name = serializer.__base_type__.get_type_name()
            if cls.__type_name__ is None:
                cls.__type_name__ = ModelBase.Empty # to be resolved later

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

        if cls.__namespace__ in namespace.const_prefmap:
            cls.__namespace__ = default_ns

        ComplexModel.resolve_namespace(cls, default_ns)

    @classmethod
    def get_serialization_instance(cls, value):
        inst = ComplexModel.__new__(Array)

        (member_name,) = cls._type_info.keys()
        setattr(inst, member_name, value)

        return inst

    @classmethod
    def get_deserialization_instance(cls):
        return []


class Iterable(Array):
    """This class generates a ComplexModel child that has one attribute that has
    the same name as the serialized class. It's contained in a Python iterable.
    """

class Alias(ComplexModel):
    """Different type_name, same _type_info."""

class SimpleContent(ModelBase):
    """THIS DOES NOT WORK!

    Implementation of a limited version on SimpleContent ComplexType.
    Actually, it can only do the extension part (no restriction of simpleType)
    """
    # Use ClassModelMeta to have _type_info
    __metaclass__ = ComplexModelMeta

    @classmethod
    def to_parent_element(cls, inst, tns, parent_elt, name=None):
        if name is None:
            name = cls.get_type_name()

        elt = etree.SubElement(parent_elt, "{%s}%s" % (tns, name))
        for k, v in cls._type_info.items():
            subval = getattr(inst, k, None)

            if isinstance(v, XMLAttribute):
                v.marshall(k, subval, elt)

        elt.text = str(inst.get_value())

    @classmethod
    def from_xml(cls, element):
        inst = cls()
        # reset attributes
        for k in cls._type_info.keys():
            setattr(inst, k, None)

        inst.set_value(element.text)
        for k in element.keys():
            setattr(inst, k, element.get(k, None))

        return inst

    @classmethod
    def add_to_schema(cls, schema_entries):
        if not schema_entries.has_class(cls):
            ns = namespaces.ns_xsd
            # extends should be a SimpleType
            extends = getattr(cls, '__extends__', None)
            if extends is None:
                raise Exception('SimpleContent must extend something')

            complex_type = etree.Element("{%s}complexType" % ns)
            complex_type.set('name', cls.get_type_name())
            simple_content = etree.SubElement(complex_type,
                                              "{%s}simpleContent" % ns)
            extention = etree.SubElement(simple_content, "{%s}extention" % ns)
            extention.set('base', extends.get_type_name_ns(schema_entries.app))

            for k, v in cls._type_info.items():
                if isinstance(v, XMLAttribute):
                    attr = etree.SubElement(extention, "{%s}attribute" % ns)
                    v.describe(k, attr)

            schema_entries.add_complex_type(cls, complex_type)

            element = etree.Element('{%s}element' % ns)
            element.set('name', cls.get_type_name())
            element.set('type', cls.get_type_name_ns(schema_entries.app))

            schema_entries.add_element(cls, element)

    @staticmethod
    def resolve_namespace(cls, default_ns):
        pass

    def get_value(self):
        return self._value

    def set_value(self, value):
        self._value = value
