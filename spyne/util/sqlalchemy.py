
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

"""Just for Postgresql, just for fun. As of yet, at least.

In case it's not obvious, this module is EXPERIMENTAL.
"""

from __future__ import absolute_import

import logging
logger = logging.getLogger(__name__)

try:
    import simplejson as json
except ImportError:
    import json

import sqlalchemy

from inspect import isclass

from lxml import etree

from sqlalchemy import sql
from sqlalchemy import event
from sqlalchemy.schema import Column
from sqlalchemy.schema import Index
from sqlalchemy.schema import Table
from sqlalchemy.schema import ForeignKey
from sqlalchemy.orm import _mapper_registry

from sqlalchemy.dialects.postgresql import FLOAT
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION
from sqlalchemy.dialects.postgresql.base import PGUuid

from sqlalchemy.ext.compiler import compiles

from sqlalchemy.orm import relationship
from sqlalchemy.orm import mapper
from sqlalchemy.orm.util import class_mapper
from sqlalchemy.orm.exc import UnmappedClassError
from sqlalchemy.ext.associationproxy import association_proxy

from sqlalchemy.types import UserDefinedType

# internal types
from spyne.model.enum import EnumBase
from spyne.model.complex import XmlModifier

# Config types
from spyne.model.complex import xml as c_xml
from spyne.model.complex import json as c_json
from spyne.model.complex import table as c_table
from spyne.model.complex import msgpack as c_msgpack

# public types
from spyne.model import SimpleModel
from spyne.model import Enum
from spyne.model import ByteArray
from spyne.model import Array
from spyne.model import ComplexModelBase
from spyne.model import AnyXml
from spyne.model import Uuid
from spyne.model import Date
from spyne.model import Time
from spyne.model import DateTime
from spyne.model import Float
from spyne.model import Double
from spyne.model import Decimal
from spyne.model import String
from spyne.model import Unicode
from spyne.model import Boolean
from spyne.model import Integer
from spyne.model import Integer8
from spyne.model import Integer16
from spyne.model import Integer32
from spyne.model import Integer64
from spyne.model import Point
from spyne.model import Line
from spyne.model import Polygon
from spyne.model import MultiPoint
from spyne.model import MultiLine
from spyne.model import MultiPolygon
from spyne.model import UnsignedInteger
from spyne.model import UnsignedInteger8
from spyne.model import UnsignedInteger16
from spyne.model import UnsignedInteger32
from spyne.model import UnsignedInteger64

from spyne.util import sanitize_args
from spyne.util.xml import get_object_as_xml
from spyne.util.xml import get_xml_as_object
from spyne.util.dictdoc import get_dict_as_object
from spyne.util.dictdoc import get_object_as_json


# Inheritance type constants.
class _SINGLE:
    pass

class _JOINED:
    pass


def own_mapper(cls):
    try:
        return class_mapper(cls)
    except UnmappedClassError:
        return mapper


_sq2sp_type_map = {
    sqlalchemy.Text: String,
    sqlalchemy.String: String,
    sqlalchemy.Unicode: String,
    sqlalchemy.UnicodeText: String,

    sqlalchemy.Float: Float,
    sqlalchemy.Numeric: Decimal,
    sqlalchemy.BigInteger: Integer,
    sqlalchemy.Integer: Integer,
    sqlalchemy.SmallInteger: Integer,

    sqlalchemy.Binary: ByteArray,
    sqlalchemy.LargeBinary: ByteArray,
    sqlalchemy.Boolean: Boolean,
    sqlalchemy.DateTime: DateTime,
    sqlalchemy.Date: Date,
    sqlalchemy.Time: Time,

    PGUuid: Uuid
}


# this needs to be called whenever a new column is instantiated.
def _sp_attrs_to_sqla_constraints(cls, v, col_kwargs=None, col=None):
    # cls is the parent class of v
    if v.Attributes.nullable == False and cls.__extends__ is None:
        if col is None:
            col_kwargs['nullable'] = False
        else:
            col.nullable = False


@compiles(PGUuid, "sqlite")
def compile_uuid_sqlite(type_, compiler, **kw):
    return "BLOB"


class PGGeometry(UserDefinedType):
    """Geometry type for Postgis 2"""

    class PlainWkt:pass
    class PlainWkb:pass

    def __init__(self, geometry_type='GEOMETRY', srid=4326, dimension=2,
                                                                format='wkt'):
        self.geometry_type = geometry_type.upper()
        self.name = 'geometry'
        self.srid = int(srid)
        self.dimension = dimension
        self.format = format

        if self.format == 'wkt':
            self.format = PGGeometry.PlainWkt
        elif self.format == 'wkb':
            self.format = PGGeometry.PlainWkb

    def get_col_spec(self):
        return '%s(%s,%d)' % (self.name, self.geometry_type, self.srid)

    def column_expression(self, col):
        if self.format is PGGeometry.PlainWkb:
            return sql.func.ST_AsBinary(col, type_=self)
        if self.format is PGGeometry.PlainWkt:
            return sql.func.ST_AsText(col, type_=self)

    def result_processor(self, dialect, coltype):
        if self.format is PGGeometry.PlainWkt:
            def process(value):
                if value is not None:
                    return value

        if self.format is PGGeometry.PlainWkb:
            def process(value):
                if value is not None:
                    return sql.func.ST_AsBinary(value, self.srid)

        return process

    def bind_expression(self, bindvalue):
        if self.format is PGGeometry.PlainWkt:
            return sql.func.ST_GeomFromText(bindvalue, self.srid)


Geometry = PGGeometry

@compiles(PGGeometry)
def compile_geometry(type_, compiler, **kw):
    return '%s(%s,%d)' % (type_.name, type_.geometry_type, type_.srid)


@compiles(PGGeometry, "sqlite")
def compile_geometry_sqlite(type_, compiler, **kw):
    return "BLOB"


class PGXml(UserDefinedType):
    def __init__(self, pretty_print=False, xml_declaration=False,
                                                             encoding='UTF-8'):
        self.xml_declaration = xml_declaration
        self.pretty_print = pretty_print
        self.encoding = encoding

    def get_col_spec(self):
        return "xml"

    def bind_processor(self, dialect):
        def process(value):
            if isinstance(value, str) or value is None:
                return value
            else:
                return etree.tostring(value, pretty_print=self.pretty_print,
                                 encoding=self.encoding, xml_declaration=False)
        return process

    def result_processor(self, dialect, col_type):
        def process(value):
            if value is not None:
                return etree.fromstring(value)
            else:
                return value
        return process

sqlalchemy.dialects.postgresql.base.ischema_names['xml'] = PGXml


class PGJson(UserDefinedType):
    def __init__(self, encoding='UTF-8'):
        self.encoding = encoding

    def get_col_spec(self):
        return "json"

    def bind_processor(self, dialect):
        def process(value):
            if isinstance(value, str) or value is None:
                return value
            else:
                return json.dumps(value, encoding=self.encoding)
        return process

    def result_processor(self, dialect, col_type):
        def process(value):
            if value is not None:
                return json.loads(value)
            else:
                return value
        return process

sqlalchemy.dialects.postgresql.base.ischema_names['json'] = PGJson


class PGObjectXml(UserDefinedType):
    def __init__(self, cls, root_tag_name=None, no_namespace=False):
        self.cls = cls
        self.root_tag_name = root_tag_name
        self.no_namespace = no_namespace

    def get_col_spec(self):
        return "xml"

    def bind_processor(self, dialect):
        def process(value):
            return etree.tostring(get_object_as_xml(value, self.cls,
                                        self.root_tag_name, self.no_namespace),
                     pretty_print=False, encoding='utf8', xml_declaration=False)
        return process

    def result_processor(self, dialect, col_type):
        def process(value):
            if value is not None:
                return get_xml_as_object(etree.fromstring(value), self.cls)
        return process


class PGObjectJson(UserDefinedType):
    def __init__(self, cls, ignore_wrappers=True, complex_as=dict):
        self.cls = cls
        self.ignore_wrappers = ignore_wrappers
        self.complex_as = complex_as

    def get_col_spec(self):
        return "json"

    def bind_processor(self, dialect):
        def process(value):
            if value is not None:
                return get_object_as_json(value, self.cls,
                        ignore_wrappers=self.ignore_wrappers,
                        complex_as=self.complex_as,
                    )
        return process

    def result_processor(self, dialect, col_type):
        def process(value):
            if value is not None:
                return get_dict_as_object(json.loads(value), self.cls)

        return process


def get_sqlalchemy_type(cls):
    db_type = cls.Attributes.db_type
    if db_type is not None:
        return db_type

    # must be above Unicode, because Uuid is Unicode's subclass
    if issubclass(cls, Uuid):
        return PGUuid(as_uuid=True)

    # must be above Unicode, because Point is Unicode's subclass
    elif issubclass(cls, Point):
        return PGGeometry("POINT", dimension=cls.Attributes.dim)

    # must be above Unicode, because Line is Unicode's subclass
    elif issubclass(cls, Line):
        return PGGeometry("LINESTRING", dimension=cls.Attributes.dim)

    # must be above Unicode, because Polygon is Unicode's subclass
    elif issubclass(cls, Polygon):
        return PGGeometry("POLYGON", dimension=cls.Attributes.dim)

    # must be above Unicode, because MultiPoint is Unicode's subclass
    elif issubclass(cls, MultiPoint):
        return PGGeometry("MULTIPOINT", dimension=cls.Attributes.dim)

    # must be above Unicode, because MultiLine is Unicode's subclass
    elif issubclass(cls, MultiLine):
        return PGGeometry("MULTILINESTRING", dimension=cls.Attributes.dim)

    # must be above Unicode, because MultiPolygon is Unicode's subclass
    elif issubclass(cls, MultiPolygon):
        return PGGeometry("MULTIPOLYGON", dimension=cls.Attributes.dim)

    # must be above Unicode, because String is Unicode's subclass
    elif issubclass(cls, String):
        if cls.Attributes.max_len == String.Attributes.max_len: # Default is arbitrary-length
            return sqlalchemy.Text
        else:
            return sqlalchemy.String(cls.Attributes.max_len)

    elif issubclass(cls, Unicode):
        if cls.Attributes.max_len == Unicode.Attributes.max_len: # Default is arbitrary-length
            return sqlalchemy.UnicodeText
        else:
            return sqlalchemy.Unicode(cls.Attributes.max_len)

    elif issubclass(cls, EnumBase):
        return sqlalchemy.Enum(*cls.__values__, name=cls.__type_name__)

    elif issubclass(cls, AnyXml):
        return PGXml

    elif issubclass(cls, ByteArray):
        return sqlalchemy.LargeBinary

    elif issubclass(cls, (Integer64, UnsignedInteger64)):
        return sqlalchemy.BigInteger

    elif issubclass(cls, (Integer32, UnsignedInteger32)):
        return sqlalchemy.Integer

    elif issubclass(cls, (Integer16, UnsignedInteger16)):
        return sqlalchemy.SmallInteger

    elif issubclass(cls, (Integer8, UnsignedInteger8)):
        return sqlalchemy.SmallInteger

    elif issubclass(cls, Float):
        return FLOAT

    elif issubclass(cls, Double):
        return DOUBLE_PRECISION

    elif issubclass(cls, (Integer, UnsignedInteger)):
        return sqlalchemy.DECIMAL

    elif issubclass(cls, Decimal):
        return sqlalchemy.DECIMAL

    elif issubclass(cls, Boolean):
        return sqlalchemy.Boolean

    elif issubclass(cls, Date):
        return sqlalchemy.Date

    elif issubclass(cls, DateTime):
        if cls.Attributes.timezone is None:
            if cls.Attributes.as_time_zone is None:
                return sqlalchemy.DateTime(timezone=True)
            else:
                return sqlalchemy.DateTime(timezone=False)
        else:
            return sqlalchemy.DateTime(timezone=cls.Attributes.timezone)

    elif issubclass(cls, Time):
        return sqlalchemy.Time

    elif issubclass(cls, XmlModifier):
        retval = get_sqlalchemy_type(cls.type)
        return retval


def get_pk_columns(cls):
    """Return primary key fields of a Spyne object."""

    retval = []
    for k, v in cls.get_flat_type_info(cls).items():
        if v.Attributes.sqla_column_args is not None and \
                    v.Attributes.sqla_column_args[-1].get('primary_key', False):
            retval.append((k,v))

    return tuple(retval) if len(retval) > 0 else None


def _get_col_o2o(parent, k, v, fk_col_name):
    """Gets key and child type and returns a column that points to the primary
    key of the child.
    """

    assert v.Attributes.table_name is not None, "%r has no table name." % v

    col_args, col_kwargs = sanitize_args(v.Attributes.sqla_column_args)
    _sp_attrs_to_sqla_constraints(parent, v, col_kwargs)

    # get pkeys from child class
    pk_column, = get_pk_columns(v) # FIXME: Support multi-col keys

    pk_key, pk_spyne_type = pk_column
    pk_sqla_type = get_sqlalchemy_type(pk_spyne_type)

    # generate a fk to it from the current object (cls)
    if fk_col_name is None:
        fk_col_name = k + "_" + pk_key

    fk = ForeignKey('%s.%s' % (v.Attributes.table_name, pk_key), use_alter=True,
          name='%s_%s_fkey' % (v.Attributes.table_name, fk_col_name))

    return Column(fk_col_name, pk_sqla_type, fk, *col_args, **col_kwargs)


def _get_col_o2m(cls, fk_col_name):
    """Gets the parent class and returns a column that points to the primary key
    of the parent.

    Funky implementation. Yes.
    """

    assert cls.Attributes.table_name is not None, "%r has no table name." % cls
    col_args, col_kwargs = sanitize_args(cls.Attributes.sqla_column_args)

    # get pkeys from current class
    pk_column, = get_pk_columns(cls) # FIXME: Support multi-col keys

    pk_key, pk_spyne_type = pk_column
    pk_sqla_type = get_sqlalchemy_type(pk_spyne_type)

    # generate a fk from child to the current class
    if fk_col_name is None:
        fk_col_name = '_'.join([cls.Attributes.table_name, pk_key])

    # we jump through all these hoops because we must instantiate the Column
    # only after we're sure that it doesn't already exist and also because
    # tinkering with functors is always fun :)
    yield [(fk_col_name, pk_sqla_type)]

    col = Column(fk_col_name, pk_sqla_type,
                ForeignKey('%s.%s' % (cls.Attributes.table_name, pk_key)),
                                                       *col_args, **col_kwargs)

    yield col


def _get_cols_m2m(cls, k, child, left_fk_col_name, right_fk_col_name):
    """Gets the parent and child classes and returns foreign keys to both
    tables. These columns can be used to create a relation table."""

    col_info, left_col = _get_col_o2m(cls, left_fk_col_name)
    right_col = _get_col_o2o(cls, k, child, right_fk_col_name)
    left_col.primary_key = right_col.primary_key = True
    return left_col, right_col


class _FakeTable(object):
    def __init__(self):
        self.c = {}
        self.columns = []
        self.indexes = []

    def append_column(self, col):
        self.columns.append(col)
        self.c[col.name] = col


def _gen_index_info(table, table_name, col, k, v):
    unique = v.Attributes.unique
    index = v.Attributes.index
    if unique and not index:
        index = True

    try:
        index_name, index_method = v.Attributes.index

    except (TypeError, ValueError):
        index_name = "%s_%s%s" % (table_name, k, '_unique' if unique else '')
        index_method = v.Attributes.index

    if index in (False, None):
        pass

    else:
        if index == True:
            index_args = (index_name, col), dict(unique=unique)
        else:
            index_args = (index_name, col), dict(unique=unique,
                                      postgresql_using=index_method)

        if isinstance(table, _FakeTable):
            table.indexes.append(index_args)
        else:
            Index(*index_args[0], **index_args[1])

def _check_inheritance(cls, cls_bases):
    table_name = cls.Attributes.table_name

    inc = []
    inheritance = None
    base_class = getattr(cls, '__extends__', None)

    if base_class is None:
        for b in cls_bases:
            if getattr(b, '_type_info', None) is not None and b.__mixin__:
                base_class = b

    if base_class is not None:
        base_table_name = base_class.Attributes.table_name
        if base_table_name is not None:
            if base_table_name == table_name:
                inheritance = _SINGLE
            else:
                inheritance = _JOINED
                raise NotImplementedError("Joined table inheritance is not yet "
                                          "implemented.")
            inc_prop = base_class.Attributes.sqla_mapper.include_properties
            if inc_prop is not None:
                inc.extend(inc_prop)

            exc_prop = base_class.Attributes.sqla_mapper.exclude_properties
            if exc_prop is not None:
                inc = [_p for _p in inc if not _p in exc_prop]

    # check whether the base classes are already mapped
    base_mapper = None
    if base_class is not None:
        base_mapper = base_class.Attributes.sqla_mapper

    if base_mapper is None:
        for b in cls_bases:
            bm = _mapper_registry.get(b, None)
            if bm is not None:
                assert base_mapper is None, "There can be only one base mapper."
                base_mapper = bm
                inheritance = _SINGLE

    return inheritance, base_class, base_mapper, inc

def _check_table(cls):
    table_name = cls.Attributes.table_name
    metadata = cls.Attributes.sqla_metadata

    # check whether the object already has a table
    table = None
    if table_name in metadata.tables:
        table = metadata.tables[table_name]
    else:
        # We need FakeTable because table_args can contain all sorts of stuff
        # that can require a fully-constructed table, and we don't have that
        # information here yet.
        table = _FakeTable()

    return table


def table_fields(cls):
    for k, v in cls._type_info.items():
        if not v.Attributes.exc_table:
            yield k, v


def _add_simple_type(cls, props, table, k, v, sqla_type):
    col_args, col_kwargs = sanitize_args(v.Attributes.sqla_column_args)
    _sp_attrs_to_sqla_constraints(cls, v, col_kwargs)

    table_name = cls.Attributes.table_name

    if k in table.c:
        col = table.c[k]

    else:
        col = Column(k, sqla_type, *col_args, **col_kwargs)
        table.append_column(col)
        _gen_index_info(table, table_name, col, k, v)

    if not v.Attributes.exc_mapper:
        props[k] = col

def _gen_array_m2m(cls, props, k, child, p):
    metadata = cls.Attributes.sqla_metadata

    col_own, col_child = _get_cols_m2m(cls, k, child, p.left, p.right)

    p.left = col_own.key
    p.right = col_child.key

    if p.multi == True:
        rel_table_name = '_'.join([cls.Attributes.table_name, k])
    else:
        rel_table_name = p.multi

    # FIXME: Handle the case where the table already exists.
    rel_t = Table(rel_table_name, metadata, *(col_own, col_child))

    props[k] = relationship(child, secondary=rel_t,
              backref=p.backref, cascade=p.cascade, lazy=p.lazy)

def _gen_array_simple(cls, props, k, child_cust, p):
    table_name = cls.Attributes.table_name
    metadata = cls.Attributes.sqla_metadata

    # get left (fk) column info
    _gen_col = _get_col_o2m(cls, p.left)
    col_info = _gen_col.next() # gets the column name
    p.left, child_left_col_type = col_info[0] # FIXME: Add support for multi-column primary keys.
    child_left_col_name = p.left

    # get right(data) column info
    child_right_col_type = get_sqlalchemy_type(child_cust)
    child_right_col_name = p.right # this is the data column
    if child_right_col_name is None:
        child_right_col_name = k

    # get table name
    child_table_name = child_cust.Attributes.table_name
    if child_table_name is None:
        child_table_name = '_'.join([table_name, k])

    if child_table_name in metadata.tables:
        child_t = metadata.tables[child_table_name]
        assert child_right_col_type is \
               child_t.c[child_right_col_name].type.__class__
        assert child_left_col_type is \
               child_t.c[child_left_col_name].type.__class__

    else:
        # table does not exist, generate table
        child_right_col = Column(child_right_col_name,
                                        child_right_col_type)
        _sp_attrs_to_sqla_constraints(cls, child_cust,
                                            col=child_right_col)

        child_left_col = _gen_col.next()
        _sp_attrs_to_sqla_constraints(cls, child_cust,
                                            col=child_left_col)

        child_t = Table(child_table_name , metadata,
            Column('id', sqlalchemy.Integer, primary_key=True),
                                child_left_col, child_right_col)

    # generate temporary class for association proxy
    cls_name = ''.join(x.capitalize() or '_' for x in
                                    child_table_name.split('_'))
                            # generates camelcase class name.

    def _i(self, *args):
        setattr(self, child_right_col_name, args[0])

    cls_ = type("_" + cls_name, (object,), {'__init__': _i})
    own_mapper(cls_)(cls_, child_t)
    props["_" + k] = relationship(cls_)

    # generate association proxy
    setattr(cls, k, association_proxy("_" + k, child_right_col_name))


def _gen_array_o2m(cls, props, k, child, child_cust, p):
    _gen_col = _get_col_o2m(cls, p.right)
    col_info = _gen_col.next() # gets the column name
    p.right, col_type = col_info[0] # FIXME: Add support for multi-column primary keys.

    assert p.left is None, \
        "'left' is ignored in one-to-many relationships " \
        "with complex types (because they already have a " \
        "table). You probably meant to use 'right'."

    child_t = child.__table__

    if p.right in child_t.c:
        # FIXME: This branch MUST be tested.
        assert col_type is child_t.c[p.right].type.__class__

        # if the column is there, the decision about whether
        # it should be in child's mapper should also have been
        # made.
        #
        # so, not adding the child column to to child mapper
        # here.
        col = child_t.c[p.right]

    else:
        col = _gen_col.next()

        _sp_attrs_to_sqla_constraints(cls, child_cust, col=col)

        child_t.append_column(col)
        child.__mapper__.add_property(col.name, col)

    props[k] = relationship(child, foreign_keys=[col],
              backref=p.backref, cascade=p.cascade, lazy=p.lazy)

def _is_array(v):
    return (v.Attributes.max_occurs > 1 or issubclass(v, Array))

def _add_complex_type(cls, props, table, k, v):
    p = getattr(v.Attributes, 'store_as', None)
    table_name = cls.Attributes.table_name
    col_args, col_kwargs = sanitize_args(v.Attributes.sqla_column_args)
    _sp_attrs_to_sqla_constraints(cls, v, col_kwargs)
    col = None

    if isinstance(p, c_table):
        if _is_array(v):
            child_cust = v
            if issubclass(v, Array):
                child_cust, = v._type_info.values()

            child = child_cust
            if child_cust.__orig__ is not None:
                child = child_cust.__orig__

            if p.multi != False: # many to many
                _gen_array_m2m(cls, props, k, child, p)

            elif issubclass(child, SimpleModel): # one to many simple type
                _gen_array_simple(cls, props, k, child_cust, p)

            else: # one to many complex type
                _gen_array_o2m(cls, props, k, child, child_cust, p)

        else:
            # v has the Attribute values we need whereas real_v is what the
            # user instantiates (thus what sqlalchemy needs)
            if v.__orig__ is None: # vanilla class
                real_v = v
            else: # customized class
                real_v = v.__orig__

            assert not getattr(p, 'multi', False), (
                                'Storing a single element-type using a '
                                'relation table is pointless.')

            assert p.right is None, "'right' is ignored in a one-to-one " \
                                    "relationship"

            col = _get_col_o2o(cls, k, v, p.left)
            rel = relationship(real_v, uselist=False, cascade=p.cascade,
                     foreign_keys=[col], backref=p.backref, lazy=p.lazy)

            p.left = col.key
            props[k] = rel
            _gen_index_info(table, table_name, col, k, v)

    elif isinstance(p, c_xml):
        if k in table.c:
            col = table.c[k]
        else:
            t = PGObjectXml(v, p.root_tag, p.no_ns)
            col = Column(k, t, *col_args, **col_kwargs)

    elif isinstance(p, c_json):
        if k in table.c:
            col = table.c[k]
        else:
            t = PGObjectJson(v, ignore_wrappers=p.ignore_wrappers,
                                                    complex_as=p.complex_as)
            col = Column(k, t, *col_args, **col_kwargs)

    elif isinstance(p, c_msgpack):
        raise NotImplementedError(c_msgpack)

    elif p is None:
        pass

    else:
        raise ValueError(p)

    if col is not None:
        props[col.name] = col
        if not k in table.c:
            table.append_column(col)


def _convert_fake_table(cls, table):
    metadata = cls.Attributes.sqla_metadata
    table_name = cls.Attributes.table_name

    _table = table
    table_args, table_kwargs = sanitize_args(cls.Attributes.sqla_table_args)
    table = Table(table_name, metadata,
                       *(tuple(table.columns) + table_args), **table_kwargs)

    for index_args, index_kwargs in _table.indexes:
        Index(*index_args, **index_kwargs)

    return table


def _gen_mapper(cls, props, table, cls_bases):
    """
    :param cls: La Class.
    :param props: a dict.
    :param table: a Table instance. Not a _FakeTable.
    :param cls_bases: Class bases.
    """

    inheritance, base_class, base_mapper, inc = _check_inheritance(cls, cls_bases)
    mapper_args, mapper_kwargs = sanitize_args(cls.Attributes.sqla_mapper_args)

    _props = mapper_kwargs.get('properties', None)
    if _props is None:
        mapper_kwargs['properties'] = props
    else:
        props.update(_props)
        mapper_kwargs['properties'] = props

    _inc = mapper_kwargs.get('include_properties', None)
    if _inc is None:
        mapper_kwargs['include_properties'] = inc + props.keys()

    po = mapper_kwargs.get('polymorphic_on', None)
    if po is not None:
        if not isinstance(po, Column):
            mapper_kwargs['polymorphic_on'] = table.c[po]
        else:
            del mapper_kwargs['polymorphic_on']

    if base_mapper is not None:
        mapper_kwargs['inherits'] = base_mapper

    if inheritance is not _SINGLE:
        mapper_args = (table,) + mapper_args

    cls_mapper = mapper(cls, *mapper_args, **mapper_kwargs)

    def on_load(target, context):
        d = target.__dict__

        for k, v in cls.get_flat_type_info(cls).items():
            if not k in d:
                if isclass(v) and issubclass(v, ComplexModelBase):
                    pass
                else:
                    d[k] = None

    event.listen(cls, 'load', on_load)

    return cls_mapper


def add_column(cls, k, v):
    """Add field to the given Spyne object also mapped as a SQLAlchemy object
    to a SQLAlchemy table

    :param cls: The class to add the column to.
    :param k: The column name
    :param v: The column type, a ModelBase subclass.
    """

    table = cls.__table__
    mapper_props = {}

    # Add to table
    t = get_sqlalchemy_type(v)
    if t is None: # complex model
        _add_complex_type(cls, mapper_props, table, k, v)
    else:
        _add_simple_type(cls, mapper_props, table, k, v, t)

    # Add to mapper
    mapper = cls.Attributes.sqla_mapper
    for k,v in mapper_props.items():
        mapper.add_property(k, v)


def gen_sqla_info(cls, cls_bases=()):
    """Return SQLAlchemy table object corresponding to the passed Spyne object.
    Also maps given class to the returned table.
    """

    table = _check_table(cls)
    mapper_props = {}

    for k, v in table_fields(cls):
        t = get_sqlalchemy_type(v)

        if t is None: # complex model
            p = getattr(v.Attributes, 'store_as', None)
            if p is None:
                logger.debug("Skipping %s.%s.%s: %r, store_as: %r" % (
                                                cls.get_namespace(),
                                                cls.get_type_name(), k, v, p))
            else:
                _add_complex_type(cls, mapper_props, table, k, v)
        else:
            _add_simple_type(cls, mapper_props, table, k, v, t)

    if isinstance(table, _FakeTable):
        table = _convert_fake_table(cls, table)

    cls_mapper = _gen_mapper(cls, mapper_props, table, cls_bases)

    cls.__tablename__ = cls.Attributes.table_name
    cls.Attributes.sqla_mapper = cls.__mapper__ = cls_mapper
    cls.Attributes.sqla_table = cls.__table__ = table

    return table


def get_spyne_type(v):
    """This function maps sqlalchemy types to spyne types."""

    rpc_type = None

    if isinstance(v.type, sqlalchemy.Enum):
        if v.type.convert_unicode:
            rpc_type = Unicode(values=v.type.enums)
        else:
            rpc_type = Enum(*v.type.enums, **{'type_name': v.type.name})

    elif isinstance(v.type, sqlalchemy.Unicode):
        rpc_type = Unicode(v.type.length)

    elif isinstance(v.type, sqlalchemy.UnicodeText):
        rpc_type = Unicode

    elif isinstance(v.type, sqlalchemy.Text):
        rpc_type = String

    elif isinstance(v.type, sqlalchemy.String):
        rpc_type = String(v.type.length)

    elif isinstance(v.type, (sqlalchemy.Numeric)):
        rpc_type = Decimal(v.type.precision, v.type.scale)

    elif isinstance(v.type, (PGXml)):
        rpc_type = AnyXml

    elif type(v.type) in _sq2sp_type_map:
        rpc_type = _sq2sp_type_map[type(v.type)]

    else:
        raise Exception("Spyne type was not found. Probably _sq2sp_type_map "
                        "needs a new entry. %r" % v)

    return rpc_type


def gen_spyne_info(cls):
    table = cls.Attributes.sqla_table
    _type_info = cls._type_info
    mapper_args, mapper_kwargs = sanitize_args(cls.Attributes.sqla_mapper_args)

    if len(_type_info) == 0:
        for c in table.c:
            _type_info[c.name] = get_spyne_type(c)
    else:
        mapper_kwargs['include_properties'] = _type_info.keys()

    # Map the table to the object
    cls_mapper = own_mapper(cls)(cls, table, *mapper_args, **mapper_kwargs)
    cls.Attributes.table_name = cls.__tablename__ = table.name
    cls.Attributes.sqla_mapper = cls.__mapper__ = cls_mapper
