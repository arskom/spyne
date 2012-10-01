
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

"""Just for postgresql, just for fun. As of yet, at least."""

from __future__ import absolute_import

import logging
logger = logging.getLogger(__name__)

import sqlalchemy

from sqlalchemy.schema import Column
from sqlalchemy.schema import Table
from sqlalchemy.schema import ForeignKey

from sqlalchemy.dialects.postgresql import FLOAT
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION
from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.orm import relationship
from sqlalchemy.orm import mapper

from spyne.model.complex import sanitize_args
from spyne.model.complex import Array
from spyne.model.complex import ComplexModelBase
from spyne.model.primitive import Decimal
from spyne.model.primitive import Double
from spyne.model.primitive import String
from spyne.model.primitive import Unicode
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
from spyne.model.primitive import Float
from spyne.model.primitive import Boolean
from spyne.model.primitive import DateTime
from spyne.model.primitive import Date
from spyne.model.primitive import Time
from spyne.model.primitive import Uuid

from spyne.util import memoize
from spyne.util.cdict import cdict


_generic_type_map = cdict({
    Float: FLOAT,
    Double: DOUBLE_PRECISION,
    Integer: sqlalchemy.DECIMAL,
    Integer64: sqlalchemy.BigInteger,
    Integer32: sqlalchemy.Integer,
    Integer16: sqlalchemy.SmallInteger,
    Integer8: sqlalchemy.SmallInteger,

    Date: sqlalchemy.Date,
    Time: sqlalchemy.Time,
    DateTime: sqlalchemy.DateTime,

    Uuid: sqlalchemy.String,
    Boolean: sqlalchemy.Boolean,
})

_psql_type_map = dict(_generic_type_map)
_psql_type_map.update({
    Uuid : UUID,
})


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

    elif issubclass(cls, (Integer, UnsignedInteger, Decimal)):
        return sqlalchemy.DECIMAL

def get_pk_columns(cls):
    retval = []
    for k, v in cls._type_info.items():
        if v.Attributes.sqla_column_args[-1].get('primary_key', False):
            retval.append((k,v))
    return tuple(retval) if len(retval) > 0 else None

def _get_col_o2o(k, v):
    """Gets key and child type and returns a column that points to the primary
    key of the child.
    """

    # get pkeys from child class
    pk_column, = get_pk_columns(v) # FIXME: Support multi-col keys

    pk_key, pk_spyne_type = pk_column
    pk_sqla_type = get_sqlalchemy_type(pk_spyne_type)

    # generate a fk to it from the current object (cls)
    fk_col_name = k + "_" + pk_key
    fk = ForeignKey('%s.%s' % (v.__tablename__, pk_key))

    return Column(fk_col_name, pk_sqla_type, fk)

def _get_col_o2m(cls):
    """Gets parent class, key and child type and returns a column that points to
    the primary key of the parent.
    """
    # get pkeys from current class
    pk_column, = get_pk_columns(cls) # FIXME: Support multi-col keys

    pk_key, pk_spyne_type = pk_column
    pk_sqla_type = get_sqlalchemy_type(pk_spyne_type)

    # generate a fk from child to the current class
    fk_col_name = '_'.join([cls.__tablename__, pk_key])

    col = Column(fk_col_name, pk_sqla_type,
                             ForeignKey('%s.%s' % (cls.__tablename__, pk_key)))

    return col


@memoize
def get_sqlalchemy_table(cls, map_class_to_table=True):
    rels = {}
    cols = []
    constraints = []
    metadata = cls.Attributes.sqla_metadata

    # For each Spyne field
    for k, v in cls._type_info.items():
        t = get_sqlalchemy_type(v)

        if t is None:
            if issubclass(v, Array): # one to many
                child, = v._type_info.values()
                if child.__orig__ is not None:
                    child = child.__orig__

                if v.Attributes.store_as == 'table':
                    col = _get_col_o2m(cls)

                    child.__table__.append_column(col)
                    child.__mapper__.add_property(col.name, col)
                    rels[k] = relationship(child)


            elif issubclass(v, ComplexModelBase): # one to one
                col = _get_col_o2o(k, v)

                # create the relationship.
                if v.__orig__ is None:
                    # vanilla class
                    rel = relationship(v, uselist=False)
                else:
                    # customized class
                    rel = relationship(v.__orig__, uselist=False)

                cols.append(col)
                rels[k] = rel

            else:
                logger.debug("Skipping %s.%s.%s: %r" % (
                                                    cls.get_namespace(),
                                                    cls.get_type_name(), k, v))

        else:
            col_args, col_kwargs = sanitize_args(v.Attributes.sqla_column_args)
            col = Column(k, t, *col_args, **col_kwargs)
            cols.append(col)
            rels[k] = col

    # Create table
    table_args, table_kwargs = sanitize_args(cls.Attributes.sqla_table_args)
    table = Table(cls.__tablename__, metadata,
                        *(tuple(cols) + tuple(constraints) + tuple(table_args)),
                        **table_kwargs)

    # Map the table to the object
    if map_class_to_table:
        mapper_args, mapper_kwargs = sanitize_args(cls.Attributes.sqla_mapper_args)
        mapper_kwargs['properties'] = rels
        cls.__mapper__ = mapper(cls, table, *mapper_args, **mapper_kwargs)
        cls.__table__ = table

    return table
