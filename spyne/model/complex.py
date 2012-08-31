
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

"""The ``spyne.model`` module contains :class:`spyne.model.complex.ComplexBase`
class and its helper objects and subclasses. These are mainly container classes.
"""

import decimal
import logging
logger = logging.getLogger(__name__)

from spyne.model import ModelBase
from spyne.model import nillable_dict
from spyne.model import nillable_string

from spyne.util.odict import odict
from spyne.const import xml_ns as namespace
from spyne.const.suffix import TYPE_SUFFIX

class TypeInfo(odict):
    pass

class _SimpleTypeInfoElement(object):
    __slots__ = ['path', 'parent', 'type']
    def __init__(self, path, parent, type_):
        self.path = path
        self.parent = parent
        self.type = type_


class XmlAttribute(ModelBase):
    """Items which are marshalled as attributes of the parent element."""
    def __new__(cls, typ, use=None, ns=None, attribute_of=None):
        retval = cls.customize()
        retval._typ = typ
        retval._use = use
        retval._ns = ns
        retval._attribute_of = attribute_of
        return retval

    @classmethod
    def marshall(cls, name, value, parent_elt):
        if cls._ns is not None:
            name = "{%s}%s" % (cls._ns,name)

        if value is not None:
            parent_elt.set(name, cls._typ.to_string(value))

    @classmethod
    def describe(cls, name, element, document):
        element.set('name', name)
        element.set('type', cls._typ.get_type_name_ns(document.interface))

        if cls._use is not None:
            element.set('use', cls._use)

    @staticmethod
    def resolve_namespace(cls, default_ns):
        cls._typ.resolve_namespace(cls._typ, default_ns)

        cls.__namespace__ = cls._ns

        if cls.__namespace__ is None:
            cls.__namespace__ = cls._typ.get_namespace()

        if cls.__namespace__ in namespace.const_prefmap:
            cls.__namespace__ = default_ns


class XmlAttributeRef(XmlAttribute):
    """Reference to an Xml attribute."""

    def __init__(self, ref, use=None):
        self._ref = ref
        self._use = use

    def describe(self, name, element, app):
        element.set('ref', self._ref)
        if self._use:
            element.set('use', self._use)


class SelfReference(object):
    '''Use this as a placeholder type in classes that contain themselves. See
    :func:`spyne.test.model.test_complex.TestComplexModel.test_self_reference`.
    '''

    def __init__(self):
        raise NotImplementedError()


class ComplexModelMeta(type(ModelBase)):
    '''This metaclass sets ``_type_info``, ``__type_name__`` and ``__extends__``
    which are going to be used for (de)serialization and schema generation.
    '''

    def __new__(cls, cls_name, cls_bases, cls_dict):
        '''This function initializes the class and registers attributes for
        serialization.
        '''

        type_name = cls_dict.get("__type_name__", None)
        if type_name is None:
            cls_dict["__type_name__"] = cls_name

        # get base class (if exists) and enforce single inheritance
        extends = cls_dict.get('__extends__', None)
        if extends is None:
            for b in cls_bases:
                base_types = getattr(b, "_type_info", None)

                if not (base_types is None):
                    if not (extends in (None, b)):
                        raise Exception("WSDL 1.1 does not support multiple "
                                        "inheritance")

                    try:
                        if len(base_types) > 0 and issubclass(b, ModelBase):
                            cls_dict["__extends__"] = b
                    except:
                        logger.error(repr(extends))
                        raise

        # populate children
        if not ('_type_info' in cls_dict):
            cls_dict['_type_info'] = _type_info = TypeInfo()

            for k, v in cls_dict.items():
                if not k.startswith('__'):
                    try:
                        subc = issubclass(v, ModelBase) or issubclass(v, SelfReference)
                    except:
                        subc = False

                    if subc:
                        _type_info[k] = v
                        if issubclass(v, Array) and len(v._type_info) != 1:
                            raise Exception("Invalid Array definition in %s.%s."
                                                                % (cls_name, k))
        else:
            _type_info = cls_dict['_type_info']

            if not isinstance(_type_info, TypeInfo):
                _type_info = cls_dict['_type_info'] = TypeInfo(_type_info)

            for k, v in _type_info.items():
                if issubclass(v, SelfReference):
                    pass

                elif not issubclass(v, ModelBase):
                    raise ValueError( (k,v) )

                elif issubclass(v, Array) and len(v._type_info) != 1:
                    raise Exception("Invalid Array definition in %s.%s."
                                                                % (cls_name, k))

        return type(ModelBase).__new__(cls, cls_name, cls_bases, cls_dict)

    def __init__(self, cls_name, cls_bases, cls_dict):
        type_info = cls_dict['_type_info']
        for k in type_info:
            if issubclass(type_info[k], SelfReference):
                type_info[k] = self

        type(ModelBase).__init__(self, cls_name, cls_bases, cls_dict)


class ComplexModelBase(ModelBase):
    """If you want to make a better class type, this is what you should inherit
    from.
    """

    def __init__(self, **kwargs):
        super(ComplexModelBase, self).__init__()

        # this ugliness is due to sqlalchemy's forcing of relevant types for
        # database fields
        for k in self.get_flat_type_info(self.__class__).keys():
            try:
                delattr(self, k)
            except:
                try:
                    setattr(self, k, None)
                except:
                    try:
                        setattr(self, k, [])
                    except:
                        pass

        for k,v in kwargs.items():
            setattr(self, k, v)

    def __len__(self):
        return len(self._type_info)

    def __getitem__(self, i):
        return getattr(self, self._type_info.keys()[i], None)

    def __repr__(self):
        return "%s(%s)" % (self.get_type_name(), ', '.join(
               ['%s=%r' % (k, getattr(self, k, None))
                    for k in self.__class__.get_flat_type_info(self.__class__)
                    if getattr(self, k, None) is not None]))

    @classmethod
    def get_serialization_instance(cls, value):
        """Returns the native object corresponding to the serialized form passed
        in the ``value`` argument.

        :param value: This argument can be:
            * A list or tuple of native types aligned with cls._type_info.
            * A dict of native types.
            * The native type itself.

            If the value type is not a ``list``, ``tuple`` or ``dict``, the
            value is returned untouched.
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
            for r in parent_cls.get_members_pairs(parent_cls, inst):
                yield r

        for k, v in cls._type_info.items():
            mo = v.Attributes.max_occurs
            try:
                subvalue = getattr(inst, k, None)
            except: # to guard against e.g. sqlalchemy throwing NoSuchColumnError
                subvalue = None

            if mo > 1:
                if subvalue != None:
                    yield (k, (v.to_string(sv) for sv in subvalue))

            else:
                yield (k, [v.to_string(subvalue)])

    @classmethod
    @nillable_dict
    def to_dict(cls, value):
        inst = cls.get_serialization_instance(value)

        return dict(cls.get_members_pairs(inst))

    @staticmethod
    def get_flat_type_info(cls, retval=None):
        """Returns a _type_info dict that includes members from all base classes.

        It's called a "flat" dict because it flattens all members from the
        inheritance hierarchy into one dict.
        """

        if retval is None:
            retval = TypeInfo()

        parent = getattr(cls, '__extends__', None)
        if parent != None:
            cls.get_flat_type_info(parent, retval)

        retval.update(cls._type_info)

        return retval

    @staticmethod
    def get_simple_type_info(cls, hier_delim="_", retval=None, prefix=None,
                                                                    parent=None):
        """Returns a _type_info dict that includes members from all base classes
        and whose types are only primitives. It will prefix field names in
        non-top-level complex objects with field name of its parent.

        For example, given hier_delim='_'; the following hierarchy:

            {'some_object': [{'some_string': ['abc']}]}

         would be transformed to:

            {'some_object_some_string': ['abc']}

        """

        if retval is None:
            retval = TypeInfo()
        if prefix is None:
            prefix = []

        fti = cls.get_flat_type_info(cls)
        for k, v in fti.items():
            if getattr(v, 'get_flat_type_info', None) is None:
                new_prefix = list(prefix)
                new_prefix.append(k)
                key = hier_delim.join(new_prefix)
                value = retval.get(key, None)

                if value:
                    raise ValueError("%r.%s conflicts with %r" % (cls, k, value))

                retval[key] = _SimpleTypeInfoElement(path=tuple(new_prefix),
                                                        parent=parent, type_=v)

            else:
                new_prefix = list(prefix)
                new_prefix.append(k)
                v.get_simple_type_info(v, hier_delim, retval, new_prefix, parent=cls)

        return retval

    @classmethod
    @nillable_string
    def to_string(cls, value):
        raise ValueError("Only primitives can be serialized to string.")

    @classmethod
    @nillable_string
    def from_string(cls, string):
        raise ValueError("Only primitives can be deserialized from string.")

    @staticmethod
    def resolve_namespace(cls, default_ns):
        if getattr(cls, '__extends__', None) != None:
            cls.__extends__.resolve_namespace(cls.__extends__, default_ns)

        ModelBase.resolve_namespace(cls, default_ns)

        for k, v in cls._type_info.items():
            if v.__type_name__ is ModelBase.Empty:
                v.__namespace__ = cls.get_namespace()
                v.__type_name__ = "%s_%s%s" % (cls.get_type_name(), k, TYPE_SUFFIX)

            if not issubclass(v, cls):
                v.resolve_namespace(v, default_ns)

        if cls._force_own_namespace is not None:
            for c in cls._force_own_namespace:
                c.__namespace__ = cls.get_namespace()
                ComplexModel.resolve_namespace(c, cls.get_namespace())

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
        cls_dict['_target'] = target

        ti = getattr(target, '_type_info', None)
        if ti is not None:
            cls_dict['_type_info'] = ti

        return ComplexModelMeta(type_name, (Alias,), cls_dict)

    @classmethod
    def customize(cls, **kwargs):
        """Duplicates cls and overwrites the values in ``cls.Attributes`` with
        ``**kwargs`` and returns the new class."""

        cls_name, cls_bases, cls_dict = cls._s_customize(cls, **kwargs)
        cls_dict['__module__'] = cls.__module__

        retval = type(cls_name, cls_bases, cls_dict)
        retval._type_info = cls._type_info
        retval.__type_name__ = cls.__type_name__
        retval.__namespace__ = cls.__namespace__

        e = getattr(retval, '__extends__', None)
        if e != None:
            retval.__extends__ = getattr(e, '__extends__', None)

        return retval


class ComplexModel(ComplexModelBase):
    """The general complexType factory. The __call__ method of this class will
    return instances, contrary to primivites where the same call will result in
    customized duplicates of the original class definition.
    Those who'd like to customize the class should use the customize method.
    (see spyne.model.base.ModelBase).
    """

    __metaclass__ = ComplexModelMeta

class Array(ComplexModel):
    """This class generates a ComplexModel child that has one attribute that has
    the same name as the serialized class. It's contained in a Python list.
    """

    def __new__(cls, serializer, **kwargs):
        retval = cls.customize(**kwargs)

        # hack to default to unbounded arrays when the user didn't specify
        # max_occurs. We should find a better way.
        if serializer.Attributes.max_occurs == 1:
            serializer = serializer.customize(max_occurs=decimal.Decimal('inf'))

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
    """This class generates a ``ComplexModel`` child that has one attribute that
    has the same name as the serialized class. It's contained in a Python
    iterable. The distinction with the ``Array`` is made in the protocol
    implementation, this is just a marker.
    """


class Alias(ComplexModel):
    """Different type_name, same _type_info."""
