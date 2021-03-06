
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

"""This module contains the ModelBase class and other building blocks for
defining models.
"""

from __future__ import print_function

import logging
logger = logging.getLogger(__name__)

import re
import decimal
import threading

import spyne.const.xml

from copy import deepcopy
from collections import OrderedDict

from spyne import const
from spyne.util import Break, six
from spyne.util.cdict import cdict
from spyne.util.odict import odict

from spyne.const.xml import DEFAULT_NS


class Ignored(object):
    """When returned as a real rpc response, this is equivalent to returning
    None. However, direct method invocations (and NullServer) get the return
    value. It can be used for tests and from hooks."""

    __slots__ = ('args', 'kwargs')

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __eq__(self, other):
        return      isinstance(other, Ignored) \
                    and self.args == other.args and self.kwargs == other.kwargs

    def __ne__(self, other):
        return not (isinstance(other, Ignored) \
                    and self.args == other.args and self.kwargs == other.kwargs)


def _decode_pa_dict(d):
    """Decodes dict passed to prot_attrs.

    >>> _decode_pa_dict({})
    cdict({})
    >>> _decode_pa_dict({1: 2)})
    cdict({1: 2})
    >>> _decode_pa_dict({(1,2): 3)})
    cdict({1: 3, 2: 3})
    """

    retval = cdict()
    for k, v in d.items():
        if isinstance(k, (frozenset, tuple)):
            for subk in k:
                retval[subk] = v

    for k, v in d.items():
        if not isinstance(k, (frozenset, tuple)):
            retval[k] = v

    return retval


class AttributesMeta(type(object)):
    NULLABLE_DEFAULT = True

    def __new__(cls, cls_name, cls_bases, cls_dict):
        # Mapper args should not be inherited.
        if not 'sqla_mapper_args' in cls_dict:
            cls_dict['sqla_mapper_args'] = None

        rd = {}
        for k in list(cls_dict.keys()):
            if k in ('parser', 'cast'):
                rd['parser'] = cls_dict.pop(k)
                continue

            if k in ('sanitize', 'sanitizer'):
                rd['sanitizer'] = cls_dict.pop(k)
                continue

            if k == 'logged':
                rd['logged'] = cls_dict.pop(k)
                continue

        retval = super(AttributesMeta, cls).__new__(cls, cls_name, cls_bases,
                                                                       cls_dict)

        for k, v in rd.items():
            if v is None:
                setattr(retval, k, None)
            else:
                setattr(retval, k, staticmethod(v))

        return retval

    def __init__(self, cls_name, cls_bases, cls_dict):
        # you will probably want to look at ModelBase._s_customize as well.
        if not hasattr(self, '_method_config_do'):
            self._method_config_do = None

        nullable = cls_dict.get('nullable', None)
        nillable = cls_dict.get('nillable', None)
        if nullable is not None:
            assert nillable is None or nullable == nillable
            self._nullable = nullable

        elif nillable is not None:
            assert nullable is None or nullable == nillable
            self._nullable = nillable

        if not hasattr(self, '_nullable'):
            self._nullable = None

        if not hasattr(self, '_default_factory'):
            self._default_factory = None

        if not hasattr(self, '_html_cloth'):
            self._html_cloth = None
        if not hasattr(self, '_html_root_cloth'):
            self._html_root_cloth = None

        if 'html_cloth' in cls_dict:
            self.set_html_cloth(cls_dict.pop('html_cloth'))
        if 'html_root_cloth' in cls_dict:
            self.set_html_cloth(cls_dict.pop('html_root_cloth'))

        if not hasattr(self, '_xml_cloth'):
            self._xml_cloth = None
        if not hasattr(self, '_xml_root_cloth'):
            self._xml_root_cloth = None

        if 'xml_cloth' in cls_dict:
            self.set_xml_cloth(cls_dict.pop('xml_cloth'))

        if 'xml_root_cloth' in cls_dict:
            self.set_xml_cloth(cls_dict.pop('xml_root_cloth'))

        if 'method_config_do' in cls_dict and \
                                       cls_dict['method_config_do'] is not None:
            cls_dict['method_config_do'] = \
                                      staticmethod(cls_dict['method_config_do'])

        super(AttributesMeta, self).__init__(cls_name, cls_bases, cls_dict)

    def get_nullable(self):
        return (self._nullable if self._nullable is not None else
                                                          self.NULLABLE_DEFAULT)

    def set_nullable(self, what):
        self._nullable = what

    nullable = property(get_nullable, set_nullable)

    def get_nillable(self):
        return self.nullable

    def set_nillable(self, what):
        self.nullable = what

    nillable = property(get_nillable, set_nillable)

    def get_default_factory(self):
        return self._default_factory

    def set_default_factory(self, what):
        self._default_factory = staticmethod(what)

    default_factory = property(get_default_factory, set_default_factory)

    def get_html_cloth(self):
        return self._html_cloth
    def set_html_cloth(self, what):
        from spyne.protocol.cloth.to_cloth import ClothParserMixin
        cm = ClothParserMixin.from_html_cloth(what)
        if cm._root_cloth is not None:
            self._html_root_cloth = cm._root_cloth
        elif cm._cloth is not None:
            self._html_cloth = cm._cloth
        else:
            raise Exception("%r is not a suitable cloth", what)
    html_cloth = property(get_html_cloth, set_html_cloth)

    def get_html_root_cloth(self):
        return self._html_root_cloth
    html_root_cloth = property(get_html_root_cloth)

    def get_xml_cloth(self):
        return self._xml_cloth
    def set_xml_cloth(self, what):
        from spyne.protocol.cloth.to_cloth import ClothParserMixin
        cm = ClothParserMixin.from_xml_cloth(what)
        if cm._root_cloth is not None:
            self._xml_root_cloth = cm._root_cloth
        elif cm._cloth is not None:
            self._xml_cloth = cm._cloth
        else:
            raise Exception("%r is not a suitable cloth", what)
    xml_cloth = property(get_xml_cloth, set_xml_cloth)

    def get_xml_root_cloth(self):
        return self._xml_root_cloth
    xml_root_cloth = property(get_xml_root_cloth)

    def get_method_config_do(self):
        return self._method_config_do
    def set_method_config_do(self, what):
        if what is None:
            self._method_config_do = None
        else:
            self._method_config_do = staticmethod(what)
    method_config_do = property(get_method_config_do, set_method_config_do)


class ModelBaseMeta(type(object)):
    def __getitem__(self, item):
        return self.customize(**item)

    def customize(self, **kwargs):
        """Duplicates cls and overwrites the values in ``cls.Attributes`` with
        ``**kwargs`` and returns the new class."""

        cls_name, cls_bases, cls_dict = self._s_customize(**kwargs)

        return type(cls_name, cls_bases, cls_dict)


@six.add_metaclass(ModelBaseMeta)
class ModelBase(object):
    """The base class for type markers. It defines the model interface for the
    interface generators to use and also manages class customizations that are
    mainly used for defining constraints on input values.
    """

    __orig__ = None
    """This holds the original class the class .customize()d from. Ie if this is
    None, the class is not a customize()d one."""

    __extends__ = None
    """This holds the original class the class inherited or .customize()d from.
    This is different from __orig__ because it's only set when
    ``cls.is_default(cls) == False``"""

    __namespace__ = None
    """The public namespace of this class. Use ``get_namespace()`` instead of
    accessing it directly."""

    __type_name__ = None
    """The public type name of the class. Use ``get_type_name()`` instead of
    accessing it directly."""

    Value = type(None)
    """The value of this type is an instance of this class"""

    # These are not the xml schema defaults. The xml schema defaults are
    # considered in XmlSchema's add() method. the defaults here are to reflect
    # what people seem to want most.
    #
    # Please note that min_occurs and max_occurs must be validated in the
    # ComplexModelBase deserializer.
    @six.add_metaclass(AttributesMeta)
    class Attributes(object):
        """The class that holds the constraints for the given type."""

        _wrapper = False
        # when skip_wrappers=True is passed to a protocol, these objects
        # are skipped. just for internal use.

        _explicit_type_name = False
        # set to true when type_name is passed to customize() call.

        out_type = None
        """Override serialization type. Usually, this designates the return type
        of the callable in the `sanitizer` attribute. If this is a two-way type,
        it may be a good idea to also use the `parser` attribute to perform
        reverse conversion."""

        default = None
        """The default value if the input is None.

        Please note that this default is UNCONDITIONALLY applied in class
        initializer. It's recommended to at least make an effort to use this
        only in customized classes and not in original models.
        """

        default_factory = None
        """The callable that produces a default value if the value is None.

        The warnings in ``default`` apply here as well."""

        db_default = None
        """The default value used only when persisting the value if it is
        ``None``.

        Only works for primitives. Unlike ``default`` this can also be set to a
        callable that takes no arguments according to SQLAlchemy docs."""

        nillable = None
        """Set this to false to reject null values. Synonyms with
        ``nullable``. True by default. The default value can be changed by
         setting ``AttributesMeta.NULLABLE_DEFAULT``."""

        min_occurs = 0
        """Set this to 1 to make this object mandatory. Can be set to any
        positive integer. Note that an object can still be null or empty, even
        if it's there."""

        max_occurs = 1
        """Can be set to any strictly positive integer. Values greater than 1
        will imply an iterable of objects as native python type. Can be set to
        ``decimal.Decimal("inf")`` for arbitrary number of arguments."""

        schema_tag = spyne.const.xml.XSD('element')
        """The tag used to add a primitives as child to a complex type in the
        xml schema."""

        translations = None
        """A dict that contains locale codes as keys and translations of field
        names to that language as values.
        """

        sub_ns = None
        """An Xml-specific attribute that specifies which namespace should be
        used for field names in classes.
        """

        sub_name = None
        """This specifies which string should be used as field name when this
        type is seriazed under a ComplexModel.
        """

        wsdl_part_name = None
        """This specifies which string should be used as wsdl message part name when this
            type is serialized under a ComplexModel ie."parameters".
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
        """DEPRECATED !!! Use ``exc_db`` instead."""

        exc_db = False
        """If ``True``, this field will not be persisted to the database. This
        attribute only makes sense in a subfield of a ``ComplexModel`` subclass.
        """

        exc_interface = False
        """If `True`, this field will be excluded from the interface
        document."""

        exc = False
        """If `True`, this field will be excluded from all serialization or
         deserialization operations. See `prot_attrs` to make this only apply to
         a specific protocol class or instance."""

        logged = True
        """If `False`, this object will be ignored in ``log_repr``, mostly used
        for logging purposes.

        * Primitives can have logger=``'...'`` which will
        always log the value as ``(...)``.

        * ``AnyDict`` can have one of
        ``('keys', 'keys-full', 'values', 'values-full, 'full')`` as logger
        value where for ``'keys'`` and ``'values'`` the output of ``keys()``
        and ``values()`` will be logged up to MAX_DICT_ELEMENT_NUM number of
        elements and for ``'full'`` variants, all of the contents of the dict
        will be logged will be logged

        * ``Array`` can also have ``logger='full'`` where all of the value
        will be logged where as for simple ``logger=True`` only
        MAX_ARRAY_ELEMENT_NUM elements will be logged.

        * For ``ComplexModel`` subclasses sent as first value to log_repr,
        ``logger=False`` means a string of form ``ClassName(...)`` will  be
        logged.
        """

        sanitizer = None
        """A callable that takes the associated native type and returns the
        parsed value. Only called during serialization."""

        parser = None
        """A callable that takes the associated native type and returns the
        parsed value. Only called during deserialization."""

        unique = None
        """If True, this object will be set as unique in the database schema
        with default indexing options. If the value is a string, it will be
        used as the indexing method to create the unique index. See sqlalchemy
        documentation on how to create multi-column unique constraints.
        """

        db_type = None
        """When not None, it overrides Spyne's own mapping from Spyne types to
        SQLAlchemy types. It's a standard SQLAlchemy type marker, e.g.
        ``sqlalchemy.Integer``.
        """

        table_name = None
        """Database table name."""

        xml_choice_group = None
        """When not None, shares the same <choice> tag with fields with the same
        xml_choice_group value.
        """

        index = None
        """Can be ``True``, a string, or a tuple of two strings.

        * If True, this object will be set as indexed in the database schema
          with default options.

        * If the value is a string, the value will denote the indexing method
          used by the database. Should be one of:

            ('btree', 'gin', 'gist', 'hash', 'spgist')

          See: http://www.postgresql.org/docs/9.2/static/indexes-types.html

        * If the value is a tuple of two strings, the first value will denote
          the index name and the second value will denote the indexing method as
          above.
        """

        read_only = False
        """If True, the attribute won't be initialized from outside values.
        Set this to ``True`` for e.g. read-only properties."""

        prot_attrs = None
        """Customize child attributes for protocols. It's a dict of dicts.
        The key is either a ProtocolBase subclass or a ProtocolBase instance.
        Instances override classes."""

        pa = None
        """Alias for prot_attrs."""

        empty_is_none = False
        """When the incoming object is empty (e.g. '' for strings) treat it as
        None. No effect (yet) for outgoing values."""

        order = None
        """An integer that's passed to ``_type_info.insert()`` as first argument
         when not None. ``.append()`` is used otherwise."""

        validate_on_assignment = False
        """Perform validation on assignment (i.e. all the time) instead of on
        just serialization"""

        polymap = {}
        """A dict of classes that override polymorphic substitions for classes
        given as keys to classes given as values."""


    class Annotations(object):
        """The class that holds the annotations for the given type."""

        __use_parent_doc__ = False
        """If equal to True and doc is empty, Annotations will use __doc__
        from parent. Set it to False to avoid this mechanism. This is a
        convenience option"""

        doc = ""
        """The public documentation for the given type."""

        appinfo = None
        """Any object that carries app-specific info."""

    class Empty(object):
        pass

    _force_own_namespace = None

    @classmethod
    def ancestors(cls):
        """Returns a list of parent classes in child-to-parent order."""

        retval = []

        extends = cls.__extends__
        while extends is not None:
            retval.append(extends)
            extends = extends.__extends__

        return retval

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

    @classmethod
    def _fill_empty_type_name(cls, parent_ns, parent_tn, k):
        cls.__namespace__ = parent_ns

        cls.__type_name__ = "%s_%s%s" % (parent_tn, k, const.TYPE_SUFFIX)
        extends = cls.__extends__
        while extends is not None and extends.__type_name__ is ModelBase.Empty:
            cls.__extends__._fill_empty_type_name(cls.get_namespace(),
                               cls.get_type_name(), k + const.PARENT_SUFFIX)
            extends = extends.__extends__

    # TODO: rename to "resolve_identifier"
    @staticmethod
    def resolve_namespace(cls, default_ns, tags=None):
        """This call finalizes the namespace assignment. The default namespace
        is not available until the application calls populate_interface method
        of the interface generator.
        """

        if tags is None:
            tags = set()
        elif cls in tags:
            return False
        tags.add(cls)

        if cls.__namespace__ is spyne.const.xml.DEFAULT_NS:
            cls.__namespace__ = default_ns

        if (cls.__namespace__ in spyne.const.xml.PREFMAP and
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

        if cls.__namespace__ is None or len(cls.__namespace__) == 0:
            cls.__namespace__ = default_ns

        if cls.__namespace__ is None or len(cls.__namespace__) == 0:
            raise ValueError("You need to explicitly set %r.__namespace__" % cls)

        # print("    resolve ns for %r to %r" % (cls, cls.__namespace__))

        if getattr(cls, '__extends__', None) != None:
            cls.__extends__.resolve_namespace(cls.__extends__, default_ns, tags)

        return True

    @classmethod
    def get_type_name(cls):
        """Returns the class name unless the __type_name__ attribute is defined.
        """

        retval = cls.__type_name__
        if retval is None:
            retval = cls.__name__

        return retval

    # FIXME: Rename this to get_type_name_with_ns_pref
    @classmethod
    def get_type_name_ns(cls, interface):
        """Returns the type name with a namespace prefix, separated by a column.
        """

        if cls.get_namespace() != None:
            return "%s:%s" % (cls.get_namespace_prefix(interface),
                                                            cls.get_type_name())

    @classmethod
    def get_element_name(cls):
        return cls.Attributes.sub_name or cls.get_type_name()

    @classmethod
    def get_wsdl_part_name(cls):
        return cls.Attributes.wsdl_part_name or cls.get_element_name()

    @classmethod
    def get_element_name_ns(cls, interface):
        ns = cls.Attributes.sub_ns or cls.get_namespace()
        if ns is DEFAULT_NS:
            ns = interface.get_tns()
        if ns is not None:
            pref = interface.get_namespace_prefix(ns)
            return "%s:%s" % (pref, cls.get_element_name())

    @classmethod
    def to_bytes(cls, value):
        """
        Returns str(value). This should be overridden if this is not enough.
        """
        return six.binary_type(value)

    @classmethod
    def to_unicode(cls, value):
        """
        Returns unicode(value). This should be overridden if this is not enough.
        """
        return six.text_type(value)

    @classmethod
    def get_documentation(cls):
        if cls.Annotations.doc:
            return cls.Annotations.doc
        elif cls.Annotations.__use_parent_doc__:
            return cls.__doc__
        else:
            return ''

    @classmethod
    def _s_customize(cls, **kwargs):
        """Sanitizes customization parameters of the class it belongs to.
        Doesn't perform any actual customization.
        """

        def _log_debug(s, *args):
            logger.debug("\t%s: %s" % (cls.get_type_name(), s), *args)

        cls_dict = odict({'__module__': cls.__module__, '__doc__': cls.__doc__})

        if getattr(cls, '__orig__', None) is None:
            cls_dict['__orig__'] = cls
        else:
            cls_dict['__orig__'] = cls.__orig__

        class Attributes(cls.Attributes):
            _explicit_type_name = False

        if cls.Attributes.translations is None:
            Attributes.translations = {}

        if cls.Attributes.sqla_column_args is None:
            Attributes.sqla_column_args = (), {}
        else:
            Attributes.sqla_column_args = deepcopy(
                                                cls.Attributes.sqla_column_args)

        cls_dict['Attributes'] = Attributes

        # properties get reset every time a new class is defined. So we need
        # to reinitialize them explicitly.
        for k in ('nillable', '_xml_cloth', '_xml_root_cloth', '_html_cloth',
                                                            '_html_root_cloth'):
            v = getattr(cls.Attributes, k)
            if v is not None:
                setattr(Attributes, k, v)

        class Annotations(cls.Annotations):
            pass
        cls_dict['Annotations'] = Annotations

        # get protocol attrs
        prot = kwargs.get('protocol', None)
        if prot is None:
            prot = kwargs.get('prot', None)

        if prot is None:
            prot = kwargs.get('p', None)

        if prot is not None and len(prot.type_attrs) > 0:
            # if there is a class customization from protocol, do it

            type_attrs = prot.type_attrs.copy()
            type_attrs.update(kwargs)
            _log_debug("kwargs %r => %r from prot typeattr %r",
                                            kwargs, type_attrs, prot.type_attrs)
            kwargs = type_attrs

        # the ones that wrap values in staticmethod() should be added to
        # AttributesMeta initializer
        for k, v in kwargs.items():
            if k.startswith('_'):
                _log_debug("ignoring '%s' because of leading underscore", k)
                continue

            if k in ('protocol', 'prot', 'p'):
                Attributes.prot = v
                _log_debug("setting prot=%r", v)

            elif k in ('voa', 'validate_on_assignment'):
                Attributes.validate_on_assignment = v
                _log_debug("setting voa=%r", v)

            elif k in ('parser', 'in_cast'):
                setattr(Attributes, 'parser', staticmethod(v))
                _log_debug("setting %s=%r", k, v)

            elif k in ('sanitize', 'sanitizer', 'out_cast'):
                setattr(Attributes, 'sanitizer', staticmethod(v))
                _log_debug("setting %s=%r as sanitizer", k, v)

            elif k == 'logged':
                setattr(Attributes, 'logged', staticmethod(v))
                _log_debug("setting %s=%r as log sanitizer", k, v)

            elif k in ("doc", "appinfo"):
                setattr(Annotations, k, v)
                _log_debug("setting Annotations.%s=%r", k, v)

            elif k in ('primary_key', 'pk'):
                setattr(Attributes, 'primary_key', v)
                Attributes.sqla_column_args[-1]['primary_key'] = v
                _log_debug("setting primary_key=%r", v)

            elif k in ('protocol_attrs', 'prot_attrs', 'pa'):
                setattr(Attributes, 'prot_attrs', _decode_pa_dict(v))
                _log_debug("setting prot_attrs=%r", v)

            elif k in ('foreign_key', 'fk'):
                from sqlalchemy.schema import ForeignKey
                t, d = Attributes.sqla_column_args
                fkt = (ForeignKey(v),)
                new_v = (t + fkt, d)
                Attributes.sqla_column_args = new_v
                _log_debug("setting sqla_column_args=%r", new_v)

            elif k in ('autoincrement', 'onupdate', 'server_default'):
                Attributes.sqla_column_args[-1][k] = v
                _log_debug("adding %s=%r to Attributes.sqla_column_args", k, v)

            elif k == 'values_dict':
                assert not 'values' in v, "`values` and `values_dict` can't be" \
                                          "specified at the same time"

                if not isinstance(v, dict):
                    # our odict has one nasty implicit behaviour: setitem on
                    # int keys is treated as array indexes, not dict keys. so
                    # dicts with int indexes can't work with odict. so we use
                    # the one from stdlib
                    v = OrderedDict(v)

                Attributes.values = list(v.keys())
                Attributes.values_dict = v
                _log_debug("setting values=%r, values_dict=%r",
                                      Attributes.values, Attributes.values_dict)

            elif k == 'exc_table':
                Attributes.exc_table = v
                Attributes.exc_db = v
                _log_debug("setting exc_table=%r, exc_db=%r", v, v)

            elif k == 'max_occurs' and v in ('unbounded', 'inf', float('inf')):
                new_v = decimal.Decimal('inf')
                setattr(Attributes, k, new_v)
                _log_debug("setting max_occurs=%r", new_v)

            elif k == 'type_name':
                Attributes._explicit_type_name = True
                _log_debug("setting _explicit_type_name=True because "
                                                          "we have 'type_name'")

            else:
                setattr(Attributes, k, v)
                _log_debug("setting %s=%r", k, v)

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

        return (cls.Attributes.nullable or value is not None)


class Null(ModelBase):
    pass


class SimpleModelAttributesMeta(AttributesMeta):
    def __init__(self, cls_name, cls_bases, cls_dict):
        super(SimpleModelAttributesMeta, self).__init__(cls_name, cls_bases,
                                                                       cls_dict)
        if getattr(self, '_pattern', None) is None:
            self._pattern = None

    def get_pattern(self):
        return self._pattern

    def set_pattern(self, pattern):
        self._pattern = pattern
        if pattern is not None:
            self._pattern_re = re.compile(pattern)

    pattern = property(get_pattern, set_pattern)

    def get_unicode_pattern(self):
        return self._pattern

    def set_unicode_pattern(self, pattern):
        self._pattern = pattern
        if pattern is not None:
            self._pattern_re = re.compile(pattern, re.UNICODE)

    unicode_pattern = property(get_unicode_pattern, set_unicode_pattern)
    upattern = property(get_unicode_pattern, set_unicode_pattern)


class SimpleModel(ModelBase):
    """The base class for primitives."""

    __namespace__ = "http://www.w3.org/2001/XMLSchema"

    @six.add_metaclass(SimpleModelAttributesMeta)
    class Attributes(ModelBase.Attributes):
        """The class that holds the constraints for the given type."""

        values = set()
        """The set of possible values for this type."""

        # some hacks are done in _s_customize to make `values_dict`
        # behave like `values`
        values_dict = dict()
        """The dict of possible values for this type. Dict keys are values and
        dict values are either a single string or a translation dict."""

        _pattern_re = None

    def __new__(cls, **kwargs):
        """Overriden so that any attempt to instantiate a primitive will return
        a customized class instead of an instance.

        See spyne.model.base.ModelBase for more information.
        """

        return cls.customize(**kwargs)

    @classmethod
    def customize(cls, **kwargs):
        """Duplicates cls and overwrites the values in ``cls.Attributes`` with
        ``**kwargs`` and returns the new class."""

        cls_name, cls_bases, cls_dict = cls._s_customize(**kwargs)

        retval = type(cls_name, cls_bases, cls_dict)

        if not retval.is_default(retval):
            retval.__extends__ = cls
            retval.__type_name__ = kwargs.get("type_name", ModelBase.Empty)
            if 'type_name' in kwargs:
                logger.debug("Type name for %r was overridden as '%s'",
                                                   retval, retval.__type_name__)

        retval.resolve_namespace(retval, kwargs.get('__namespace__'))

        return retval

    @staticmethod
    def is_default(cls):
        return (cls.Attributes.values == SimpleModel.Attributes.values)

    @staticmethod
    def validate_native(cls, value):
        return (ModelBase.validate_native(cls, value)
                and (
                    cls.Attributes.values is None or
                    len(cls.Attributes.values) == 0 or (
                        (value is None     and cls.Attributes.nillable) or
                        (value is not None and value in cls.Attributes.values)
                    )
                )
            )


class PushBase(object):
    def __init__(self, callback=None, errback=None):
        self.orig_thread = threading.current_thread()

        self._cb = callback
        self._eb = errback

        self.length = 0
        self.ctx = None
        self.app = None
        self.gen = None
        self._cb_finish = None
        self._eb_finish = None
        self.interim = False

    def _init(self, ctx, gen, _cb_finish, _eb_finish, interim):
        self.length = 0

        self.ctx = ctx
        self.app = ctx.app

        self.gen = gen

        self._cb_finish = _cb_finish
        self._eb_finish = _eb_finish

        self.interim = interim

    def init(self, ctx, gen, _cb_finish, _eb_finish, interim):
        self._init(ctx, gen, _cb_finish, _eb_finish, interim)
        if self._cb is not None:
            return self._cb(self)

    def __len__(self):
        return self.length

    def append(self, inst):
        self.gen.send(inst)
        self.length += 1

    def extend(self, insts):
        for inst in insts:
            self.gen.send(inst)
            self.length += 1

    def close(self):
        try:
            self.gen.throw(Break())
        except (Break, StopIteration, GeneratorExit):
            pass
        self._cb_finish()


class xml:
    """Compound option object for xml serialization. It's meant to be passed to
    :func:`ComplexModelBase.Attributes.store_as`.

    :param root_tag: Root tag of the xml element that contains the field values.
    :param no_ns: When true, the xml document is stripped from namespace
        information. This is generally a stupid thing to do. Use with caution.
    """

    def __init__(self, root_tag=None, no_ns=False, pretty_print=False):
        self.root_tag = root_tag
        self.no_ns = no_ns
        self.pretty_print = pretty_print


class table:
    """Compound option object for for storing the class instance as in row in a
    table in a relational database. It's meant to be passed to
    :func:`ComplexModelBase.Attributes.store_as`.

    :param multi: When False, configures a one-to-many relationship where the
        child table has a foreign key to the parent. When not ``False``,
        configures a many-to-many relationship by creating an intermediate
        relation table that has foreign keys to both parent and child classes
        and generates a table name automatically. When ``True``, the table name
        is generated automatically. Otherwise, it should be a string, as the
        value is used as the name of the intermediate table.
    :param left: Name of the left join column.
    :param right: Name of the right join column.
    :param backref: See https://docs.sqlalchemy.org/en/13/orm/relationship_api.html?highlight=lazy#sqlalchemy.orm.relationship.params.backref
    :param cascade: https://docs.sqlalchemy.org/en/13/orm/relationship_api.html?highlight=lazy#sqlalchemy.orm.relationship.params.cascade
    :param lazy: See https://docs.sqlalchemy.org/en/13/orm/relationship_api.html?highlight=lazy#sqlalchemy.orm.relationship.params.lazy
    :param back_populates: See https://docs.sqlalchemy.org/en/13/orm/relationship_api.html?highlight=lazy#sqlalchemy.orm.relationship.params.back_populates
    """

    def __init__(self, multi=False, left=None, right=None, backref=None,
            id_backref=None, cascade=False, lazy='select', back_populates=None,
                       fk_left_deferrable=None, fk_left_initially=None,
                       fk_right_deferrable=None, fk_right_initially=None,
                       fk_left_ondelete=None, fk_left_onupdate=None,
                       fk_right_ondelete=None, fk_right_onupdate=None,
                       explicit_join=False, order_by=False, single_parent=None):
        self.multi = multi
        self.left = left
        self.right = right
        self.backref = backref
        self.id_backref = id_backref
        self.cascade = cascade
        self.lazy = lazy
        self.back_populates = back_populates
        self.fk_left_deferrable = fk_left_deferrable
        self.fk_left_initially = fk_left_initially
        self.fk_right_deferrable = fk_right_deferrable
        self.fk_right_initially = fk_right_initially
        self.fk_left_ondelete = fk_left_ondelete
        self.fk_left_onupdate = fk_left_onupdate
        self.fk_right_ondelete = fk_right_ondelete
        self.fk_right_onupdate = fk_right_onupdate
        self.explicit_join = explicit_join
        self.order_by = order_by
        self.single_parent = single_parent


class json:
    """Compound option object for json serialization. It's meant to be passed to
    :func:`ComplexModelBase.Attributes.store_as`.

    Make sure you don't mix this with the json package when importing.
    """

    def __init__(self, ignore_wrappers=True, complex_as=dict):
        if ignore_wrappers != True:
            raise NotImplementedError("ignore_wrappers != True")
        self.ignore_wrappers = ignore_wrappers
        self.complex_as = complex_as


class jsonb:
    """Compound option object for jsonb serialization. It's meant to be passed
    to :func:`ComplexModelBase.Attributes.store_as`.
    """

    def __init__(self, ignore_wrappers=True, complex_as=dict):
        if ignore_wrappers != True:
            raise NotImplementedError("ignore_wrappers != True")
        self.ignore_wrappers = ignore_wrappers
        self.complex_as = complex_as


class msgpack:
    """Compound option object for msgpack serialization. It's meant to be passed
    to :func:`ComplexModelBase.Attributes.store_as`.

    Make sure you don't mix this with the msgpack package when importing.
    """
    def __init__(self):
        pass


PSSM_VALUES = {'json': json, 'jsonb': jsonb, 'xml': xml,
                                             'msgpack': msgpack, 'table': table}


def apply_pssm(val):
    if val is not None:
        val_c = PSSM_VALUES.get(val, None)
        if val_c is None:
            assert isinstance(val, tuple(PSSM_VALUES.values())), \
             "'store_as' should be one of: %r or an instance of %r not %r" \
             % (tuple(PSSM_VALUES.keys()), tuple(PSSM_VALUES.values()), val)

            return val
        return val_c()
