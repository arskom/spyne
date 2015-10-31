
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
from sqlalchemy.orm import _mapper_registry

from sqlalchemy.dialects.postgresql import FLOAT
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION
from sqlalchemy.dialects.postgresql.base import PGUuid, PGInet

from sqlalchemy.orm import relationship
from sqlalchemy.orm import mapper
from sqlalchemy.ext.associationproxy import association_proxy

from spyne.store.relational.simple import PGLTree
from spyne.store.relational.document import PGXml, PGObjectXml, PGObjectJson, \
    PGFileJson
from spyne.store.relational.document import PGHtml
from spyne.store.relational.document import PGJson
from spyne.store.relational.spatial import PGGeometry

# internal types
from spyne.model.enum import EnumBase
from spyne.model.complex import XmlModifier

# Config types
from spyne.model.complex import xml as c_xml
from spyne.model.complex import json as c_json
from spyne.model.complex import table as c_table
from spyne.model.complex import msgpack as c_msgpack
from spyne.model.binary import HybridFileStore

# public types
from spyne.model import SimpleModel, AnyDict, Enum, ByteArray, Array, \
    ComplexModelBase, AnyXml, AnyHtml, Uuid, Date, Time, DateTime, Float, \
    Double, Decimal, String, Unicode, Boolean, Integer, Integer8, Integer16, \
    Integer32, Integer64, Point, Line, Polygon, MultiPoint, MultiLine, \
    MultiPolygon, UnsignedInteger, UnsignedInteger8, UnsignedInteger16, \
    UnsignedInteger32, UnsignedInteger64, File, Ltree, Ipv6Address, Ipv4Address, \
    IpAddress

from spyne.util import sanitize_args


# Inheritance type constants.
class _SINGLE:
    pass

class _JOINED:
    pass


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

    PGUuid: Uuid,
    PGLTree: Ltree,
}


# this needs to be called whenever a new column is instantiated.
def _sp_attrs_to_sqla_constraints(cls, v, col_kwargs=None, col=None):
    # cls is the parent class of v
    if v.Attributes.nullable == False and cls.__extends__ is None:
        if col is None:
            col_kwargs['nullable'] = False
        else:
            col.nullable = False


def _get_sqlalchemy_type(cls):
    db_type = cls.Attributes.db_type
    if db_type is not None:
        return db_type

    # must be above Unicode, because Ltree is Unicode's subclass
    elif issubclass(cls, Ltree):
        return PGLTree

    # must be above Unicode, because Ip*Address is Unicode's subclass
    elif issubclass(cls, (IpAddress, Ipv4Address, Ipv6Address)):
        return PGInet

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

    elif issubclass(cls, AnyHtml):
        return PGHtml

    elif issubclass(cls, AnyDict):
        sa = cls.Attributes.store_as
        if isinstance(sa, c_json):
            return PGJson
        raise NotImplementedError(dict(cls=AnyDict, store_as=sa))

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
            if cls.Attributes.as_timezone is None:
                return sqlalchemy.DateTime(timezone=True)
            else:
                return sqlalchemy.DateTime(timezone=False)
        else:
            return sqlalchemy.DateTime(timezone=cls.Attributes.timezone)

    elif issubclass(cls, Time):
        return sqlalchemy.Time

    elif issubclass(cls, XmlModifier):
        retval = _get_sqlalchemy_type(cls.type)
        return retval


def _get_col_o2o(parent, k, v, fk_col_name, deferrable=None, initially=None):
    """Gets key and child type and returns a column that points to the primary
    key of the child.
    """

    assert v.Attributes.table_name is not None, "%r has no table name." % v

    col_args, col_kwargs = sanitize_args(v.Attributes.sqla_column_args)
    _sp_attrs_to_sqla_constraints(parent, v, col_kwargs)

    # get pkeys from child class
    pk_column, = get_pk_columns(v)  # FIXME: Support multi-col keys

    pk_key, pk_spyne_type = pk_column
    pk_sqla_type = _get_sqlalchemy_type(pk_spyne_type)

    # generate a fk to it from the current object (cls)
    if fk_col_name is None:
        fk_col_name = k + "_" + pk_key

    assert fk_col_name != k, "The column name for the foreign key must be " \
                             "different from the column name for the object " \
                             "itself."

    fk = ForeignKey('%s.%s' % (v.Attributes.table_name, pk_key), use_alter=True,
          name='%s_%s_fkey' % (v.Attributes.table_name, fk_col_name),
          deferrable=deferrable, initially=initially)

    return Column(fk_col_name, pk_sqla_type, fk, *col_args, **col_kwargs)


def _get_col_o2m(cls, fk_col_name, deferrable=None, initially=None):
    """Gets the parent class and returns a column that points to the primary key
    of the parent.

    Funky implementation. Yes.
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
                                     deferrable=deferrable, initially=initially)
    col = Column(fk_col_name, pk_sqla_type, fk, *col_args, **col_kwargs)

    yield col


def _get_cols_m2m(cls, k, child, fk_left_col_name, fk_right_col_name,
                  fk_left_deferrable, fk_left_initially,
                  fk_right_deferrable, fk_right_initially):
    """Gets the parent and child classes and returns foreign keys to both
    tables. These columns can be used to create a relation table."""

    col_info, left_col = _get_col_o2m(cls, fk_left_col_name,
                                                deferrable=fk_left_deferrable,
                                                initially=fk_left_initially)
    right_col = _get_col_o2o(cls, k, child, fk_right_col_name,
                                               deferrable=fk_right_deferrable,
                                               initially=fk_right_initially)
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
        index_name, index_method = v.Attributes.index

    except (TypeError, ValueError):
        index_name = "%s_%s%s" % (table.name, k, '_unique' if unique else '')
        index_method = v.Attributes.index

    if index in (False, None):
        pass

    else:
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
                assert existing_idx.unique == unique
                assert existing_idx.kwargs.get('postgresql_using') == index_method


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
        table = _FakeTable(table_name)

    return table


def _add_simple_type(cls, props, table, k, v, sqla_type):
    col_args, col_kwargs = sanitize_args(v.Attributes.sqla_column_args)
    _sp_attrs_to_sqla_constraints(cls, v, col_kwargs)

    mp = getattr(v.Attributes, 'mapper_property', None)
    if not v.Attributes.exc_table:
        if k in table.c:
            col = table.c[k]

        else:
            col = Column(k, sqla_type, *col_args, **col_kwargs)
            table.append_column(col)
            _gen_index_info(table, col, k, v)

        if not v.Attributes.exc_mapper:
            props[k] = col

    elif mp is not None:
        props[k] = mp


def _gen_array_m2m(cls, props, k, child, p):
    metadata = cls.Attributes.sqla_metadata

    col_own, col_child = _get_cols_m2m(cls, k, child, p.left, p.right,
                                    p.fk_left_deferrable, p.fk_left_initially,
                                    p.fk_right_deferrable, p.fk_right_initially)

    p.left = col_own.key
    p.right = col_child.key

    if p.multi == True:
        rel_table_name = '_'.join([cls.Attributes.table_name, k])
    else:
        rel_table_name = p.multi

    if rel_table_name in metadata.tables:
        rel_t = metadata.tables[rel_table_name]

        assert col_own.type.__class__ == rel_t.c[col_own.key].type.__class__
        assert col_child.type.__class__ == rel_t.c[col_child.key].type.__class__

    else:
        rel_t = Table(rel_table_name, metadata, *(col_own, col_child))

    own_t = cls.Attributes.sqla_table
    if p.explicit_join:
        # Specify primaryjoin and secondaryjoin when requested.
        # There are special cases when sqlalchemy can't figure it out by itself.
        # this is where we help it when we can.
        # e.g.: http://sqlalchemy.readthedocs.org/en/rel_1_0/orm/join_conditions.html#self-referential-many-to-many-relationship

        assert own_t is not None and len(get_pk_columns(cls)) > 0

        # FIXME: support more than one pk
        (col_pk_key, _), = get_pk_columns(cls)
        col_pk = own_t.c[col_pk_key]

        props[k] = relationship(child, secondary=rel_t, backref=p.backref,
                back_populates=p.back_populates, cascade=p.cascade, lazy=p.lazy,
                primaryjoin=(col_pk == rel_t.c[col_own.key]),
                secondaryjoin=(col_pk == rel_t.c[col_child.key]),
                order_by=p.order_by)
    else:
        props[k] = relationship(child, secondary=rel_t, backref=p.backref,
                            back_populates=p.back_populates, cascade=p.cascade,
                                               lazy=p.lazy, order_by=p.order_by)


def _gen_array_simple(cls, props, k, child_cust, p):
    table_name = cls.Attributes.table_name
    metadata = cls.Attributes.sqla_metadata

    # get left (fk) column info
    _gen_col = _get_col_o2m(cls, p.left, deferrable=p.fk_left_deferrable,
                                                  initially=p.fk_left_initially)
    col_info = next(_gen_col) # gets the column name
    # FIXME: Add support for multi-column primary keys.
    p.left, child_left_col_type = col_info[0]
    child_left_col_name = p.left

    # get right(data) column info
    child_right_col_type = _get_sqlalchemy_type(child_cust)
    child_right_col_name = p.right  # this is the data column
    if child_right_col_name is None:
        child_right_col_name = k

    # get table name
    child_table_name = child_cust.Attributes.table_name
    if child_table_name is None:
        child_table_name = '_'.join([table_name, k])

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
            _sp_attrs_to_sqla_constraints(cls, child_cust, col=child_left_col)
            child_t.append_column(child_left_col)

    else:
        # table does not exist, generate table
        child_right_col = Column(child_right_col_name, child_right_col_type)
        _sp_attrs_to_sqla_constraints(cls, child_cust, col=child_right_col)

        child_left_col = next(_gen_col)
        _sp_attrs_to_sqla_constraints(cls, child_cust, col=child_left_col)

        child_t = Table(child_table_name , metadata,
            Column('id', sqlalchemy.Integer, primary_key=True),
            child_left_col,
            child_right_col,
        )
        _gen_index_info(child_t, child_right_col, child_right_col_name, child_cust)

    # generate temporary class for association proxy
    cls_name = ''.join(x.capitalize() or '_' for x in
                                                child_table_name.split('_'))
                                                # generates camelcase class name.

    def _i(self, *args):
        setattr(self, child_right_col_name, args[0])

    cls_ = type("_" + cls_name, (object,), {'__init__': _i})
    mapper(cls_, child_t)
    props["_" + k] = relationship(cls_)

    # generate association proxy
    setattr(cls, k, association_proxy("_" + k, child_right_col_name))


def _gen_array_o2m(cls, props, k, child, child_cust, p):
    _gen_col = _get_col_o2m(cls, p.right, deferrable=p.fk_right_deferrable,
                                                 initially=p.fk_right_initially)
    col_info = next(_gen_col)  # gets the column name
    p.right, col_type = col_info[0]  # FIXME: Add support for multi-column primary keys.

    assert p.left is None, \
        "'left' is ignored in one-to-many relationships " \
        "with complex types (because they already have a " \
        "table). You probably meant to use 'right'."

    child_t = child.__table__

    if p.right in child_t.c:
        # FIXME: This branch MUST be tested.
        new_col_type = child_t.c[p.right].type.__class__
        assert col_type is child_t.c[p.right].type.__class__, \
                "Existing column type %r disagrees with new column type %r" % \
                                                        (col_type, new_col_type)

        # if the column is already there, the decision about whether
        # it should be in child's mapper or not should also have been
        # made.
        #
        # so, not adding the child column to to child mapper
        # here.
        col = child_t.c[p.right]

    else:
        col = next(_gen_col)

        _sp_attrs_to_sqla_constraints(cls, child_cust, col=col)

        child_t.append_column(col)
        child.__mapper__.add_property(col.name, col)

    props[k] = relationship(child, foreign_keys=[col], backref=p.backref,
                             back_populates=p.back_populates, cascade=p.cascade,
                                               lazy=p.lazy, order_by=p.order_by)


def _is_array(v):
    return (v.Attributes.max_occurs > 1 or issubclass(v, Array))


def _add_complex_type_as_table(cls, props, table, k, v, p, col_args, col_kwargs):
    # add one to many relation
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

    # add one to one relation
    else:
        # v has the Attribute values we need whereas real_v is what the
        # user instantiates (thus what sqlalchemy needs)
        if v.__orig__ is None:  # vanilla class
            real_v = v
        else: # customized class
            real_v = v.__orig__

        assert not getattr(p, 'multi', False), ('Storing a single element-type '
                                                'using a relation table is '
                                                'pointless.')

        assert p.right is None, "'right' is ignored in a one-to-one " \
                                "relationship"

        col = _get_col_o2o(cls, k, v, p.left, deferrable=p.fk_left_deferrable,
                                              initially=p.fk_left_initially)
        p.left = col.name

        if col.name in table.c:
            col = table.c[col.name]
            if col_kwargs.get('nullable') is False:
                col.nullable = False
        else:
            table.append_column(col)

        rel_kwargs = dict(
            lazy=p.lazy,
            backref=p.backref,
            order_by=p.order_by,
            back_populates=p.back_populates,
        )

        if real_v is (cls.__orig__ or cls):
            (pk_col_name, pk_col_type), = get_pk_columns(cls)
            rel_kwargs['remote_side'] = [table.c[pk_col_name]]

        rel = relationship(real_v, uselist=False, foreign_keys=[col],
                                                                   **rel_kwargs)

        _gen_index_info(table, col, k, v)

        props[k] = rel
        props[col.name] = col


def _add_complex_type_as_xml(cls, props, table, k, v, p, col_args, col_kwargs):
    if k in table.c:
        col = table.c[k]
    else:
        t = PGObjectXml(v, p.root_tag, p.no_ns, p.pretty_print)
        col = Column(k, t, *col_args, **col_kwargs)

    props[k] = col
    if not k in table.c:
        table.append_column(col)


def _add_complex_type_as_json(cls, props, table, k, v, p, col_args, col_kwargs):
    if k in table.c:
        col = table.c[k]
    else:
        t = PGObjectJson(v, ignore_wrappers=p.ignore_wrappers,
                                                        complex_as=p.complex_as)
        col = Column(k, t, *col_args, **col_kwargs)

    props[k] = col
    if not k in table.c:
        table.append_column(col)


def _add_complex_type(cls, props, table, k, v):
    if issubclass(v, File):
        return _add_file_type(cls, props, table, k, v)

    p = getattr(v.Attributes, 'store_as', None)
    col_args, col_kwargs = sanitize_args(v.Attributes.sqla_column_args)
    _sp_attrs_to_sqla_constraints(cls, v, col_kwargs)

    if isinstance(p, c_table):
        return _add_complex_type_as_table(cls, props, table, k, v,
                                                        p, col_args, col_kwargs)

    elif isinstance(p, c_xml):
        return _add_complex_type_as_xml(cls, props, table, k, v,
                                                        p, col_args, col_kwargs)
    elif isinstance(p, c_json):
        return _add_complex_type_as_json(cls, props, table, k, v,
                                                        p, col_args, col_kwargs)

    elif isinstance(p, c_msgpack):
        raise NotImplementedError(c_msgpack)

    elif p is None:
        return

    raise ValueError(p)


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
    :param props: a dict.
    :param table: a Table instance. Not a `_FakeTable` or anything.
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

    _inc = mapper_kwargs.get('include_properties', None)
    if _inc is None:
        mapper_kwargs['include_properties'] = inc + list(props.keys())

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


def _add_file_type(cls, props, table, k, v):
    p = getattr(v.Attributes, 'store_as', None)
    col_args, col_kwargs = sanitize_args(v.Attributes.sqla_column_args)
    _sp_attrs_to_sqla_constraints(cls, v, col_kwargs)

    if isinstance(p, HybridFileStore):
        if k in table.c:
            col = table.c[k]
        else:
            assert isabs(p.store)
            #FIXME: Add support for storage markers from spyne.model.complex
            if p.db_format == 'json':
                t = PGFileJson(p.store, p.type)
            else:
                raise NotImplementedError(p.db_format)

            col = Column(k, t, *col_args, **col_kwargs)

        props[k] = col
        if not k in table.c:
            table.append_column(col)

    else:
        raise NotImplementedError(p)


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
    t = _get_sqlalchemy_type(v)
    if t is None: # complex model
        _add_complex_type(cls, mapper_props, table, k, v)
    else:
        _add_simple_type(cls, mapper_props, table, k, v, t)

    # Add to mapper
    sqla_mapper = cls.Attributes.sqla_mapper
    for k,v in mapper_props.items():
        if not sqla_mapper.has_property(k):
            sqla_mapper.add_property(k, v)


def gen_sqla_info(cls, cls_bases=()):
    """Return SQLAlchemy table object corresponding to the passed Spyne object.
    Also maps given class to the returned table.
    """

    table = _check_table(cls)
    mapper_props = {}

    for k, v in cls.get_flat_type_info(cls).items():
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

    elif isinstance(v.type, PGXml):
        rpc_type = AnyXml

    elif isinstance(v.type, PGHtml):
        rpc_type = AnyHtml

    elif type(v.type) in _sq2sp_type_map:
        rpc_type = _sq2sp_type_map[type(v.type)]

    elif isinstance(v.type, (PGObjectJson, PGObjectXml)):
        rpc_type = v.type.cls

    elif isinstance(v.type, PGFileJson):
        rpc_type = v.FileData

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
