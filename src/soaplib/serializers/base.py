
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
    def wrapper(cls, value, *args, **kwargs):
        if value is None:
            return Null.to_xml(value, *args, **kwargs)
        return func(cls, value, *args, **kwargs)
    return wrapper

def nillable_element(func):
    def wrapper(cls, element, *args, **kwargs):
        if element.text is None:
            return None
        return func(cls, element, *args, **kwargs)
    return wrapper

def string_to_xml(cls, value, name):
    retval = etree.Element(name)

    retval.set('{%s}type' % soaplib.nsmap['xsi'], cls.get_type_name_ns())
    retval.text = value

    return retval

class Base(object):
    __namespace__ = None
    __type_name__ = None

    @classmethod
    def get_namespace_prefix(cls):
        retval = soaplib.get_namespace_prefix(cls.get_namespace())

        return retval

    @classmethod
    def get_namespace(cls):
        retval = cls.__namespace__

        if retval is None:
            retval = cls.__module__

        return retval

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
    def to_xml(cls, value, name='retval'):
        return string_to_xml(cls, value, name)

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
        original class remains intact. The implementation seems to be a hack,
        advice to better write this function is welcome.

        An example where this is useful:
            Array(String) normally creates an instance of Array class. This is
            inconsistent with the rest of the type definitions (e.g. String)
            being classes and not instances.

            Thanks to this function, one will get a new Array class instead,
            with its serializer set to String.
        """

        cls_dict = {}

        for k in cls.__dict__:
            if not (k in ("__dict__", "__module__", "__weakref__")):
                cls_dict[k] = cls.__dict__[k]

        cls_dict.update(kwargs)

        cls_dup = type(cls.__name__, cls.__bases__, cls_dict)

        return cls_dup

class Null(Base):
    @classmethod
    def to_xml(cls, value, name='retval'):
        element = etree.Element(name)
        element.set('{%s}nil' % _ns_xs, '1')
        return element

    @classmethod
    def from_xml(cls, element):
        return None
