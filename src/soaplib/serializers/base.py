
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

class Base(object):
    __namespace__ = None
    __type_name__ = None

    @classmethod
    def get_namespace_prefix(cls):
        retval = cls.__namespace__
        
        if retval is None:
            retval = soaplib.prefmap['http://www.w3.org/2001/XMLSchema']
        else:
            retval = soaplib.get_namespace_prefix(cls.__namespace__)

        return retval

    @classmethod
    def set_namespace(cls, ns):
        cls.__namespace__ = ns

    @classmethod
    def get_type_name(cls):
        tn = cls.__type_name__
        if tn is None:
            tn = cls.__name__.lower()

        return tn

    @classmethod
    def get_type_name_ns(cls):
        return "%s:%s" % (cls.get_namespace_prefix(), cls.get_type_name())
    
    @nillable_value
    @classmethod
    def to_xml(cls, value, name='retval'):
        retval = etree.Element(name)
        retval.set('{%(xsi)s}type' % soaplib.nsmap, cls.type_name)

        if value:
            retval.text = value

        return retval

    @classmethod
    def from_xml(cls, element):
        raise Exception("Not Implemented")

    @classmethod
    def add_to_schema(cls, schema_dict):
        '''
        Nothing needs to happen when the type is a standard schema element
        '''
        pass

    @classmethod
    def customize(cls, **kwargs):
        """
        This class duplicates and customizes the class. The original class
        remains intact. It's a hack, advice to better write this function is
        welcome.

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

        for k,v in kwargs.items():
            cls_dict[k] = v

        cls_dup = type(cls.__name__, cls.__bases__, cls_dict)

        return cls_dup

class Null(Base):
    def to_xml(self, value, name='retval'):
        element = etree.Element(name)
        element.set('xs:nil', '1') # FIXME: hack!
        return element

    def from_xml(self, element):
        return None

class SchemaInfo(object):
    def __init__(self):
        self.simple = {}
        self.complex = {}
