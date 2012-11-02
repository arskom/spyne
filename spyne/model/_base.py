
#
# spyne - Copyright (C) Spyne contributors.
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

import re

import spyne.const.xml_ns

from decimal import Decimal

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


class AttributesMeta(type(object)):
    """I hate quirks. So this is a 10-minute attempt to get rid of a one-letter
    quirk."""

    def __init__(self, cls_name, cls_bases, cls_dict):
        nullable = cls_dict.get('nullable', None)
        nillable = cls_dict.get('nillable', None)

        assert nullable is None or nillable is None or nullable == nillable

        self.__nullable = nullable or nillable or True

        type(object).__init__(self, cls_name, cls_bases, cls_dict)

    def get_nullable(self):
        return self.__nullable
    def set_nullable(self, what):
        self.__nullable = what
    nullable = property(get_nullable, set_nullable)

    def get_nillable(self):
        return self.__nullable
    def set_nillable(self, what):
        self.__nullable = what
    nillable = property(get_nillable, set_nillable)


class ModelBase(object):
    """The base class for type markers. It defines the model interface for the
    interface generators to use and also manages class customizations that are
    mainly used for defining constraints on input values.
    """

    __orig__ = None
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
        __metaclass__ = AttributesMeta

        default = None
        """The default value if the input is None"""

        nillable = True
        """Set this to false to reject null values. Synonyms with
        ``nullable``."""

        min_occurs = 0
        """Set this to 1 to make this object mandatory. Can be set to any
        positive integer. Note that an object can still be null or empty, even
        if it's there."""

        max_occurs = 1
        """Can be set to any strictly positive integer. Values greater than 1
        will imply an iterable of objects as native python type. Can be set to
        ``decimal.Decimal("inf")`` for arbitrary number of arguments."""

        schema_tag = '{%s}element' % spyne.const.xml_ns.xsd
        """The tag used to add a primitives as child to a complex type in the
        xml schema."""

        translations = None
        """A dict that contains locale codes as keys and translations of field
        names to that language as values.
        """

        sqla_column_args = None
        """A dict that will be passed to SQLAlchemy's ``Column`` constructor as
        ``**kwargs``.
        """

        exc_mapper = False
        """If true, this field will be excluded from the table mapper of the
        parent class.
        """

        exc_table = False
        """If true, this field will be excluded from the table of the parent
        class.
        """

        exc_interface = False
        """If true, this field will be excluded from the interface document."""

        logged = True
        """If false, this object will be ignored in ``log_repr``, mostly used
        for logging purposes."""

    class Annotations(object):
        """The class that holds the annotations for the given type."""

        __use_parent_doc__ = False
        """If set to True Annotations will use __doc__ from parent,
        This is a convenience option"""

        doc = ""
        """The public documentation for the given type."""

        appinfo = None
        """Any object that carries app-specific info."""

    class Empty(object):
        pass

    _force_own_namespace = None

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

        if cls.__namespace__ is spyne.const.xml_ns.DEFAULT_NS:
            cls.__namespace__ = default_ns

        if (cls.__namespace__ in spyne.const.xml_ns.const_prefmap and
                                                       not cls.is_default(cls)):
            cls.__namespace__ = default_ns

        if cls.__namespace__ is None:
            ret = []
            for f in cls.__module__.split('.'):
                if f.startswith('_'):
                    break
                else:
                    ret.append(f)

            cls.__namespace__ = '.'.join(ret)

    @classmethod
    def get_type_name(cls):
        """Returns the class name unless the __type_name__ attribute is defined.
        """

        retval = cls.__type_name__
        if retval is None:
            retval = cls.__name__

        return retval

    @classmethod
    def get_type_name_ns(cls, interface):
        """Returns the type name with a namespace prefix, separated by a column.
        """

        if cls.get_namespace() != None:
            return "%s:%s" % (cls.get_namespace_prefix(interface), cls.get_type_name())

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
    @nillable_dict
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
    def _s_customize(cls, **kwargs):
        """This function duplicates and customizes the class it belongs to. The
        original class remains unchanged.

        Not meant to be overridden.
        """

        cls_dict = {}
        if getattr(cls, '__orig__', None) is None:
            cls_dict['__orig__'] = cls

        class Attributes(cls.Attributes):
            translations = {}
            sqla_column_args = (), {}
        cls_dict['Attributes'] = Attributes

        class Annotations(cls.Annotations):
            pass
        cls_dict['Annotations'] = Annotations

        for k, v in kwargs.items():
            if k.startswith('_'):
                continue

            elif k in ("doc", "appinfo"):
                setattr(Annotations, k, v)

            elif k in ('primary_key','pk'):
                Attributes.sqla_column_args[-1]['primary_key'] = v

            elif k in ('foreign_key','fk'):
                from sqlalchemy.schema import ForeignKey
                t, d = Attributes.sqla_column_args
                fkt = (ForeignKey(v),)
                Attributes.sqla_column_args = (t + fkt, d)

            elif k == 'max_occurs' and v == 'unbounded':
                setattr(Attributes, k, Decimal('inf'))

            else:
                setattr(Attributes, k, v)

        return (cls.__name__, (cls,), cls_dict)

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
    __base_type__ = None # this is different from __orig__ because it's only set
                         # when cls.is_default(cls) == False

    class Attributes(ModelBase.Attributes):
        """The class that holds the constraints for the given type."""

        class __metaclass__(AttributesMeta):
            def __init__(self, cls_name, cls_bases, cls_dict):
                AttributesMeta.__init__(self, cls_name, cls_bases, cls_dict)
                self.__pattern = None
            def get_pattern(self):
                return self.__pattern
            def set_pattern(self, pattern):
                self.__pattern = pattern
                if pattern is not None:
                    self._pattern_re = re.compile(pattern)
            pattern = property(get_pattern, set_pattern)

        values = set()
        """The set of possible values for this type."""

        _pattern_re = None

    def __new__(cls, **kwargs):
        """Overriden so that any attempt to instantiate a primitive will return
        a customized class instead of an instance.

        See spyne.model.base.ModelBase for more information.
        """

        retval = cls.customize(**kwargs)

        if not retval.is_default(retval):
            retval.__base_type__ = cls
            retval.__type_name__ = kwargs.get("type_name", ModelBase.Empty)

        return retval

    @staticmethod
    def is_default(cls):
        return (cls.Attributes.values == SimpleModel.Attributes.values)

    @staticmethod
    def validate_string(cls, value):
        return (     ModelBase.validate_string(cls, value)
                and (len(cls.Attributes.values) == 0 or
                                                value in cls.Attributes.values)
            )
