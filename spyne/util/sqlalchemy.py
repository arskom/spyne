
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

from lxml import etree

from sqlalchemy.schema import Column
from sqlalchemy.schema import Table
from sqlalchemy.schema import ForeignKey

from sqlalchemy.dialects.postgresql import FLOAT
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION
from sqlalchemy.dialects.postgresql.base import PGUuid

from sqlalchemy.ext.compiler import compiles

from sqlalchemy.orm import relationship
from sqlalchemy.orm import mapper

from sqlalchemy.types import UserDefinedType

from spyne.model.complex import table as c_table
from spyne.model.complex import xml as c_xml
from spyne.model.complex import json as c_json
from spyne.model.complex import msgpack as c_msgpack

from spyne.model.complex import Array
from spyne.model.complex import ComplexModelBase
from spyne.model.primitive import Uuid
from spyne.model.primitive import Date
from spyne.model.primitive import Time
from spyne.model.primitive import DateTime
from spyne.model.primitive import Float
from spyne.model.primitive import Double
from spyne.model.primitive import Decimal
from spyne.model.primitive import String
from spyne.model.primitive import Unicode
from spyne.model.primitive import Boolean
from spyne.model.primitive import Integer
from spyne.model.primitive import Integer8
from spyne.model.primitive import Integer16
from spyne.model.primitive import Integer32
from spyne.model.primitive import Integer64
from spyne.model.primitive import UnsignedInteger
from spyne.model.primitive import UnsignedInteger8
from spyne.model.primitive import UnsignedInteger16
from spyne.model.primitive import UnsignedInteger32
from spyne.model.primitive import UnsignedInteger64

from spyne.util import memoize
from spyne.util import sanitize_args

from spyne.util.xml import get_object_as_xml
from spyne.util.xml import get_xml_as_object
from spyne.util.dictobj import get_dict_as_object
from spyne.util.dictobj import get_object_as_dict


# Inheritance type constants.
class _SINGLE:
    pass

class _JOINED:
    pass


@compiles(PGUuid, "sqlite")
def compile_uuid_sqlite(type_, compiler, **kw):
    return "BLOB"


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

sqlalchemy.dialects.postgresql.base.ischema_names['xml'] = PGObjectXml


class PGObjectJson(UserDefinedType):
    def __init__(self, cls):
        self.cls = cls

    def get_col_spec(self):
        return "json"

    def bind_processor(self, dialect):
        def process(value):
            return json.dumps(get_object_as_dict(value, self.cls))
        return process

    def result_processor(self, dialect, col_type):
        def process(value):
            if value is not None:
                return get_dict_as_object(json.loads(value), self.cls)
        return process

sqlalchemy.dialects.postgresql.base.ischema_names['json'] = PGObjectJson


@memoize
def get_sqlalchemy_type(cls):
    if issubclass(cls, String):
        if cls.Attributes.max_len == String.Attributes.max_len: # Default is arbitrary-length
            return sqlalchemy.Text
        else:
            return sqlalchemy.String(cls.Attributes.max_len)

    elif issubclass(cls, Unicode):
        if cls.Attributes.max_len == Unicode.Attributes.max_len: # Default is arbitrary-length
            return sqlalchemy.UnicodeText
        else:
            return sqlalchemy.Unicode(cls.Attributes.max_len)

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

    elif issubclass(cls, DateTime):
        return sqlalchemy.DateTime

    elif issubclass(cls, Date):
        return sqlalchemy.Date

    elif issubclass(cls, Time):
        return sqlalchemy.Time

    elif issubclass(cls, Uuid):
        return PGUuid


def get_pk_columns(cls):
    """Return primary key fields of a Spyne object."""

    retval = []
    for k, v in cls._type_info.items():
        if v.Attributes.sqla_column_args is not None and \
                    v.Attributes.sqla_column_args[-1].get('primary_key', False):
            retval.append((k,v))
    return tuple(retval) if len(retval) > 0 else None


def _get_col_o2o(k, v, fk_col_name):
    """Gets key and child type and returns a column that points to the primary
    key of the child.
    """
    assert v.Attributes.table_name is not None, "%r has no table name." % v
    col_args, col_kwargs = sanitize_args(v.Attributes.sqla_column_args)

    # get pkeys from child class
    pk_column, = get_pk_columns(v) # FIXME: Support multi-col keys

    pk_key, pk_spyne_type = pk_column
    pk_sqla_type = get_sqlalchemy_type(pk_spyne_type)

    # generate a fk to it from the current object (cls)
    if fk_col_name is None:
        fk_col_name = k + "_" + pk_key

    fk = ForeignKey('%s.%s' % (v.Attributes.table_name, pk_key))

    return Column(fk_col_name, pk_sqla_type, fk, *col_args, **col_kwargs)


def _get_col_o2m(cls, fk_col_name):
    """Gets the parent class and returns a column that points to the primary key
    of the parent.
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

    col = Column(fk_col_name, pk_sqla_type,
                    ForeignKey('%s.%s' % (cls.Attributes.table_name, pk_key)),
                                                        *col_args, **col_kwargs)

    return col


def _get_cols_m2m(cls, k, v, left_fk_col_name, right_fk_col_name):
    """Gets the parent and child classes and returns foreign keys to both
    tables. These columns can be used to create a relation table."""

    child, = v._type_info.values()
    return _get_col_o2m(cls, left_fk_col_name), \
                                       _get_col_o2o(k, child, right_fk_col_name)


class _FakeTable(object):
    def __init__(self):
        self.columns = []
        self.c = {}

    def append_column(self, col):
        self.columns.append(col)
        self.c[col.name] = col


def gen_sqla_info(cls, cls_bases=()):
    """Return SQLAlchemy table object corresponding to the passed Spyne object.
    Also maps given class to the returned table.
    """

    metadata = cls.Attributes.sqla_metadata
    table_name = cls.Attributes.table_name

    # check inheritance
    inheritance = None
    base_class = getattr(cls, '__extends__', None)
    if base_class is None:
        for b in cls_bases:
            if getattr(b, '_type_info', None) is not None:
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

    # check whether the object is already mapped
    table = None
    if table_name in metadata.tables:
        if inheritance is None:
            return metadata.tables[table_name]
        else:
            table = base_class.Attributes.sqla_table
    else:
        # We need FakeTable because table_args can contain all sorts of stuff
        # that can require a fully-constructed table, and we don't have that
        # information here yet.
        table = _FakeTable()

    rels = {}
    exc = []

    # For each Spyne field
    for k, v in cls._type_info.items():
        col_args, col_kwargs = sanitize_args(v.Attributes.sqla_column_args)
        if v.Attributes.nullable == False:
            col_kwargs['nullable'] = False

        if k in table.c:
            continue

        t = get_sqlalchemy_type(v)

        if t is None:
            p = getattr(v.Attributes, 'store_as', None)
            if p is not None and issubclass(v, Array) and isinstance(p, c_table):
                child, = v._type_info.values()
                if child.__orig__ is not None:
                    child = child.__orig__

                if p.multi != False: # many to many
                    col_own, col_child = _get_cols_m2m(cls, k, v, p.left, p.right)

                    if p.multi == True:
                        rel_table_name = '_'.join([cls.Attributes.table_name, k])
                    else:
                        rel_table_name = p.multi

                    # FIXME: Handle the case where the table already exists.
                    rel_t = Table(rel_table_name, metadata, *(col_own, col_child))

                    rels[k] = relationship(child, secondary=rel_t)

                else: # one to many
                    assert p.left is None, "'left' is ignored."

                    col = _get_col_o2m(cls, p.right)

                    child.__table__.append_column(col)
                    child.__mapper__.add_property(col.name, col)

                    rels[k] = relationship(child)

            elif p is not None and issubclass(v, ComplexModelBase):
                # v has the Attribute values we need whereas real_v is what the
                # user instantiates (thus what sqlalchemy needs)
                if v.__orig__ is None: # vanilla class
                    real_v = v
                else: # customized class
                    real_v = v.__orig__

                if isinstance(p, c_table):
                    if getattr(p, 'multi', False):
                        raise Exception('Storing a single element-type using a '
                                        'relation table is pointless.')

                    assert p.right is None, "'right' is ignored"

                    col = _get_col_o2o(k, v, p.left)
                    rel = relationship(real_v, uselist=False)

                    rels[k] = rel

                elif isinstance(p, c_xml):
                    col = Column(k, PGObjectXml(v, p.root_tag, p.no_ns),
                                                        *col_args, **col_kwargs)

                elif isinstance(p, c_json):
                    col = Column(k, PGObjectJson(v), *col_args, **col_kwargs)

                elif isinstance(p, c_msgpack):
                    raise NotImplementedError()

                else:
                    raise ValueError(p)

                rels[col.name] = col
                table.append_column(col)

            else:
                logger.debug("Skipping %s.%s.%s: %r, store_as: %r" % (
                                                cls.get_namespace(),
                                                cls.get_type_name(), k, v, p))

        else:
            col = Column(k, t, *col_args, **col_kwargs)
            table.append_column(col)

            if v.Attributes.private:
                exc.append(k)
            else:
                rels[k] = col

    if isinstance(table, _FakeTable):
        table_args, table_kwargs = sanitize_args(cls.Attributes.sqla_table_args)
        table = Table(table_name, metadata,
                           *(tuple(table.columns) + table_args), **table_kwargs)

    # Map the table to the object
    mapper_args, mapper_kwargs = sanitize_args(cls.Attributes.sqla_mapper_args)
    mapper_kwargs['properties'] = rels
    mapper_kwargs['exclude_properties'] = exc
    po = mapper_kwargs.get('polymorphic_on', None)
    if po is not None:
        mapper_kwargs['polymorphic_on'] = table.c[po]

    if getattr(cls, '__extends__', None) is not None:
        mapper_kwargs['inherits'] = cls.__extends__.Attributes.sqla_mapper
    cls_mapper = mapper(cls, table, *mapper_args, **mapper_kwargs)

    cls.__tablename__ = cls.Attributes.table_name
    cls.Attributes.sqla_mapper = cls.__mapper__ = cls_mapper
    cls.Attributes.sqla_table = cls.__table__ = table

    return table
