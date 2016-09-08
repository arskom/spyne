
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

"""The ``spyne.model.complex`` module contains
:class:`spyne.model.complex.ComplexBase` class and its helper objects and
subclasses. These are mainly container classes for other simple or
complex objects -- they don't carry any data by themselves.
"""

from __future__ import print_function

import logging
logger = logging.getLogger(__name__)

import decimal

from copy import copy
from weakref import WeakKeyDictionary
from collections import deque
from inspect import isclass
from itertools import chain

from spyne import BODY_STYLE_BARE, BODY_STYLE_WRAPPED, BODY_STYLE_EMPTY
from spyne import const
from spyne.const import xml_ns

from spyne.model import Point
from spyne.model import Unicode
from spyne.model import PushBase
from spyne.model import ModelBase
from spyne.model import json, xml, msgpack, table
from spyne.model._base import apply_pssm
from spyne.model.primitive import NATIVE_MAP

from spyne.util import six
from spyne.util import memoize
from spyne.util import memoize_id
from spyne.util import sanitize_args
from spyne.util.meta import Prepareable
from spyne.util.odict import odict
from spyne.util.six import add_metaclass, with_metaclass, string_types


PSSM_VALUES = {'json': json, 'xml': xml, 'msgpack': msgpack, 'table': table}


def _is_under_pydev_debugger():
    import inspect
    for frame in inspect.stack():
        if frame[1].endswith("pydevd.py"):
            return True
    return False


def _get_flat_type_info(cls, retval):
    assert isinstance(retval, TypeInfo)
    parent = getattr(cls, '__extends__', None)
    if parent != None:
        _get_flat_type_info(parent, retval)
    retval.update(cls._type_info)
    retval.alt.update(cls._type_info_alt) # FIXME: move to cls._type_info.alt
    return retval


class TypeInfo(odict):
    def __init__(self, *args, **kwargs):
        super(TypeInfo, self).__init__(*args, **kwargs)
        self.attributes = {}
        self.alt = {}

    def __setitem__(self, key, val):
        assert isinstance(key, string_types)
        super(TypeInfo, self).__setitem__(key, val)


class _SimpleTypeInfoElement(object):
    __slots__ = ['path', 'parent', 'type', 'is_array', 'can_be_empty']

    def __init__(self, path, parent, type_, is_array, can_be_empty):
        self.path = path
        self.parent = parent
        self.type = type_
        self.is_array = is_array
        self.can_be_empty = can_be_empty

    def __repr__(self):
        return "SimpleTypeInfoElement(path=%r, parent=%r, type=%r, is_array=%r)" \
                            % (self.path, self.parent, self.type, self.is_array)


class XmlModifier(ModelBase):
    def __new__(cls, type, ns=None):
        retval = cls.customize()
        retval.type = type
        retval.Attributes = type.Attributes
        retval._ns = ns
        if type.__type_name__ is ModelBase.Empty:
            retval.__type_name__ = ModelBase.Empty
        return retval

    @staticmethod
    def resolve_namespace(cls, default_ns, tags=None):
        cls.type.resolve_namespace(cls.type, default_ns, tags)

        cls.__namespace__ = cls._ns

        if cls.__namespace__ is None:
            cls.__namespace__ = cls.type.get_namespace()

        if cls.__namespace__ in xml_ns.const_prefmap:
            cls.__namespace__ = default_ns

    @classmethod
    def _fill_empty_type_name(cls, parent_ns, parent_tn, k):
        cls.__namespace__ = parent_ns
        tn = "%s_%s%s" % (parent_tn, k, const.TYPE_SUFFIX)

        child_v = cls.type
        child_v.__type_name__ = tn

        cls._type_info = TypeInfo({tn: child_v})
        cls.__type_name__ = '%s%s%s' % (const.ARRAY_PREFIX, tn,
                                                         const.ARRAY_SUFFIX)

        extends = child_v.__extends__
        while extends is not None and extends.get_type_name() is cls.Empty:
            extends._fill_empty_type_name(parent_ns, parent_tn,
                                                    k + const.PARENT_SUFFIX)
            extends = extends.__extends__


class XmlData(XmlModifier):
    """Items which are marshalled as data of the parent element."""

    @classmethod
    def marshall(cls, prot, name, value, parent_elt):
        if value is not None:
            if len(parent_elt) == 0:
                parent_elt.text = prot.to_string(cls.type, value)
            else:
                parent_elt[-1].tail = prot.to_string(cls.type, value)

    @classmethod
    def get_type_name(cls):
        return cls.type.get_type_name()

    @classmethod
    def get_type_name_ns(cls, interface):
        return cls.type.get_type_name_ns(interface)

    @classmethod
    def get_namespace(cls):
        return cls.type.get_namespace()

    @classmethod
    def get_element_name(cls):
        return cls.type.get_element_name()

    @classmethod
    def get_element_name_ns(cls, interface):
        return cls.type.get_element_name_ns(interface)


class XmlAttribute(XmlModifier):
    """Items which are marshalled as attributes of the parent element. If
    ``attribute_of`` is passed, it's marshalled as the attribute of the element
    with given name.
    """

    def __new__(cls, type_, use=None, ns=None, attribute_of=None):
        retval = super(XmlAttribute, cls).__new__(cls, type_, ns)
        retval._use = use
        if retval.type.Attributes.min_occurs > 0 and retval._use is None:
            retval._use = 'required'
        retval.attribute_of = attribute_of
        return retval


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
    """Use this as a placeholder type in classes that contain themselves. See
    :func:`spyne.test.model.test_complex.TestComplexModel.test_self_reference`.
    """
    customize_args = []
    customize_kwargs = {}
    __orig__ = None

    def __init__(self):
        raise NotImplementedError()

    @classmethod
    def customize(cls, *args, **kwargs):
        args = chain(args, cls.customize_args)
        kwargs = dict(chain(kwargs.items(), cls.customize_kwargs.items()))
        if cls.__orig__ is None:
            cls.__orig__ = cls

        return type("SelfReference", (cls,), {
            'customize_args': args,
            'customize_kwargs': kwargs,
        })


def _get_spyne_type(cls_name, k, v):
    try:
        v = NATIVE_MAP.get(v, v)
    except TypeError:
        return

    try:
        subc = issubclass(v, ModelBase) or issubclass(v, SelfReference)
    except:
        subc = False

    if subc:
        if issubclass(v, Array) and len(v._type_info) != 1:
            raise Exception("Invalid Array definition in %s.%s."% (cls_name, k))
        elif issubclass(v, Point) and v.Attributes.dim is None:
            raise Exception("Please specify the number of dimensions")
        return v


def _join_args(x, y):
    if x is None:
        return y
    if y is None:
        return x

    xa, xk = sanitize_args(x)
    ya, yk = sanitize_args(y)

    xk = dict(xk)
    xk.update(yk)

    return xa + ya, xk


def _gen_attrs(cls_bases, cls_dict):
    attrs = cls_dict.get('Attributes', None)
    if attrs is None:
        for b in cls_bases:
            if hasattr(b, 'Attributes'):
                class Attributes(b.Attributes):
                    pass
                attrs = cls_dict['Attributes'] = Attributes
                break
        else:
            raise Exception("No ModelBase subclass in bases? Huh?")

    return attrs


def _get_type_info(cls, cls_name, cls_bases, cls_dict, attrs):
    base_type_info = TypeInfo()
    mixin = TypeInfo()
    extends = cls_dict.get('__extends__', None)

    # user did not specify explicit base class so let's try to derive it from
    # the actual class hierarchy
    if extends is None:
        # we don't want origs end up as base classes
        orig = cls_dict.get("__orig__", None)
        if orig is None:
            orig = getattr(cls, '__orig__', None)

        if orig is not None:
            bases = orig.__bases__
            logger.debug("Got bases for %s from orig: %r", cls_name, bases)
        else:
            bases = cls_bases
            logger.debug("Got bases for %s from meta: %r", cls_name, bases)

        for b in bases:
            base_types = getattr(b, "_type_info", None)

            # we don't care about non-ComplexModel bases
            if base_types is None:
                continue

            # mixins are simple
            if getattr(b, '__mixin__', False) == True:
                logger.debug("Adding fields from mixin %r to '%s'", b, cls_name)
                mixin.update(b.get_flat_type_info(b))

                if '__mixin__' not in cls_dict:
                    cls_dict['__mixin__'] = False

                continue

            if not (extends in (None, b)):
                raise Exception("Spyne objects do not support multiple "
                    "inheritance. Use mixins if you need to reuse "
                    "fields from multiple classes.")

            if len(base_types) > 0 and issubclass(b, ModelBase):
                extends = cls_dict["__extends__"] = b
                assert extends.__orig__ is None, "You can't inherit from a " \
                    "customized class. You should first get your class " \
                    "hierarchy right, then start customizing classes."

                b.get_subclasses.memo.clear()
                logger.debug("Registering %r as base of '%s'", b, cls_name)

    if not ('_type_info' in cls_dict):
        cls_dict['_type_info'] = _type_info = TypeInfo()
        _type_info.update(base_type_info)

        class_fields = []
        for k, v in cls_dict.items():
            if not k.startswith('_'):
                v = _get_spyne_type(cls_name, k, v)
                if v is not None:
                    class_fields.append((k, v))

        _type_info.update(class_fields)

    else:
        _type_info = cls_dict['_type_info']

        if not isinstance(_type_info, TypeInfo):
            _type_info = cls_dict['_type_info'] = TypeInfo(_type_info)

    _type_info.update(mixin)

    return _type_info


class _MethodsDict(dict):
    def __init__(self, *args, **kwargs):
        super(_MethodsDict, self).__init__(*args, **kwargs)

        self._processed = False

    def sanitize(self, cls):
        # sanitize is called on every customization, so we make sure it's run
        # only once in this class' lifetime.
        if self._processed:
            return

        self._processed = True

        for d in self.values():
            d.parent_class = cls

            if d.in_message_name_override:
                d.in_message.__type_name__ = '%s.%s' % \
                          (cls.get_type_name(), d.in_message.get_type_name())

            if d.body_style is BODY_STYLE_WRAPPED or d.out_message_name_override:
                d.out_message.__type_name__ = '%s.%s' % \
                          (cls.get_type_name(), d.out_message.get_type_name())

            if d.body_style in (BODY_STYLE_BARE, BODY_STYLE_EMPTY):
                # The method only needs the primary key(s) and shouldn't
                # complain when other mandatory fields are missing.
                d.in_message = cls.novalidate_freq()
                d.body_style = BODY_STYLE_BARE

            else:
                d.in_message.insert_field(0, 'self', cls.novalidate_freq())
                d.body_style = BODY_STYLE_WRAPPED

                if issubclass(d.in_message, ComplexModelBase):
                    for k, v in d.in_message._type_info.items():
                        # SelfReference is replaced by descriptor.in_message
                        # itself. However, in the context of mrpc, SelfReference
                        # means parent class. here, we do that substitution.
                        # It's a safe hack but a hack nevertheless.
                        if v is d.in_message:
                            d.in_message._type_info[k] = cls

            # Same as above, for the output type.
            if issubclass(d.out_message, ComplexModelBase):
                for k, v in d.out_message._type_info.items():
                    if v is d.out_message:
                        d.out_message._type_info[k] = cls

            if d.patterns is not None and not d.no_self:
                d.name = '.'.join((cls.get_type_name(), d.name))
                for p in d.patterns:
                    if p.address is None:
                        p.address = d.name


def _gen_methods(cls, cls_dict):
    methods = _MethodsDict()
    for k, v in cls_dict.items():
        if not k.startswith('_') and hasattr(v, '_is_rpc'):
            descriptor = v(_default_function_name=k, _self_ref_replacement=cls)
            setattr(cls, k, descriptor.function)
            methods[k] = descriptor

    return methods


def _get_ordered_attributes(cls_name, cls_dict, attrs):
    if not isinstance(cls_dict, odict):
        # FIXME: Maybe add a warning here?
        return cls_dict

    SUPPORTED_ORDERS = ('random', 'declared')
    if (attrs.declare_order is not None and
            not attrs.declare_order in SUPPORTED_ORDERS):

        msg = "The declare_order attribute value %r is invalid in %s"
        raise Exception(msg % (attrs.declare_order, cls_name))

    declare_order = attrs.declare_order or const.DEFAULT_DECLARE_ORDER
    if declare_order is None or declare_order == 'random':
        # support old behaviour
        cls_dict = dict(cls_dict)

    return cls_dict


def _sanitize_sqlalchemy_parameters(cls_dict, attrs):
    table_name = cls_dict.get('__tablename__', None)
    if attrs.table_name is None:
        attrs.table_name = table_name

    _cls_table = cls_dict.get('__table__', None)
    if attrs.sqla_table is None:
        attrs.sqla_table = _cls_table

    metadata = cls_dict.get('__metadata__', None)
    if attrs.sqla_metadata is None:
        attrs.sqla_metadata = metadata

    margs = cls_dict.get('__mapper_args__', None)
    attrs.sqla_mapper_args = _join_args(attrs.sqla_mapper_args, margs)

    targs = cls_dict.get('__table_args__', None)
    attrs.sqla_table_args = _join_args(attrs.sqla_table_args, targs)


def _sanitize_type_info(cls_name, _type_info, _type_info_alt):
    # make sure _type_info contents are sane
    for k, v in _type_info.items():
        if not isinstance(k, six.string_types):
            raise ValueError("Invalid class key", k)
        if not isclass(v):
            raise ValueError(v)

        if issubclass(v, SelfReference):
            continue

        elif not issubclass(v, ModelBase):
            v = _get_spyne_type(cls_name, k, v)
            if v is None:
                raise ValueError( (cls_name, k, v) )
            _type_info[k] = v

        elif issubclass(v, Array) and len(v._type_info) != 1:
            raise Exception("Invalid Array definition in %s.%s." %
                                                        (cls_name, k))
        sub_ns = v.Attributes.sub_ns
        sub_name = v.Attributes.sub_name

        if sub_ns is None and sub_name is None:
            pass

        elif sub_ns is not None and sub_name is not None:
            key = "{%s}%s" % (sub_ns, sub_name)
            if key in _type_info:
                raise Exception("%r is already defined: %r" %
                                                         (key, _type_info[key]))
            _type_info_alt[key] = v, k

        elif sub_ns is None:
            key = sub_name
            if sub_ns in _type_info:
                raise Exception("%r is already defined: %r" %
                                                        (key, _type_info[key]))
            _type_info_alt[key] = v, k

        elif sub_name is None:
            key = "{%s}%s" % (sub_ns, k)
            if key in _type_info:
                raise Exception("%r is already defined: %r" %
                                                        (key, _type_info[key]))
            _type_info_alt[key] = v, k


def _process_child_attrs(cls, retval, kwargs):
    child_attrs_all = kwargs.get('child_attrs_all', None)
    if child_attrs_all is not None:
        ti = retval._type_info
        logger.debug("processing child_attrs_all for %r", cls)
        for k, v in ti.items():
            logger.debug("  child_attrs_all set %r=%r", k, child_attrs_all)
            ti[k] = ti[k].customize(**child_attrs_all)

        if retval.__extends__ is not None:
            retval.__extends__ = retval.__extends__.customize(
                                            child_attrs_all=child_attrs_all)

        retval.Attributes._delayed_child_attrs_all = child_attrs_all

    child_attrs = copy(kwargs.get('child_attrs', None))
    if child_attrs is not None:
        ti = retval._type_info
        logger.debug("processing child_attrs for %r", cls)
        for k, v in list(child_attrs.items()):
            if k in ti:
                logger.debug("  child_attr set %r=%r", k, v)
                ti[k] = ti[k].customize(**v)
                del child_attrs[k]

        base_fti = {}
        if retval.__extends__ is not None:
            retval.__extends__ = retval.__extends__.customize(
                                                    child_attrs=child_attrs)
            base_fti = retval.__extends__.get_flat_type_info(
                                                         retval.__extends__)
        for k, v in child_attrs.items():
            if k not in base_fti:
                logger.debug("  child_attr delayed %r=%r", k, v)
                retval.Attributes._delayed_child_attrs[k] = v


class ComplexModelMeta(with_metaclass(Prepareable, type(ModelBase))):
    """This metaclass sets ``_type_info``, ``__type_name__`` and ``__extends__``
    which are going to be used for (de)serialization and schema generation.
    """

    def __new__(cls, cls_name, cls_bases, cls_dict):
        """This function initializes the class and registers attributes."""

        attrs = _gen_attrs(cls_bases, cls_dict)
        assert issubclass(attrs, ComplexModelBase.Attributes), \
                   ("%r must be a ComplexModelBase.Attributes subclass" % attrs)

        cls_dict = _get_ordered_attributes(cls_name, cls_dict, attrs)

        type_name = cls_dict.get("__type_name__", None)
        if type_name is None:
            cls_dict["__type_name__"] = cls_name

        _type_info = _get_type_info(cls, cls_name, cls_bases, cls_dict, attrs)

        # used for sub_name and sub_ns
        _type_info_alt = cls_dict['_type_info_alt'] = TypeInfo()
        for b in cls_bases:
            if hasattr(b, '_type_info_alt'):
                _type_info_alt.update(b._type_info_alt)

        _sanitize_type_info(cls_name, _type_info, _type_info_alt)
        _sanitize_sqlalchemy_parameters(cls_dict, attrs)

        return super(ComplexModelMeta, cls).__new__(cls, cls_name, cls_bases,
                                                    cls_dict)

    def __init__(self, cls_name, cls_bases, cls_dict):
        type_info = self._type_info

        extends = self.__extends__
        if extends is not None and self.__orig__ is None:
            eattr = extends.Attributes;
            if eattr._subclasses is None:
                eattr._subclasses = []
            eattr._subclasses.append(self)
            if self.Attributes._subclasses is eattr._subclasses:
                self.Attributes._subclasses = None

        for k, v in type_info.items():
            if issubclass(v, SelfReference):
                self._replace_field(k, self.customize(*v.customize_args,
                                                          **v.customize_kwargs))

            elif issubclass(v, XmlData):
                if self.Attributes._xml_tag_body_as is None:
                    self.Attributes._xml_tag_body_as = [(k, v)]
                else:
                    self.Attributes._xml_tag_body_as.append((k, v))

            elif issubclass(v, XmlAttribute):
                a_of = v.attribute_of
                if a_of is not None:
                    type_info.attributes[k] = type_info[a_of]

            elif issubclass(v, Array):
                v2, = v._type_info.values()
                while issubclass(v2, Array):
                    v = v2
                    v2, = v2._type_info.values()

                if issubclass(v2, SelfReference):
                    v._set_serializer(self)

        # FIXME: Implement this better
        new_type_info = []
        for k, v in self._type_info.items():
            if v.Attributes.order == None:
                new_type_info.append(k)

        for k, v in self._type_info.items():
            if v.Attributes.order is not None:
                new_type_info.insert(v.Attributes.order, k)

        assert len(self._type_info) == len(new_type_info)
        self._type_info.keys()[:] = new_type_info

        tn = self.Attributes.table_name
        meta = self.Attributes.sqla_metadata
        t = self.Attributes.sqla_table

        methods = _gen_methods(self, cls_dict)
        if len(methods) > 0:
            self.Attributes.methods = methods

        methods = self.Attributes.methods
        if methods is not None:
            assert isinstance(methods, _MethodsDict)
            methods.sanitize(self)

        # For spyne objects reflecting an existing db table
        if tn is None:
            if t is not None:
                self.Attributes.sqla_metadata = t.metadata
                from spyne.store.relational import gen_spyne_info

                gen_spyne_info(self)

        # For spyne objects being converted to a sqlalchemy table
        elif meta is not None and (tn is not None or t is not None) and \
                                                       len(self._type_info) > 0:
            from spyne.store.relational import gen_sqla_info

            gen_sqla_info(self, cls_bases)

        super(ComplexModelMeta, self).__init__(cls_name, cls_bases, cls_dict)

    #
    # We record the order fields are defined into ordered dict, so we can
    # declare them in the same order in the WSDL.
    #
    # For Python 3 __prepare__ works out of the box, see PEP 3115.
    # But we use `Preparable` metaclass for both Python 2 and Python 3 to
    # support six.add_metaclass decorator
    #
    @classmethod
    def __prepare__(mcs, name, bases, **kwds):
        return odict()

    #
    #  pydev debugger seems to secretly manipulate class dictionaries without
    # doing proper checks -- not always do a class with a metaclass with a
    # __prepare__ has to have it. this code has a very specific workaround to
    # make debugging under pydev for python 3.x work.
    #
    # see https://github.com/arskom/spyne/issues/432 for details
    #
    # this can be removed once pydev fixes secret calls to class dict's
    # __delitem__
    if _is_under_pydev_debugger():
        @classmethod
        def __prepare__(mcs, name, bases, **kwds):
            return odict((('__class__', mcs),))
        print("ComplexModelMeta.__prepare__ substitution for PyDev successful")


_is_array = lambda v: issubclass(v, Array) or (v.Attributes.min_occurs > 1)


class ComplexModelBase(ModelBase):
    """If you want to make a better class type, this is what you should inherit
    from.
    """

    __mixin__ = False

    class Attributes(ModelBase.Attributes):
        """ComplexModel-specific attributes"""

        store_as = None
        """Method for serializing to persistent storage. One of %r. It makes
        sense to specify this only when this object is a child of another
        ComplexModel sublass.""" % (PSSM_VALUES,)

        sqla_metadata = None
        """None or :class:`sqlalchemy.MetaData` instance."""

        sqla_table_args = None
        """A dict that will be passed to :class:`sqlalchemy.schema.Table`
        constructor as ``**kwargs``.
        """

        sqla_mapper_args = None
        """A dict that will be passed to :func:`sqlalchemy.orm.mapper`
        constructor as. ``**kwargs``.
        """

        sqla_table = None
        """The sqlalchemy table object"""

        sqla_mapper = None
        """The sqlalchemy mapper object"""

        validate_freq = True
        """When ``False``, soft validation ignores missing mandatory attributes.
        """

        child_attrs = None
        """Customize child attributes in one go. It's a dict of dicts. This is
        ignored unless used via explicit customization."""

        child_attrs_all = None
        """Customize all child attributes. It's a dict. This is ignored unless
        used via explicit customization. `child_attrs` always take precedence.
        """

        declare_order = None
        """The order fields of the :class:``ComplexModel`` are to be declared
        in the SOAP WSDL. If this is left as None or explicitly set to
        ``'random'`` declares then the fields appear in whatever order the
        Python's hash map implementation seems fit in the WSDL. This randomised
        order can change every time the program is run. This is what Spyne <2.11
        did if you didn't set _type_info as an explicit sequence (e.g. using a
        list, odict, etc.). It means that clients who are manually complied or
        generated from the WSDL will likely need to be recompiled every time it
        changes. The string ``name`` means the field names are alphabetically
        sorted in the WSDL declaration.  The string ``declared`` means in the
        order the field type was declared in Python 2, and the order the
        field was declared in Python 3.

        In order to get declared field order in Python 2, the
        :class:`spyne.util.meta.Preparable` class inspects the frame stack in
        order to locate the class definition, re-parses it to get declaration
        order from the AST and uses that information to order elements.

        It's a horrible hack that we tested to work with CPython 2.6 through 3.3
        and PyPy. It breaks in Nuitka as Nuitka does away with code objects.
        Other platforms were not tested.

        It's not recommended to use set this to ``'declared'`` in Python 2
        unless you're sure you fully understand the consequences.
        """

        parent_variant = None
        """FIXME: document me yo."""

        methods = None
        """FIXME: document me yo."""

        _variants = None
        _xml_tag_body_as = None
        _delayed_child_attrs = None
        _delayed_child_attrs_all = None
        _subclasses = None

    def __init__(self, *args, **kwargs):
        cls = self.__class__
        fti = cls.get_flat_type_info(cls)

        if cls.__orig__ is not None:
            logger.warning("%r seems to be a customized class. It is not "
                      "supposed to be instantiated. You have been warned.", cls)

        if cls.Attributes._xml_tag_body_as is not None:
            for arg, (xtba_key, xtba_type) in \
                                     zip(args, cls.Attributes._xml_tag_body_as):
                if xtba_key is not None and len(args) == 1:
                    self._safe_set(xtba_key, arg, xtba_type)
                elif len(args) > 0:
                    raise TypeError(
                                "Positional argument is only for ComplexModels "
                                "with XmlData field. You must use keyword "
                                "arguments in any other case.")

        for k, v in fti.items():
            if k in kwargs:
                self._safe_set(k, kwargs[k], v)

            elif not k in self.__dict__:
                attr = v.Attributes
                def_val = attr.default
                def_fac = attr.default_factory

                if def_fac is not None:
                    if six.PY2 and hasattr(def_fac, 'im_func'):
                        # unbound-method error workaround. huh.
                        def_fac = def_fac.im_func
                    dval = def_fac()

                    # should not check for read-only for default values
                    setattr(self, k, dval)

                elif def_val is not None:
                    # should not check for read-only for default values
                    setattr(self, k, def_val)

                # sqlalchemy objects do their own init.
                elif hasattr(cls, '_sa_class_manager'):
                    # except the attributes that sqlalchemy doesn't know about
                    if v.Attributes.exc_table:
                        try:
                            setattr(self, k, None)
                        except AttributeError: # it could be a read-only property
                            pass

                    elif issubclass(v, ComplexModelBase) and \
                                                  v.Attributes.store_as is None:
                        setattr(self, k, None)
                else:
                    setattr(self, k, None)

    def __len__(self):
        return len(self._type_info)

    def __getitem__(self, i):
        if isinstance(i, slice):
            retval = []
            for key in self._type_info.keys()[i]:
                retval.append(getattr(self, key, None))

        else:
            retval = getattr(self, self._type_info.keys()[i], None)

        return retval

    def __repr__(self):
        return "%s(%s)" % (self.get_type_name(), ', '.join(
               ['%s=%r' % (k, self.__dict__.get(k))
                    for k in self.__class__.get_flat_type_info(self.__class__)
                    if self.__dict__.get(k, None) is not None]))

    def _safe_set(self, key, value, t):
        if t.Attributes.read_only:
            return False

        try:
            setattr(self, key, value)
        except AttributeError as e:
            logger.exception(e)
            raise AttributeError("can't set %r attribute %s to %r" %
                                                   (self.__class__, key, value))

        return True

    def as_dict(self):
        """Represent object as dict.

        Null values are omitted from dict representation to support optional
        not nullable attributes.

        """
        return dict((
            (k, getattr(self, k)) for k in self.get_flat_type_info(self)
            if getattr(self, k) is not None
        ))

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

            cls_orig = cls
            if cls.__orig__ is not None:
                cls_orig = cls.__orig__
            inst = cls_orig()

            keys = cls.get_flat_type_info(cls).keys()
            for i in range(len(value)):
                setattr(inst, keys[i], value[i])

        elif isinstance(value, dict):
            cls_orig = cls
            if cls.__orig__ is not None:
                cls_orig = cls.__orig__
            inst = cls_orig()

            for k in cls.get_flat_type_info(cls):
                setattr(inst, k, value.get(k, None))

        else:
            inst = value

        return inst

    @classmethod
    def get_deserialization_instance(cls):
        """Get an empty native type so that the deserialization logic can set
        its attributes.
        """
        if cls.__orig__ is None:
            return cls()
        return cls.__orig__()

    @classmethod
    @memoize_id
    def get_subclasses(cls):
        retval = []
        subca = cls.Attributes._subclasses
        if subca is not None:
            retval.extend(subca)
            for subc in subca:
                retval.extend(subc.get_subclasses())
        return retval

    @staticmethod
    @memoize
    def get_flat_type_info(cls):
        """Returns a _type_info dict that includes members from all base
        classes.

        It's called a "flat" dict because it flattens all members from the
        inheritance hierarchy into one dict.
        """
        return _get_flat_type_info(cls, TypeInfo())

    @classmethod
    def get_orig(cls):
        return cls.__orig__ or cls

    @staticmethod
    @memoize
    def get_simple_type_info(cls, hier_delim="."):
        """Returns a _type_info dict that includes members from all base classes
        and whose types are only primitives. It will prefix field names in
        non-top-level complex objects with field name of its parent.

        For example, given hier_delim='_'; the following hierarchy: ::

            {'some_object': [{'some_string': ['abc']}]}

        would be transformed to: ::

            {'some_object_some_string': ['abc']}

        :param hier_delim: String that will be used as delimiter between field
            names. Default is ``'_'``.
        """

        fti = cls.get_flat_type_info(cls)

        retval = TypeInfo()
        tags = set()
        queue = deque([(k, v, (k,), (_is_array(v),), cls)
                                                        for k,v in fti.items()])
        tags.add(cls)

        while len(queue) > 0:
            k, v, prefix, is_array, parent = queue.popleft()
            if issubclass(v, Array) and v.Attributes.max_occurs == 1:
                v, = v._type_info.values()

            key = hier_delim.join(prefix)
            if issubclass(v, ComplexModelBase):
                retval[key] = _SimpleTypeInfoElement(path=tuple(prefix),
                               parent=parent, type_=v, is_array=tuple(is_array),
                                                              can_be_empty=True)

                if not (v in tags):
                    tags.add(v)
                    queue.extend([
                        (k2, v2, prefix + (k2,),
                            is_array + (v.Attributes.max_occurs > 1,), v)
                                   for k2, v2 in v.get_flat_type_info(v).items()])
            else:
                value = retval.get(key, None)

                if value is not None:
                    raise ValueError("%r.%s conflicts with %r" %
                                                       (cls, k, value.path))

                retval[key] = _SimpleTypeInfoElement(path=tuple(prefix),
                               parent=parent, type_=v, is_array=tuple(is_array),
                                                             can_be_empty=False)

        return retval

    @staticmethod
    def resolve_namespace(cls, default_ns, tags=None):
        if tags is None:
            tags = set()
        elif cls in tags:
            return False

        if not ModelBase.resolve_namespace(cls, default_ns, tags):
            return False

        for k, v in cls._type_info.items():
            if v is None:
                continue

            if v.__type_name__ is ModelBase.Empty:
                v._fill_empty_type_name(cls.get_namespace(),
                                                         cls.get_type_name(), k)

            v.resolve_namespace(v, default_ns, tags)

        if cls._force_own_namespace is not None:
            for c in cls._force_own_namespace:
                c.__namespace__ = cls.get_namespace()
                ComplexModel.resolve_namespace(c, cls.get_namespace(), tags)

        assert not (cls.__namespace__ is ModelBase.Empty)
        assert not (cls.__type_name__ is ModelBase.Empty)

        return True

    @staticmethod
    def produce(namespace, type_name, members):
        """Lets you create a class programmatically."""

        return ComplexModelMeta(type_name, (ComplexModel,), odict({
            '__namespace__': namespace,
            '__type_name__': type_name,
            '_type_info': TypeInfo(members),
        }))

    @classmethod
    def customize(cls, **kwargs):
        """Duplicates cls and overwrites the values in ``cls.Attributes`` with
        ``**kwargs`` and returns the new class.

        Because each class is registered as a variant of the original (__orig__)
        class, using this function to generate classes dynamically on-the-fly
        could cause memory leaks. You have been warned.
        """

        store_as = apply_pssm(kwargs.get('store_as', None), PSSM_VALUES)
        if store_as is not None:
            kwargs['store_as'] = store_as

        cls_name, cls_bases, cls_dict = cls._s_customize(cls, **kwargs)
        cls_dict['__module__'] = cls.__module__
        if '__extends__' not in cls_dict:
            cls_dict['__extends__'] = cls.__extends__

        retval = type(cls_name, cls_bases, cls_dict)
        retval._type_info = TypeInfo(cls._type_info)
        retval.__type_name__ = cls.__type_name__
        retval.__namespace__ = cls.__namespace__
        retval.Attributes.parent_variant = cls

        dca = retval.Attributes._delayed_child_attrs
        if retval.Attributes._delayed_child_attrs is None:
            retval.Attributes._delayed_child_attrs = {}
        else:
            retval.Attributes._delayed_child_attrs = dict(dca.items())

        tn = kwargs.get("type_name", None)
        if tn is not None:
            retval.__type_name__ = tn

        ns = kwargs.get("namespace", None)
        if ns is not None:
            retval.__namespace__ = ns

        if cls is not ComplexModel:
            cls._process_variants(retval)

        _process_child_attrs(cls, retval, kwargs)

        # we could be smarter, but customize is supposed to be called only
        # during daemon initialization, so it's not really necessary.
        ComplexModelBase.get_subclasses.memo.clear()
        ComplexModelBase.get_flat_type_info.memo.clear()
        ComplexModelBase.get_simple_type_info.memo.clear()

        return retval

    @classmethod
    def _process_variants(cls, retval):
        orig = getattr(retval, '__orig__', None)
        if orig is not None:
            if orig.Attributes._variants is None:
                orig.Attributes._variants = WeakKeyDictionary()
            orig.Attributes._variants[retval] = True
            # _variants is only for the root class.
            retval.Attributes._variants = None

    @classmethod
    def _append_field_impl(cls, field_name, field_type):
        assert isinstance(field_name, string_types)

        dcaa = cls.Attributes._delayed_child_attrs_all
        if dcaa is not None:
            field_type = field_type.customize(**dcaa)

        dca = cls.Attributes._delayed_child_attrs
        if dca is not None:
            d_cust = dca.get(field_name, None)
            if d_cust is not None:
                field_type = field_type.customize(**d_cust)

        cls._type_info[field_name] = field_type

        ComplexModelBase.get_flat_type_info.memo.clear()
        ComplexModelBase.get_simple_type_info.memo.clear()

    @classmethod
    def _append_to_variants(cls, field_name, field_type):
        if cls.Attributes._variants is not None:
            for c in cls.Attributes._variants:
                c.append_field(field_name, field_type)

    @classmethod
    def append_field(cls, field_name, field_type):
        cls._append_field_impl(field_name, field_type)
        cls._append_to_variants(field_name, field_type)

    @classmethod
    def _insert_to_variants(cls, index, field_name, field_type):
        if cls.Attributes._variants is not None:
            for c in cls.Attributes._variants:
                c.insert_field(index, field_name, field_type)

    @classmethod
    def _insert_field_impl(cls, index, field_name, field_type):
        assert isinstance(index, int)
        assert isinstance(field_name, string_types)

        dcaa = cls.Attributes._delayed_child_attrs_all
        if dcaa is not None:
            field_type = field_type.customize(**dcaa)

        dca = cls.Attributes._delayed_child_attrs
        if dca is not None:
            if field_name in dca:
                d_cust = dca.pop(field_name)
                field_type = field_type.customize(**d_cust)

        cls._type_info.insert(index, (field_name, field_type))

        ComplexModelBase.get_flat_type_info.memo.clear()
        ComplexModelBase.get_simple_type_info.memo.clear()

    @classmethod
    def insert_field(cls, index, field_name, field_type):
        cls._insert_field_impl(index, field_name, field_type)
        cls._insert_to_variants(index, field_name, field_type)

    @classmethod
    def _replace_in_variants(cls, field_name, field_type):
        if cls.Attributes._variants is not None:
            for c in cls.Attributes._variants:
                c._replace_field(field_name, field_type)

    @classmethod
    def _replace_field_impl(cls, field_name, field_type):
        assert isinstance(field_name, string_types)

        cls._type_info[field_name] = field_type

        ComplexModelBase.get_flat_type_info.memo.clear()
        ComplexModelBase.get_simple_type_info.memo.clear()

    @classmethod
    def _replace_field(cls, field_name, field_type):
        cls._replace_field_impl(field_name, field_type)
        cls._replace_in_variants(field_name, field_type)

    @classmethod
    def store_as(cls, what):
        return cls.customize(store_as=what)

    @classmethod
    def novalidate_freq(cls):
        return cls.customize(validate_freq=False)

    @classmethod
    def init_from(cls, other, **kwargs):
        retval = (cls if cls.__orig__ is None else cls.__orig__)()

        for k, v in cls._type_info.items():
            if v.Attributes.read_only:
                continue

            try:
                if k in kwargs:
                    setattr(retval, k, kwargs[k])

                elif hasattr(other, k):
                    setattr(retval, k, getattr(other, k))

            except AttributeError as e:
                logger.warning("Error setting %s: %r", k, e)

        return retval

    @classmethod
    def __respawn__(cls, ctx=None):
        if ctx is not None and ctx.in_object is not None and \
                                                         len(ctx.in_object) > 0:
            return ctx.in_object[0]


@add_metaclass(ComplexModelMeta)
class ComplexModel(ComplexModelBase):
    """The general complexType factory. The __call__ method of this class will
    return instances, contrary to primivites where the same call will result in
    customized duplicates of the original class definition.
    Those who'd like to customize the class should use the customize method.
    (see :class:``spyne.model.ModelBase``).
    """


@add_metaclass(ComplexModelMeta)
class Array(ComplexModelBase):
    """This class generates a ComplexModel child that has one attribute that has
    the same name as the serialized class. It's contained in a Python list.
    """

    class Attributes(ComplexModelBase.Attributes):
        _wrapper = True

    def __new__(cls, serializer, member_name=None, wrapped=True, **kwargs):
        if not wrapped:
            if serializer.Attributes.max_occurs == 1:
                kwargs['max_occurs'] = 'unbounded'

            return serializer.customize(**kwargs)

        retval = cls.customize(**kwargs)

        _serializer = _get_spyne_type(cls.__name__, '__serializer__', serializer)
        if _serializer is None:
            raise ValueError("serializer=%r is not a valid spyne type" % serializer)

        if issubclass(_serializer, SelfReference):
             # hack to make sure the array passes ComplexModel sanity checks
             # that are there to prevent empty arrays.
            retval._type_info = {'_bogus': _serializer}
        else:
            retval._set_serializer(_serializer, member_name)

        tn = kwargs.get("type_name", None)
        if tn is not None:
            retval.__type_name__ = tn

        return retval

    @classmethod
    def _fill_empty_type_name(cls, parent_ns, parent_tn, k):
        cls.__namespace__ = parent_ns
        tn = "%s_%s%s" % (parent_tn, k, const.TYPE_SUFFIX)

        child_v, = cls._type_info.values()
        child_v.__type_name__ = tn

        cls._type_info = TypeInfo({tn: child_v})
        cls.__type_name__ = '%s%s%s' % (const.ARRAY_PREFIX, tn,
                                                             const.ARRAY_SUFFIX)

        extends = child_v.__extends__
        while extends is not None and extends.get_type_name() is cls.Empty:
            extends._fill_empty_type_name(parent_ns, parent_tn,
                                                    k + const.PARENT_SUFFIX)
            extends = extends.__extends__

    @classmethod
    def customize(cls, **kwargs):
        serializer_attrs = kwargs.get('serializer_attrs', None)
        if serializer_attrs is None:
            return super(Array, cls).customize(**kwargs)

        del kwargs['serializer_attrs']

        serializer, = cls._type_info.values()
        return cls(serializer.customize(**serializer_attrs)).customize(**kwargs)

    @classmethod
    def _set_serializer(cls, serializer, member_name=None):
        if serializer.get_type_name() is ModelBase.Empty:  # A customized class
            member_name = "OhNoes"
            # mark array type name as "to be resolved later".
            cls.__type_name__ = ModelBase.Empty

        else:
            if member_name is None:
                member_name = serializer.get_type_name()

            cls.__type_name__ = '%s%s%s' % (const.ARRAY_PREFIX,
                                                serializer.get_type_name(),
                                                             const.ARRAY_SUFFIX)

        # hack to default to unbounded arrays when the user didn't specify
        # max_occurs.
        if serializer.Attributes.max_occurs == 1:
            serializer = serializer.customize(max_occurs=decimal.Decimal('inf'))

        assert isinstance(member_name, string_types), member_name
        cls._type_info = TypeInfo({member_name: serializer})

    # the array belongs to its child's namespace, it doesn't have its own
    # namespace.
    @staticmethod
    def resolve_namespace(cls, default_ns, tags=None):
        (serializer,) = cls._type_info.values()

        serializer.resolve_namespace(serializer, default_ns, tags)

        if cls.__namespace__ is None:
            cls.__namespace__ = serializer.get_namespace()

        if cls.__namespace__ in xml_ns.const_prefmap:
            cls.__namespace__ = default_ns

        return ComplexModel.resolve_namespace(cls, default_ns, tags)

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

    Whenever you return a generator instead of a list, you should use this type
    as this suggests the intermediate machinery to NEVER actually try to iterate
    over the value. An ``Array`` could be iterated over for e.g. logging
    purposes.
    """

    class Attributes(Array.Attributes):
        logged = False

    class Push(PushBase):
        pass


@memoize
def TTableModelBase():
    from spyne.store.relational import add_column

    class TableModelBase(ComplexModelBase):
        @classmethod
        def append_field(cls, field_name, field_type):
            cls._append_field_impl(field_name, field_type)
            # There could have been changes to field_type in ComplexModel so we
            # should not use field_type directly from above
            if cls.__table__ is not None:
                add_column(cls, field_name, cls._type_info[field_name])
            cls._append_to_variants(field_name, field_type)

        @classmethod
        def replace_field(cls, field_name, field_type):
            raise NotImplementedError()

        @classmethod
        def insert_field(cls, index, field_name, field_type):
            cls._insert_field_impl(index, field_name, field_type)
            # There could have been changes to field_type in ComplexModel so we
            # should not use field_type directly from above
            if cls.__table__ is not None:
                add_column(cls, field_name, cls._type_info[field_name])
            cls._insert_to_variants(index, field_name, field_type)

    return TableModelBase


# this has docstring repeated in the documentation at reference/model/complex.rst
@memoize_id
def TTableModel(metadata=None):
    """A TableModel template that generates a new TableModel class for each
    call. If metadata is not supplied, a new one is instantiated.
    """

    from sqlalchemy import MetaData

    @add_metaclass(ComplexModelMeta)
    class TableModel(TTableModelBase()):
        class Attributes(ComplexModelBase.Attributes):
            sqla_metadata = metadata or MetaData()

    return TableModel


def Mandatory(cls, **_kwargs):
    """Customizes the given type to be a mandatory one. Has special cases for
    :class:`spyne.model.primitive.Unicode` and
    :class:`spyne.model.complex.Array`\.
    """

    kwargs = dict(min_occurs=1, nillable=False)
    if cls.get_type_name() is not cls.Empty:
        kwargs['type_name'] = '%s%s%s' % (const.MANDATORY_PREFIX,
                                    cls.get_type_name(), const.MANDATORY_SUFFIX)
    kwargs.update(_kwargs)
    if issubclass(cls, Unicode):
        kwargs.update(dict(min_len=1))

    elif issubclass(cls, Array):
        (k,v), = cls._type_info.items()
        if v.Attributes.min_occurs == 0:
            cls._type_info[k] = Mandatory(v)

    return cls.customize(**kwargs)
