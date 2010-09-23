
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

import soaplib

from lxml import etree

def nillable_value(func):
    def wrapper(cls, value, tns, parent_elt, *args, **kwargs):
        if value is None:
            Null.to_xml(value, tns, parent_elt, *args, **kwargs)
        else:
            func(cls, value, tns, parent_elt, *args, **kwargs)
    return wrapper

def nillable_element(func):
    def wrapper(cls, element):
        if bool(element.get('{%s}nil' % soaplib.ns_xsi)): # or (element.text is None and len(element.getchildren()) == 0):
            return None
        else:
            return func(cls, element)
    return wrapper

def string_to_xml(cls, value, tns, parent_elt, name):
    assert isinstance(value, str) or isinstance(value, unicode), "'value' must " \
                    "be string or unicode. it is instead '%s'" % repr(value)

    element = etree.SubElement(parent_elt, "{%s}%s" % (tns,name))

    element.set('{%s}type' % soaplib.ns_xsi, cls.get_type_name_ns())
    element.text = value

class Base(object):
    __namespace__ = None
    __type_name__ = None

    # There are not the xml schema defaults. The xml schema defaults are
    # considered in ClassSerializer's add_to_schema method. the defaults here
    # are to reflect what people want most.
    class Attributes(object):
        nillable = True
        min_occurs = 0
        max_occurs = 1

    class Empty(object):
        pass

    @staticmethod
    def is_default(cls):
        return True

    @classmethod
    def get_namespace_prefix(cls):
        ns = cls.get_namespace()

        retval = soaplib.get_namespace_prefix(ns)

        return retval

    @classmethod
    def get_namespace(cls):
        return cls.__namespace__

    @staticmethod
    def resolve_namespace(cls, default_ns):
        if cls.__namespace__ in soaplib.const_prefmap and not cls.is_default(cls):
            cls.__namespace__ = default_ns

        if cls.__namespace__ is None:
            cls.__namespace__ = cls.__module__

    @classmethod
    def get_type_name(cls):
        retval = cls.__type_name__
        if retval is None:
            retval = cls.__name__.lower()

        return retval

    @classmethod
    def get_type_name_ns(cls):
        if cls.get_namespace() != None:
            return "%s:%s" % (cls.get_namespace_prefix(), cls.get_type_name())

    @classmethod
    def to_xml(cls, value, tns, parent_elt, name='retval'):
        string_to_xml(cls, value, tns, parent_elt, name)

    @classmethod
    def add_to_schema(cls, schema_entries):
        '''
        Add this type to the wsdl.
        '''
        #Nothing needs to happen when the type is a standard schema element

    @classmethod
    def customize(cls, **kwargs):
        """
        This function duplicates and customizes the class it belongs to. The
        original class remains unchanged. This is an ugly hack. If you know
        better, let us know.
        """

        cls_dict = {}

        for k in cls.__dict__:
            if not (k in ("__dict__", "__weakref__")):
                cls_dict[k] = cls.__dict__[k]

        class Attributes(cls.Attributes):
            pass

        cls_dict['Attributes'] = Attributes

        if not ('_is_clone_of' in cls_dict):
            cls_dict['_is_clone_of'] = cls

        for k,v in kwargs.items():
            setattr(Attributes,k,v)

        cls_dup = type(cls.__name__, cls.__bases__, cls_dict)
        return cls_dup

class Null(Base):
    @classmethod
    def to_xml(cls, value, tns, parent_elt, name='retval'):
        element = etree.SubElement(parent_elt, "{%s}%s" % (tns,name))
        element.set('{%s}nil' % soaplib.ns_xsi, 'true')

    @classmethod
    def from_xml(cls, element):
        return None

class SimpleType(Base):
    __namespace__ = "http://www.w3.org/2001/XMLSchema"
    __base_type__ = None

    class Attributes(Base.Attributes):
        values = set()

    def __new__(cls, **kwargs):
        """
        Overriden so that any attempt to instantiate a primitive will return a
        customized class instead of an instance.

        See serializers.base.Base for more information.
        """

        retval = cls.customize(**kwargs)

        if not retval.is_default(retval):
            retval.__base_type__ = cls
            if retval.__type_name__ is None:
                retval.__type_name__ = kwargs.get("type_name", Base.Empty)

        return retval

    @staticmethod
    def is_default(cls):
        return (cls.Attributes.values == SimpleType.Attributes.values)

    @classmethod
    def get_restriction_tag(cls, schema_entries):
        simple_type = etree.Element('{%s}simpleType' % soaplib.ns_xsd)
        simple_type.set('name', cls.get_type_name())
        schema_entries.add_simple_type(cls, simple_type)

        restriction = etree.SubElement(simple_type,
                                            '{%s}restriction' % soaplib.ns_xsd)
        restriction.set('base', cls.__base_type__.get_type_name_ns())

        for v in cls.Attributes.values:
            enumeration = etree.SubElement(restriction,
                                            '{%s}enumeration' % soaplib.ns_xsd)
            enumeration.set('value', str(v))

        return restriction

    @classmethod
    def add_to_schema(cls, schema_entries):
        if not schema_entries.has_class(cls) and not cls.is_default(cls):
            cls.get_restriction_tag(schema_entries)
