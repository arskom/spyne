
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

import rpclib.const.xml_ns

"""This module contains the ModelBase class and other building blocks for
defining models.
"""

def nillable_dict(func):
    """Decorator that retuns empty dictionary if input is None"""

    def wrapper(cls, element):
        if element is None:
            return {}
        else:
            return func(cls, element)
    return wrapper

def nillable_string(func):
    """Decorator that retuns None if input is None."""

    def wrapper(cls, string):
        if string is None:
            return None
        else:
            return func(cls, string)
    return wrapper

def nillable_iterable(func):
    """Decorator that retuns [] if input is None."""

    def wrapper(cls, string):
        if string is None:
            return []
        else:
            return func(cls, string)
    return wrapper

class ModelBase(object):
    """The base class for type markers. It defines the model interface for the
    interface generators to use and also manages class customizations that are
    mainly used for defining constraints on input values.
    """

    __namespace__ = None
    __type_name__ = None

    # These are not the xml schema defaults. The xml schema defaults are
    # considered in ComplexModel's add_to_schema method. the defaults here
    # are to reflect what people seem to want most.
    class Attributes(object):
        nillable = True
        min_occurs = 0
        max_occurs = 1

    class Annotations(object):
        doc = ""

    class Empty(object):
        pass

    @staticmethod
    def is_default(cls):
        return True

    @classmethod
    def get_namespace_prefix(cls, interface):
        """Returns the namespace prefix for the given interface. The
        get_namespace_prefix of the interface class generates a prefix if none
        is defined.
        """

        ns = cls.get_namespace()

        retval = interface.get_namespace_prefix(ns)

        return retval

    @classmethod
    def get_namespace(cls):
        """Returns the namespace of the class. Defaults to the python module
        name."""

        return cls.__namespace__

    @staticmethod
    def resolve_namespace(cls, default_ns):
        """This call finalizes the namespace assignment. The default namespace
        is not available until the application calls populate_interface method
        of the interface generator.
        """

        if cls.__namespace__ is rpclib.const.xml_ns.DEFAULT_NS:
            cls.__namespace__ = default_ns

        if (cls.__namespace__ in rpclib.const.xml_ns.const_prefmap and
                                                       not cls.is_default(cls)):
            cls.__namespace__ = default_ns

        if cls.__namespace__ is None:
            cls.__namespace__ = cls.__module__

    @classmethod
    def get_type_name(cls):
        """Returns the class name unless the __type_name__ attribute is defined.
        """

        retval = cls.__type_name__
        if retval is None:
            retval = cls.__name__

        return retval

    @classmethod
    def get_type_name_ns(cls, app):
        """Returns the type name with a namespace prefix, separated by a column.
        """

        if cls.get_namespace() != None:
            return "%s:%s" % (cls.get_namespace_prefix(app), cls.get_type_name())

    @classmethod
    @nillable_string
    def to_string(cls, value):
        """Returns str(value). This should be overridden if this is not enough.
        """

        return str(value)

    @classmethod
    @nillable_iterable
    def to_string_iterable(cls, value):
        """Returns the result of :func:`to_string` in a list. This method should
        be overridden if this is not enough."""

        return [cls.to_string(value)]

    @classmethod
    @nillable_string
    def to_dict(cls, value):
        """Returns a dict with type name as key and str(value) as value. This
        should be overridden if this is not enough."""

        return {cls.get_type_name(): cls.to_string(value)}

    @classmethod
    def customize(cls, **kwargs):
        """Returns a duplicate of cls only with values in function arguments
        overwriting the ones in cls.Attributes."""

        cls_name, cls_bases, cls_dict = cls._s_customize(cls, **kwargs)

        return type(cls_name, cls_bases, cls_dict)

    @staticmethod
    def _s_customize(cls, ** kwargs):
        """This function duplicates and customizes the class it belongs to. The
        original class remains unchanged.

        Not meant to be overridden.
        """

        cls_dict = {}

        for k in cls.__dict__:
            if not (k in ("__dict__", "__weakref__")):
                cls_dict[k] = cls.__dict__[k]

        class Attributes(cls.Attributes):
            pass
        cls_dict['Attributes'] = Attributes

        class Annotations(cls.Annotations):
            pass
        cls_dict['Annotations'] = Annotations

        if not ('_is_clone_of' in cls_dict):
            cls_dict['_is_clone_of'] = cls

        for k, v in kwargs.items():
            if k != "doc":
                setattr(Attributes, k, v)
            else:
                setattr(Annotations, k, v)

        return (cls.__name__, cls.__bases__, cls_dict)

class Null(ModelBase):
    @classmethod
    def to_string(cls, value):
        return ""

    @classmethod
    def from_string(cls, value):
        return None

class SimpleModel(ModelBase):
    __namespace__ = "http://www.w3.org/2001/XMLSchema"
    __base_type__ = None

    class Attributes(ModelBase.Attributes):
        values = set()

    def __new__(cls, ** kwargs):
        """Overriden so that any attempt to instantiate a primitive will return
        a customized class instead of an instance.

        See rpclib.model.base.ModelBase for more information.
        """

        retval = cls.customize( ** kwargs)

        if not retval.is_default(retval):
            retval.__base_type__ = cls
            retval.__type_name__ = kwargs.get("type_name", ModelBase.Empty)

        return retval

    @staticmethod
    def is_default(cls):
        return (cls.Attributes.values == SimpleModel.Attributes.values)
