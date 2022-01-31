
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


from __future__ import absolute_import, print_function

import logging
logger = logging.getLogger(__name__)

import sqlalchemy

try:
    import simplejson as json
except ImportError:
    import json

from os.path import isabs
from inspect import isclass

from sqlalchemy import event
from sqlalchemy.schema import Column
from sqlalchemy.schema import Index
from sqlalchemy.schema import Table
from sqlalchemy.schema import ForeignKey

from sqlalchemy.dialects.postgresql import FLOAT
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION
from sqlalchemy.dialects.postgresql.base import PGUuid, PGInet

from sqlalchemy.orm import relationship
from sqlalchemy.orm import mapper
from sqlalchemy.ext.associationproxy import association_proxy

# TODO: find the latest way of checking whether a class is already mapped
try:
    from sqlalchemy.orm import mapperlib
    _mapper_registries = mapperlib._mapper_registries

except (ImportError, AttributeError):
    from sqlalchemy.orm import _mapper_registry as _mapper_registries

from spyne.store.relational.simple import PGLTree
from spyne.store.relational.document import PGXml, PGObjectXml, PGObjectJson, \
    PGFileJson, PGJsonB, PGHtml, PGJson
from spyne.store.relational.spatial import PGGeometry

# internal types
from spyne.model.enum import EnumBase
from spyne.model.complex import XmlModifier

# Config types
from spyne.model import xml as c_xml
from spyne.model import json as c_json
from spyne.model import jsonb as c_jsonb
from spyne.model import table as c_table
from spyne.model import msgpack as c_msgpack
from spyne.model.binary import HybridFileStore

# public types
from spyne.model import SimpleModel, Enum, Array, ComplexModelBase, \
    Any, AnyDict, AnyXml, AnyHtml, \
    Date, Time, DateTime, Duration, \
    ByteArray, String, Unicode, Uuid, Boolean, \
    Point, Line, Polygon, MultiPoint, MultiLine, MultiPolygon, \
    Float, Double, Decimal, \
    Integer, Integer8, Integer16, Integer32, Integer64, \
    UnsignedInteger, UnsignedInteger8, UnsignedInteger16, UnsignedInteger32, \
                                                            UnsignedInteger64, \
    Ipv6Address, Ipv4Address, IpAddress, \
    File, Ltree

from spyne.util import sanitize_args


# Inheritance type constants.
class _SINGLE:
    pass

class _JOINED:
    pass


_sq2sp_type_map = {
    # we map float => double because sqla doesn't
    # distinguish between floats and doubles.
    sqlalchemy.Float: Double,
    sqlalchemy.FLOAT: Double,

    sqlalchemy.Numeric: Decimal,
    sqlalchemy.NUMERIC: Decimal,

    sqlalchemy.BigInteger: Integer64,
    sqlalchemy.BIGINT: Integer64,

    sqlalchemy.Integer: Integer32,
    sqlalchemy.INTEGER: Integer32,

    sqlalchemy.SmallInteger: Integer16,
    sqlalchemy.SMALLINT: Integer16,

    sqlalchemy.LargeBinary: ByteArray,

    sqlalchemy.Boolean: Boolean,
    sqlalchemy.BOOLEAN: Boolean,

    sqlalchemy.DateTime: DateTime,
    sqlalchemy.TIMESTAMP: DateTime,
    sqlalchemy.dialects.postgresql.base.TIMESTAMP: DateTime,
    sqlalchemy.DATETIME: DateTime,
    sqlalchemy.dialects.postgresql.base.INTERVAL: Duration,

    sqlalchemy.Date: Date,
    sqlalchemy.DATE: Date,

    sqlalchemy.Time: Time,
    sqlalchemy.TIME: Time,

    PGUuid: Uuid,
    PGLTree: Ltree,
    PGInet: IpAddress,
}


sqlalchemy_BINARY = \
    getattr(sqlalchemy, 'Binary', getattr(sqlalchemy, 'BINARY', None))

if sqlalchemy_BINARY is not None:
    _sq2sp_type_map[sqlalchemy_BINARY] = ByteArray


# this needs to be called whenever a new column is instantiated.
def _sp_attrs_to_sqla_constraints(cls, subcls, col_kwargs=None, col=None):
    # cls is the parent class of v
    if subcls.Attributes.nullable == False and cls.__extends__ is None:
        if col is None:
            col_kwargs['nullable'] = False
        else:
            col.nullable = False

    if subcls.Attributes.db_default is not None:
        if col is None:
            col_kwargs['default'] = subcls.Attributes.db_default
        else:
            col.default = subcls.Attributes.db_default


def _get_sqlalchemy_type(cls):
    db_type = cls.Attributes.db_type
    if db_type is not None:
        return db_type

    # must be above Unicode, because Ltree is Unicode's subclass
    if issubclass(cls, Ltree):
        return PGLTree

    # must be above Unicode, because Ip*Address is Unicode's subclass
    if issubclass(cls, (IpAddress, Ipv4Address, Ipv6Address)):
        return PGInet

    # must be above Unicode, because Uuid is Unicode's subclass
    if issubclass(cls, Uuid):
        return PGUuid(as_uuid=True)

    # must be above Unicode, because Point is Unicode's subclass
    if issubclass(cls, Point):
        return PGGeometry("POINT", dimension=cls.Attributes.dim)

    # must be above Unicode, because Line is Unicode's subclass
    if issubclass(cls, Line):
        return PGGeometry("LINESTRING", dimension=cls.Attributes.dim)

    # must be above Unicode, because Polygon is Unicode's subclass
    if issubclass(cls, Polygon):
        return PGGeometry("POLYGON", dimension=cls.Attributes.dim)

    # must be above Unicode, because MultiPoint is Unicode's subclass
    if issubclass(cls, MultiPoint):
        return PGGeometry("MULTIPOINT", dimension=cls.Attributes.dim)

    # must be above Unicode, because MultiLine is Unicode's subclass
    if issubclass(cls, MultiLine):
        return PGGeometry("MULTILINESTRING", dimension=cls.Attributes.dim)

    # must be above Unicode, because MultiPolygon is Unicode's subclass
    if issubclass(cls, MultiPolygon):
        return PGGeometry("MULTIPOLYGON", dimension=cls.Attributes.dim)

    # must be above Unicode, because String is Unicode's subclass
    if issubclass(cls, String):
        if cls.Attributes.max_len == String.Attributes.max_len: # Default is arbitrary-length
            return sqlalchemy.Text
        else:
            return sqlalchemy.String(cls.Attributes.max_len)

    if issubclass(cls, Unicode):
        if cls.Attributes.max_len == Unicode.Attributes.max_len: # Default is arbitrary-length
            return sqlalchemy.UnicodeText
        else:
            return sqlalchemy.Unicode(cls.Attributes.max_len)

    if issubclass(cls, EnumBase):
        return sqlalchemy.Enum(*cls.__values__, name=cls.__type_name__)

    if issubclass(cls, AnyXml):
        return PGXml

    if issubclass(cls, AnyHtml):
        return PGHtml

    if issubclass(cls, (Any, AnyDict)):
        sa = cls.Attributes.store_as
        if sa is None:
            return None
        if isinstance(sa, c_json):
            return PGJson
        if isinstance(sa, c_jsonb):
            return PGJsonB
        raise NotImplementedError(dict(cls=cls, store_as=sa))

    if issubclass(cls, ByteArray):
        return sqlalchemy.LargeBinary

    if issubclass(cls, (Integer64, UnsignedInteger64)):
        return sqlalchemy.BigInteger

    if issubclass(cls, (Integer32, UnsignedInteger32)):
        return sqlalchemy.Integer

    if issubclass(cls, (Integer16, UnsignedInteger16)):
        return sqlalchemy.SmallInteger

    if issubclass(cls, (Integer8, UnsignedInteger8)):
        return sqlalchemy.SmallInteger

    if issubclass(cls, Float):
        return FLOAT

    if issubclass(cls, Double):
        return DOUBLE_PRECISION

    if issubclass(cls, (Integer, UnsignedInteger)):
        return sqlalchemy.DECIMAL

    if issubclass(cls, Decimal):
        return sqlalchemy.DECIMAL

    if issubclass(cls, Boolean):
        if cls.Attributes.store_as is bool:
            return sqlalchemy.Boolean
        if cls.Attributes.store_as is int:
            return sqlalchemy.SmallInteger

        raise ValueError("Boolean.store_as has invalid value %r" %
                                                        cls.Attributes.store_as)

    if issubclass(cls, Date):
        return sqlalchemy.Date

    if issubclass(cls, DateTime):
        if cls.Attributes.timezone is None:
            if cls.Attributes.as_timezone is None:
                return sqlalchemy.DateTime(timezone=True)
            else:
                return sqlalchemy.DateTime(timezone=False)
        else:
            return sqlalchemy.DateTime(timezone=cls.Attributes.timezone)

    if issubclass(cls, Time):
        return sqlalchemy.Time

    if issubclass(cls, Duration):
        return sqlalchemy.dialects.postgresql.base.INTERVAL

    if issubclass(cls, XmlModifier):
        retval = _get_sqlalchemy_type(cls.type)
        return retval


def _get_col_o2o(parent, subname, subcls, fk_col_name, deferrable=None,
                                  initially=None, ondelete=None, onupdate=None):
    """Gets key and child type and returns a column that points to the primary
    key of the child.
    """

    assert subcls.Attributes.table_name is not None, \
                                                "%r has no table name." % subcls

    col_args, col_kwargs = sanitize_args(subcls.Attributes.sqla_column_args)
    _sp_attrs_to_sqla_constraints(parent, subcls, col_kwargs)

    # get pkeys from child class
    pk_column, = get_pk_columns(subcls)  # FIXME: Support multi-col keys

    pk_key, pk_spyne_type = pk_column
    pk_sqla_type = _get_sqlalchemy_type(pk_spyne_type)

    # generate a fk to it from the current object (cls)
    if 'name' in col_kwargs:
        colname = col_kwargs.pop('name')
    else:
        colname = subname

    if fk_col_name is None:
        fk_col_name = colname + "_" + pk_key

    assert fk_col_name != colname, \
        "The column name for the foreign key must be different from the " \
        "column name for the object itself."

    fk = ForeignKey(
        '%s.%s' % (subcls.Attributes.table_name, pk_key),
        use_alter=True,
        name='%s_%s_fkey' % (subcls.Attributes.table_name, fk_col_name),
        deferrable=deferrable, initially=initially,
        ondelete=ondelete, onupdate=onupdate,
    )

    return Column(fk_col_name, pk_sqla_type, fk, **col_kwargs)


def _get_col_o2m(cls, fk_col_name, deferrable=None, initially=None,
                                                  ondelete=None, onupdate=None):
    """Gets the parent class and returns a column that points to the primary key
    of the parent.
    """

    assert cls.Attributes.table_name is not None, "%r has no table name." % cls
    col_args, col_kwargs = sanitize_args(cls.Attributes.sqla_column_args)

    # get pkeys from current class
    pk_column, = get_pk_columns(cls) # FIXME: Support multi-col keys

    pk_key, pk_spyne_type = pk_column
    pk_sqla_type = _get_sqlalchemy_type(pk_spyne_type)

    # generate a fk from child to the current class
    if fk_col_name is None:
        fk_col_name = '_'.join([cls.Attributes.table_name, pk_key])

    # we jump through all these hoops because we must instantiate the Column
    # only after we're sure that it doesn't already exist and also because
    # tinkering with functors is always fun :)
    yield [(fk_col_name, pk_sqla_type)]

    fk = ForeignKey('%s.%s' % (cls.Attributes.table_name, pk_key),
                                     deferrable=deferrable, initially=initially,
                                           ondelete=ondelete, onupdate=onupdate)
    col = Column(fk_col_name, pk_sqla_type, fk, **col_kwargs)

    yield col


def _get_cols_m2m(cls, k, child, fk_left_col_name, fk_right_col_name,
                  fk_left_deferrable, fk_left_initially,
                  fk_right_deferrable, fk_right_initially,
                  fk_left_ondelete, fk_left_onupdate,
                  fk_right_ondelete, fk_right_onupdate):
    """Gets the parent and child classes and returns foreign keys to both
    tables. These columns can be used to create a relation table."""

    col_info, left_col = _get_col_o2m(cls, fk_left_col_name,
                     ondelete=fk_left_ondelete, onupdate=fk_left_onupdate,
                     deferrable=fk_left_deferrable, initially=fk_left_initially)
    right_col = _get_col_o2o(cls, k, child, fk_right_col_name,
                   ondelete=fk_right_ondelete, onupdate=fk_right_onupdate,
                   deferrable=fk_right_deferrable, initially=fk_right_initially)
    left_col.primary_key = right_col.primary_key = True
    return left_col, right_col


class _FakeTable(object):
    def __init__(self, name):
        self.name = name
        self.c = {}
        self.columns = []
        self.indexes = []

    def append_column(self, col):
        self.columns.append(col)
        self.c[col.name] = col


def _gen_index_info(table, col, k, v):
    """
    :param table: sqla table
    :param col: sqla col
    :param k: field name (not necessarily == k)
    :param v: spyne type
    """

    unique = v.Attributes.unique
    index = v.Attributes.index
    if unique and not index:
        index = True

    try:
        index_name, index_method = index

    except (TypeError, ValueError):
        index_name = "%s_%s%s" % (table.name, k, '_unique' if unique else '')
        index_method = index

    if index in (False, None):
        return

    if index is True:
        index_args = (index_name, col), dict(unique=unique)
    else:
        index_args = (index_name, col), dict(unique=unique,
                                                  postgresql_using=index_method)

    if isinstance(table, _FakeTable):
        table.indexes.append(index_args)

    else:
        indexes = dict([(idx.name, idx) for idx in col.table.indexes])
        existing_idx = indexes.get(index_name, None)
        if existing_idx is None:
            Index(*index_args[0], **index_args[1])

        else:
            assert existing_idx.unique == unique, \
                "Uniqueness flag differ between existing and current values. " \
                "Existing: {!r}, New: {!r}".format(existing_idx.unique, unique)

            existing_val = existing_idx.kwargs.get('postgresql_using')

            assert existing_val == index_method, \
                "Indexing methods differ between existing and current index " \
                "directives. Existing: {!r}, New: {!r}".format(
                                                     existing_val, index_method)

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

    # check whether the base classes are already mapped
    base_mapper = None
    if base_class is not None:
        base_mapper = base_class.Attributes.sqla_mapper

    if base_mapper is None:
        for b in cls_bases:
            bm = _mapper_registries.get(b, None)
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
        table = _FakeTable(table_name)

    return table


def _add_simple_type(cls, props, table, subname, subcls, sqla_type):
    col_args, col_kwargs = sanitize_args(subcls.Attributes.sqla_column_args)
    _sp_attrs_to_sqla_constraints(cls, subcls, col_kwargs)

    mp = getattr(subcls.Attributes, 'mapper_property', None)

    if 'name' in col_kwargs:
        colname = col_kwargs.pop('name')
    else:
        colname = subname

    if not subcls.Attributes.exc_db:
        if colname in table.c:
            col = table.c[colname]

        else:
            col = Column(colname, sqla_type, *col_args, **col_kwargs)
            table.append_column(col)
            _gen_index_info(table, col, subname, subcls)

        if not subcls.Attributes.exc_mapper:
            props[subname] = col

    elif mp is not None:
        props[subname] = mp


def _gen_array_m2m(cls, props, subname, arrser, storage):
    """Generates a relational many-to-many array.

    :param cls: The class that owns the field
    :param props: SQLAlchemy Mapper properties
    :param subname: Field name
    :param arrser: Array serializer, ie the __orig__ of the class inside the
                   Array object
    :param storage: The storage configuration object passed to the store_as
    attribute.
    """

    metadata = cls.Attributes.sqla_metadata

    col_own, col_child = _get_cols_m2m(cls, subname, arrser,
                        storage.left, storage.right,
                        storage.fk_left_deferrable, storage.fk_left_initially,
                        storage.fk_right_deferrable, storage.fk_right_initially,
                        storage.fk_left_ondelete, storage.fk_left_onupdate,
                        storage.fk_right_ondelete, storage.fk_right_onupdate)

    storage.left = col_own.key
    storage.right = col_child.key

    # noinspection PySimplifyBooleanCheck because literal True means
    # "generate table name automatically" here
    if storage.multi is True:
        rel_table_name = '_'.join([cls.Attributes.table_name, subname])
    else:
        rel_table_name = storage.multi

    if rel_table_name in metadata.tables:
        rel_t = metadata.tables[rel_table_name]

        col_own_existing = rel_t.c.get(col_own.key, None)
        assert col_own_existing is not None
        if col_own_existing is not None:
            assert col_own.type.__class__ == col_own_existing.type.__class__

        col_child_existing = rel_t.c.get(col_child.key, None)
        if col_child_existing is None:
            rel_t.append_column(col_child)

        else:
            assert col_child.type.__class__ == col_child_existing.type.__class__

    else:
        rel_t = Table(rel_table_name, metadata, *(col_own, col_child))

    own_t = cls.Attributes.sqla_table

    rel_kwargs = dict(
        lazy=storage.lazy,
        backref=storage.backref,
        cascade=storage.cascade,
        order_by=storage.order_by,
        back_populates=storage.back_populates,
    )

    if storage.explicit_join:
        # Specify primaryjoin and secondaryjoin when requested.
        # There are special cases when sqlalchemy can't figure it out by itself.
        # this is where we help it when we can.
        # e.g.: http://sqlalchemy.readthedocs.org/en/rel_1_0/orm/join_conditions.html#self-referential-many-to-many-relationship

        assert own_t is not None and len(get_pk_columns(cls)) > 0

        # FIXME: support more than one pk
        (col_pk_key, _), = get_pk_columns(cls)
        col_pk = own_t.c[col_pk_key]

        rel_kwargs.update(dict(
            secondary=rel_t,
            primaryjoin=(col_pk == rel_t.c[col_own.key]),
            secondaryjoin=(col_pk == rel_t.c[col_child.key]),
        ))

        if storage.single_parent is not None:
            rel_kwargs['single_parent'] = storage.single_parent

        props[subname] = relationship(arrser, **rel_kwargs)

    else:
        rel_kwargs.update(dict(
            secondary=rel_t,
        ))

        if storage.single_parent is not None:
            rel_kwargs['single_parent'] = storage.single_parent

        props[subname] = relationship(arrser, **rel_kwargs)


def _gen_array_simple(cls, props, subname, arrser_cust, storage):
    """Generate an array of simple objects.

    :param cls: The class that owns this field
    :param props: SQLAlchemy Mapper properties
    :param subname: Field name
    :param arrser_cust: Array serializer, ie the class itself inside the Array
                        object
    :param storage: The storage configuration object passed to the store_as
    """

    table_name = cls.Attributes.table_name
    metadata = cls.Attributes.sqla_metadata

    # get left (fk) column info
    _gen_col = _get_col_o2m(cls, storage.left,
        ondelete=storage.fk_left_ondelete, onupdate=storage.fk_left_onupdate,
        deferrable=storage.fk_left_deferrable,
                                          initially=storage.fk_left_initially)

    col_info = next(_gen_col) # gets the column name
    # FIXME: Add support for multi-column primary keys.
    storage.left, child_left_col_type = col_info[0]
    child_left_col_name = storage.left

    # get right(data) column info
    child_right_col_type = _get_sqlalchemy_type(arrser_cust)
    child_right_col_name = storage.right  # this is the data column
    if child_right_col_name is None:
        child_right_col_name = subname

    # get table name
    child_table_name = arrser_cust.Attributes.table_name
    if child_table_name is None:
        child_table_name = '_'.join([table_name, subname])

    if child_table_name in metadata.tables:
        child_t = metadata.tables[child_table_name]

        # if we have the table, make sure have the right column (data column)
        assert child_right_col_type.__class__ is \
           child_t.c[child_right_col_name].type.__class__, "%s.%s: %r != %r" % \
                   (cls, child_right_col_name, child_right_col_type.__class__,
                               child_t.c[child_right_col_name].type.__class__)

        if child_left_col_name in child_t.c:
            assert child_left_col_type is \
                child_t.c[child_left_col_name].type.__class__, "%r != %r" % \
                   (child_left_col_type,
                               child_t.c[child_left_col_name].type.__class__)
        else:
            # Table exists but our own foreign key doesn't.
            child_left_col = next(_gen_col)
            _sp_attrs_to_sqla_constraints(cls, arrser_cust, col=child_left_col)
            child_t.append_column(child_left_col)

    else:
        # table does not exist, generate table
        child_right_col = Column(child_right_col_name, child_right_col_type)
        _sp_attrs_to_sqla_constraints(cls, arrser_cust, col=child_right_col)

        child_left_col = next(_gen_col)
        _sp_attrs_to_sqla_constraints(cls, arrser_cust, col=child_left_col)

        child_t = Table(child_table_name , metadata,
            Column('id', sqlalchemy.Integer, primary_key=True),
            child_left_col,
            child_right_col,
        )
        _gen_index_info(child_t, child_right_col, child_right_col_name,
                                                                    arrser_cust)

    # generate temporary class for association proxy
    cls_name = ''.join(x.capitalize() or '_' for x in
                                                child_table_name.split('_'))
                                                # generates camelcase class name.

    def _i(self, *args):
        setattr(self, child_right_col_name, args[0])

    cls_ = type("_" + cls_name, (object,), {'__init__': _i})
    mapper(cls_, child_t)
    props["_" + subname] = relationship(cls_)

    # generate association proxy
    setattr(cls, subname,
                         association_proxy("_" + subname, child_right_col_name))


def _gen_array_o2m(cls, props, subname, arrser, arrser_cust, storage):
    _gen_col = _get_col_o2m(cls, storage.right,
        ondelete=storage.fk_right_ondelete, onupdate=storage.fk_right_onupdate,
        deferrable=storage.fk_right_deferrable,
                                           initially=storage.fk_right_initially)

    col_info = next(_gen_col)  # gets the column name
    storage.right, col_type = col_info[0]  # FIXME: Add support for multi-column primary keys.

    assert storage.left is None, \
        "'left' is ignored in one-to-many relationships " \
        "with complex types (because they already have a " \
        "table). You probably meant to use 'right'."

    child_t = arrser.__table__

    if storage.right in child_t.c:
        # TODO: This branch MUST be tested.
        new_col_type = child_t.c[storage.right].type.__class__
        assert col_type is child_t.c[storage.right].type.__class__, \
                "Existing column type %r disagrees with new column type %r" % \
                                                        (col_type, new_col_type)

        # if the column is already there, the decision about whether
        # it should be in child's mapper or not should also have been
        # made.
        #
        # so, not adding the child column to to child mapper
        # here.
        col = child_t.c[storage.right]

    else:
        col = next(_gen_col)

        _sp_attrs_to_sqla_constraints(cls, arrser_cust, col=col)

        child_t.append_column(col)
        arrser.__mapper__.add_property(col.name, col)


    rel_kwargs = dict(
        lazy=storage.lazy,
        backref=storage.backref,
        cascade=storage.cascade,
        order_by=storage.order_by,
        foreign_keys=[col],
        back_populates=storage.back_populates,
    )

    if storage.single_parent is not None:
        rel_kwargs['single_parent'] = storage.single_parent

    props[subname] = relationship(arrser, **rel_kwargs)


def _is_array(v):
    return v.Attributes.max_occurs > 1 or issubclass(v, Array)


def _add_array_to_complex(cls, props, subname, subcls, storage):
    arrser_cust = subcls
    if issubclass(subcls, Array):
        arrser_cust, = subcls._type_info.values()

    arrser = arrser_cust
    if arrser_cust.__orig__ is not None:
        arrser = arrser_cust.__orig__

    if storage.multi != False:  # many to many
        _gen_array_m2m(cls, props, subname, arrser, storage)

    elif issubclass(arrser, SimpleModel):  # one to many simple type
        _gen_array_simple(cls, props, subname, arrser_cust, storage)

    else:  # one to many complex type
        _gen_array_o2m(cls, props, subname, arrser, arrser_cust, storage)


def _add_simple_type_to_complex(cls, props, table, subname, subcls, storage,
                                                                    col_kwargs):
    # v has the Attribute values we need whereas real_v is what the
    # user instantiates (thus what sqlalchemy needs)
    if subcls.__orig__ is None:  # vanilla class
        real_v = subcls
    else:  # customized class
        real_v = subcls.__orig__

    assert not getattr(storage, 'multi', False), \
            'Storing a single element-type using a relation table is pointless.'

    assert storage.right is None, \
                               "'right' is ignored in a one-to-one relationship"

    col = _get_col_o2o(cls, subname, subcls, storage.left,
        ondelete=storage.fk_left_ondelete, onupdate=storage.fk_left_onupdate,
        deferrable=storage.fk_left_deferrable,
                                            initially=storage.fk_left_initially)

    storage.left = col.name

    if col.name in table.c:
        col = table.c[col.name]
        if col_kwargs.get('nullable') is False:
            col.nullable = False
    else:
        table.append_column(col)

    rel_kwargs = dict(
        lazy=storage.lazy,
        backref=storage.backref,
        order_by=storage.order_by,
        back_populates=storage.back_populates,
    )

    if storage.single_parent is not None:
        rel_kwargs['single_parent'] = storage.single_parent

    if real_v is (cls.__orig__ or cls):
        (pk_col_name, pk_col_type), = get_pk_columns(cls)
        rel_kwargs['remote_side'] = [table.c[pk_col_name]]

    rel = relationship(real_v, uselist=False, foreign_keys=[col],
        **rel_kwargs)

    _gen_index_info(table, col, subname, subcls)

    props[subname] = rel
    props[col.name] = col


def _add_complex_type_as_table(cls, props, table, subname, subcls, storage,
                                                          col_args, col_kwargs):
    # add one to many relation
    if _is_array(subcls):
        _add_array_to_complex(cls, props, subname, subcls, storage)

    # add one to one relation
    else:
        _add_simple_type_to_complex(cls, props, table, subname, subcls,
                                                            storage, col_kwargs)


def _add_complex_type_as_xml(cls, props, table, subname, subcls, storage,
                                                          col_args, col_kwargs):
    if 'name' in col_kwargs:
        colname = col_kwargs.pop('name')
    else:
        colname = subname

    if colname in table.c:
        col = table.c[colname]
    else:
        t = PGObjectXml(subcls, storage.root_tag, storage.no_ns,
                                                           storage.pretty_print)
        col = Column(colname, t, **col_kwargs)

    props[subname] = col
    if not subname in table.c:
        table.append_column(col)


def _add_complex_type_as_json(cls, props, table, subname, subcls, storage,
                                                     col_args, col_kwargs, dbt):
    if 'name' in col_kwargs:
        colname = col_kwargs.pop('name')
    else:
        colname = subname

    if colname in table.c:
        col = table.c[colname]

    else:
        t = PGObjectJson(subcls, ignore_wrappers=storage.ignore_wrappers,
                                         complex_as=storage.complex_as, dbt=dbt)
        col = Column(colname, t, **col_kwargs)

    props[subname] = col
    if not subname in table.c:
        table.append_column(col)


def _add_complex_type(cls, props, table, subname, subcls):
    if issubclass(subcls, File):
        return _add_file_type(cls, props, table, subname, subcls)

    storage = getattr(subcls.Attributes, 'store_as', None)
    col_args, col_kwargs = sanitize_args(subcls.Attributes.sqla_column_args)
    _sp_attrs_to_sqla_constraints(cls, subcls, col_kwargs)

    if isinstance(storage, c_table):
        return _add_complex_type_as_table(cls, props, table, subname, subcls,
                                                  storage, col_args, col_kwargs)
    if isinstance(storage, c_xml):
        return _add_complex_type_as_xml(cls, props, table, subname, subcls,
                                                  storage, col_args, col_kwargs)
    if isinstance(storage, c_json):
        return _add_complex_type_as_json(cls, props, table, subname, subcls,
                                         storage, col_args, col_kwargs, 'json')
    if isinstance(storage, c_jsonb):
        return _add_complex_type_as_json(cls, props, table, subname, subcls,
                                         storage, col_args, col_kwargs, 'jsonb')
    if isinstance(storage, c_msgpack):
        raise NotImplementedError(c_msgpack)

    if storage is None:
        return

    raise ValueError(storage)


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
    """Generate SQLAlchemy mapper from Spyne definition data.

    :param cls: La Class.
    :param props: Dict of properties for SQLAlchemt'y Mapper call.
    :param table: A Table instance. Not a `_FakeTable` or anything.
    :param cls_bases: Sequence of class bases.
    """

    inheritance, base_class, base_mapper, inc = _check_inheritance(cls, cls_bases)
    mapper_args, mapper_kwargs = sanitize_args(cls.Attributes.sqla_mapper_args)

    _props = mapper_kwargs.get('properties', None)
    if _props is None:
        mapper_kwargs['properties'] = props
    else:
        props.update(_props)
        mapper_kwargs['properties'] = props

    po = mapper_kwargs.get('polymorphic_on', None)
    if po is not None:
        if not isinstance(po, Column):
            mapper_kwargs['polymorphic_on'] = table.c[po]
        else:
            logger.warning("Deleted invalid 'polymorphic_on' value %r for %r.",
                                                                        po, cls)
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


def _add_file_type(cls, props, table, subname, subcls):
    storage = getattr(subcls.Attributes, 'store_as', None)
    col_args, col_kwargs = sanitize_args(subcls.Attributes.sqla_column_args)
    _sp_attrs_to_sqla_constraints(cls, subcls, col_kwargs)

    if isinstance(storage, HybridFileStore):
        if subname in table.c:
            col = table.c[subname]

        else:
            assert isabs(storage.store)
            #FIXME: Add support for storage markers from spyne.model.complex
            if storage.db_format == 'json':
                t = PGFileJson(storage.store, storage.type)

            elif storage.db_format == 'jsonb':
                t = PGFileJson(storage.store, storage.type, dbt='jsonb')

            else:
                raise NotImplementedError(storage.db_format)

            col = Column(subname, t, **col_kwargs)

        props[subname] = col
        if not subname in table.c:
            table.append_column(col)

    else:
        raise NotImplementedError(storage)


def add_column(cls, subname, subcls):
    """Add field to the given Spyne object also mapped as a SQLAlchemy object
    to a SQLAlchemy table

    :param cls: The class to add the column to.
    :param subname: The column name
    :param subcls: The column type, a ModelBase subclass.
    """

    table = cls.__table__
    mapper_props = {}

    # Add to table
    sqla_type = _get_sqlalchemy_type(subcls)
    if sqla_type is None:  # complex model
        _add_complex_type(cls, mapper_props, table, subname, subcls)
    else:
        _add_simple_type(cls, mapper_props, table, subname, subcls, sqla_type)

    # Add to mapper
    sqla_mapper = cls.Attributes.sqla_mapper
    for subname, subcls in mapper_props.items():
        if not sqla_mapper.has_property(subname):
            sqla_mapper.add_property(subname, subcls)


def _parent_mapper_has_property(cls, cls_bases, k):
    if len(cls_bases) == 0 and cls.__orig__ is cls_bases[0]:
        return False

    for b in cls_bases:
        if not hasattr(b, 'Attributes'):
            continue

        mapper = b.Attributes.sqla_mapper
        if mapper is not None and mapper.has_property(k):
            # print("    Skipping mapping field", "%s.%s" % (cls.__name__, k),
            #          "because parent mapper from", b.__name__, "already has it")
            return True

    # print("NOT skipping mapping field", "%s.%s" % (cls.__name__, k))
    return False


def gen_sqla_info(cls, cls_bases=()):
    """Return SQLAlchemy table object corresponding to the passed Spyne object.
    Also maps given class to the returned table.
    """

    table = _check_table(cls)
    mapper_props = {}

    ancestors = cls.ancestors()
    if len(ancestors) > 0:
        anc_mapper = ancestors[0].Attributes.sqla_mapper
        if anc_mapper is None:
            # no mapper in parent, use all fields
            fields = cls.get_flat_type_info(cls).items()

        elif anc_mapper.concrete:
            # there is mapper in parent and it's concrete, so use all fields
            fields = cls.get_flat_type_info(cls).items()

        else:
            # there is a mapper in parent and it's not concrete, so parent
            # columns are already mapped, so use only own fields.
            fields = cls._type_info.items()

    else:
        # when no parents, use all fields anyway.
        assert set(cls._type_info.items()) == \
               set(cls.get_flat_type_info(cls).items())

        fields = cls.get_flat_type_info(cls).items()

    for k, v in fields:
        if _parent_mapper_has_property(cls, cls_bases, k):
            continue

        t = _get_sqlalchemy_type(v)

        if t is None:  # complex model
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


def _get_spyne_type(v):
    """Map sqlalchemy types to spyne types."""

    cust = {}
    if v.primary_key:
        cust['primary_key'] = True

    if not v.nullable:
        cust['nullable'] = False
        cust['min_occurs'] = 1

    if isinstance(v.type, sqlalchemy.Enum):
        if v.type.convert_unicode:
            return Unicode(values=v.type.enums, **cust)
        else:
            cust['type_name'] = v.type.name
            return Enum(*v.type.enums, **cust)

    if isinstance(v.type, (sqlalchemy.UnicodeText, sqlalchemy.Text)):
        return Unicode(**cust)

    if isinstance(v.type, (sqlalchemy.Unicode, sqlalchemy.String,
                                                           sqlalchemy.VARCHAR)):
        return Unicode(v.type.length, **cust)

    if isinstance(v.type, sqlalchemy.Numeric):
        return Decimal(v.type.precision, v.type.scale, **cust)

    if isinstance(v.type, PGXml):
        if len(cust) > 0:
            return AnyXml(**cust)
        else:
            return AnyXml

    if isinstance(v.type, PGHtml):
        if len(cust) > 0:
            return AnyHtml(**cust)
        else:
            return AnyHtml

    if type(v.type) in _sq2sp_type_map:
        retval = _sq2sp_type_map[type(v.type)]
        if len(cust) > 0:
            return retval.customize(**cust)
        else:
            return retval

    if isinstance(v.type, (PGObjectJson, PGObjectXml)):
        retval = v.type.cls
        if len(cust) > 0:
            return retval.customize(**cust)
        else:
            return retval

    if isinstance(v.type, PGFileJson):
        retval = v.FileData
        if len(cust) > 0:
            return v.FileData.customize(**cust)
        else:
            return retval

    raise Exception("Spyne type was not found. Probably _sq2sp_type_map "
                                                    "needs a new entry. %r" % v)


def gen_spyne_info(cls):
    table = cls.Attributes.sqla_table
    _type_info = cls._type_info
    mapper_args, mapper_kwargs = sanitize_args(cls.Attributes.sqla_mapper_args)

    if len(_type_info) == 0:
        for c in table.c:
            _type_info[c.name] = _get_spyne_type(c)
    else:
        mapper_kwargs['include_properties'] = _type_info.keys()

    # Map the table to the object
    cls_mapper = mapper(cls, table, *mapper_args, **mapper_kwargs)

    cls.Attributes.table_name = cls.__tablename__ = table.name
    cls.Attributes.sqla_mapper = cls.__mapper__ = cls_mapper


def get_pk_columns(cls):
    """Return primary key fields of a Spyne object."""

    retval = []
    for k, v in cls.get_flat_type_info(cls).items():
        if v.Attributes.sqla_column_args is not None and \
                    v.Attributes.sqla_column_args[-1].get('primary_key', False):
            retval.append((k, v))

    return tuple(retval) if len(retval) > 0 else None
