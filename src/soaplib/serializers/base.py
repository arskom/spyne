
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

_ns_xs = soaplib.nsmap['xs']

def nillable_value(func):
    def wrapper(cls, value, tns, *args, **kwargs):
        if value is None:
            return Null.to_xml(value, tns, *args, **kwargs)
        return func(cls, value, tns, *args, **kwargs)
    return wrapper

def nillable_element(func):
    def wrapper(cls, element):
        if bool(element.get('{%s}nil' % soaplib.ns_xsi)): # or (element.text is None and len(element.getchildren()) == 0):
            return None
        return func(cls, element)
    return wrapper

def string_to_xml(cls, value, tns, name):
    assert isinstance(value, str) or isinstance(value, unicode), "'value' must " \
                    "be string or unicode. it is instead '%s'" % repr(value)

    retval = etree.Element("{%s}%s" % (tns,name))

    retval.set('{%s}type' % soaplib.ns_xsi, cls.get_type_name_ns())
    retval.text = value

    return retval

class Base(object):
    __namespace__ = None
    __type_name__ = None

    nillable = True
    min_occurs = 0
    max_occurs = 1

    class Empty(object):
        pass

    @classmethod
    def get_namespace_prefix(cls):
        ns = cls.get_namespace()

        assert ns != "__main__", cls
        assert ns != "soaplib.serializers.base", cls

        retval = soaplib.get_namespace_prefix(ns)

        return retval

    @classmethod
    def get_namespace(cls):
        retval = cls.__namespace__

        if retval is None:
            retval = cls.__module__

        return retval

    @classmethod
    def resolve_namespace(cls, default_ns):
        if cls.__namespace__ is None:
            cls.__namespace__ = cls.__module__

            if (cls.__namespace__.startswith("soaplib") or cls.__namespace__ == '__main__'):
                cls.__namespace__ = default_ns

    @classmethod
    def get_type_name(cls):
        retval = cls.__type_name__
        if retval is None:
            retval = cls.__name__.lower()

        return retval

    @classmethod
    def get_type_name_ns(cls):
        return "%s:%s" % (cls.get_namespace_prefix(), cls.get_type_name())

    @classmethod
    def to_xml(cls, value, tns, name='retval'):
        return string_to_xml(cls, value, tns, name)

    @classmethod
    def add_to_schema(cls, schema_entries):
        '''
        Nothing needs to happen when the type is a standard schema element
        '''
        pass
    
    @classmethod
    def customize(cls, **kwargs):
        """
        This function duplicates and customizes the class it belongs to. The
        original class remains intact.

        An example where this is useful:
            Array(String) normally creates an instance of Array class. This is
            inconsistent with the rest of the type definitions (e.g. String)
            being classes and not instances.

            Thanks to this function, one will get a new Array class instead,
            with its serializer set to String.
        """

        cls_dup = type(cls.__name__, (cls,), kwargs)

        return cls_dup

class Null(Base):
    @classmethod
    def to_xml(cls, value, tns, name='retval'):
        element = etree.Element("{%s}%s" % (tns,name))
        element.set('{%s}nil' % soaplib.ns_xsi, 'true')

        return element

    @classmethod
    def from_xml(cls, element):
        return None

class SimpleType(Base):
    __namespace__ = "http://www.w3.org/2001/XMLSchema"
    __base_type__ = None
    values = set()

    def __new__(cls, **kwargs):
        """
        Overriden so that any attempt to instantiate a primitive will return a
        customized class instead of an instance.

        See serializers.base.Base for more information.
        """

        retval = cls.customize(**kwargs)

        retval.values = kwargs.get("values", SimpleType.values)

        if not retval.is_default():
            retval.__base_type__ = cls.get_type_name_ns()
            retval.__type_name__ = kwargs.get("type_name", Base.Empty)

        return retval

    @classmethod
    def is_default(cls):
        return cls.values == SimpleType.values

    @classmethod
    def get_restriction_tag(cls, schema_entries):
        simple_type = etree.Element('{%s}simpleType' % _ns_xs)
        simple_type.set('name', cls.get_type_name())
        schema_entries.add_simple_type(cls, simple_type)

        restriction = etree.SubElement(simple_type, '{%s}restriction' % _ns_xs)
        restriction.set('base', cls.__base_type__)

        for v in cls.values:
            enumeration = etree.SubElement(restriction, '{%s}enumeration' % _ns_xs)
            enumeration.set('value', v)

        return restriction

    @classmethod
    def add_to_schema(cls, schema_entries):
        if not schema_entries.has_class(cls) and not cls.is_default():
            cls.get_restriction_tag(schema_entries)
