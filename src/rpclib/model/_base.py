
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
    #
    # please note that min_occurs and max_occurs must be validated in the
    # ComplexModelBase deserializer.
    class Attributes(object):
        """The class that holds the constraints for the given type."""

        default = None
        """The default value if the input is None"""

        nillable = True
        """Set this to false to reject null values."""

        min_occurs = 0
        """Set this to 0 to make the type mandatory. Can be set to any positive
        integer."""

        max_occurs = 1
        """Can be set to any strictly positive integer. Values greater than 1
        will imply an iterable of objects as native python type. Can be set to
        'unbounded' for arbitrary number of arguments."""

    class Annotations(object):
        """The class that holds the annotations for the given type."""

        doc = ""
        """The documentation for the given type."""

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
        """Duplicates cls and overwrites the values in ``cls.Attributes`` with
        ``**kwargs`` and returns the new class."""

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

    @staticmethod
    def validate_string(cls, value):
        """Override this method to do your own input validation on the input
        string. This is called before converting the incoming string to the
        native python value."""

        return (cls.Attributes.nillable or value is not None)

    @staticmethod
    def validate_native(cls, value):
        """Override this method to do your own input validation on the native
        value. This is called after converting the incoming string to the
        native python value."""
        return True

class Null(ModelBase):
    @classmethod
    def to_string(cls, value):
        return ""

    @classmethod
    def from_string(cls, value):
        return None

class SimpleModel(ModelBase):
    """The base class for primitives."""

    __namespace__ = "http://www.w3.org/2001/XMLSchema"
    __base_type__ = None

    class Attributes(ModelBase.Attributes):
        """The class that holds the constraints for the given type."""

        values = set()
        """The set of possible values for this type."""

    def __new__(cls, **kwargs):
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

    @staticmethod
    def validate_string(cls, value):
        return (    ModelBase.validate_string(cls, value)
                and (len(cls.Attributes.values) == 0 or
                                                value in cls.Attributes.values)
            )
