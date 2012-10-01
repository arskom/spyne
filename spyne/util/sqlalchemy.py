
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

from spyne.model.complex import sanitize_args
import logging
logger = logging.getLogger(__name__)

import sqlalchemy

from sqlalchemy.schema import Column
from sqlalchemy.schema import Table

from sqlalchemy.dialects.postgresql import FLOAT
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION
from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.orm import relationship
from sqlalchemy.orm import mapper

from sqlalchemy.schema import ForeignKeyConstraint

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

@memoize
def get_sqlalchemy_table(cls, map_class_to_table=True):
    props = {}
    columns = []
    constraints = []

    # For each Spyne field
    for k, v in cls._type_info.items():
        print cls, k, v
        t = get_sqlalchemy_type(v)

        if t is None:
            if issubclass(v, Array): # one to many
                props[k] = relationship(v)

            elif issubclass(v, ComplexModelBase): # one to one
                # get pk column of the sub-object (v) ...
                pk_column, = get_pk_columns(v) # FIXME: Support multi-col pkeys

                pk_key, pk_spyne_type = pk_column
                pk_sqla_type = get_sqlalchemy_type(pk_spyne_type)

                # ... generate a fk to it from the current object (cls)
                fk_col_name = k + "_" + pk_key
                columns.append(Column(fk_col_name, pk_sqla_type))

                fk_args = [fk_col_name], ['%s.%s' % (v.__table__, pk_key)]
                constraints.append(ForeignKeyConstraint(*fk_args))

                # ... and finally create the relationship.
                if v.__orig__ is None:
                    # vanilla class
                    props[k] = relationship(v, uselist=False)
                else:
                    # customized class
                    props[k] = relationship(v.__orig__, uselist=False)

            else:
                logger.debug("Skipping %s.%s.%s: %r" % (
                                                    cls.get_namespace(),
                                                    cls.get_type_name(), k, v))

        else:
            col_args, col_kwargs = sanitize_args(v.Attributes.sqla_column_args)
            col = Column(k, t, *col_args, **col_kwargs)
            columns.append(col)
            props[k] = col

    # Create table
    table_args, table_kwargs = sanitize_args(cls.Attributes.sqla_table_args)
    table = Table(cls.__tablename__, cls.Attributes.sqla_metadata,
                        *(tuple(columns) + tuple(constraints) + tuple(table_args)),
                        **table_kwargs)

    # Map the table to the object
    if map_class_to_table:
        mapper_args, mapper_kwargs = sanitize_args(cls.Attributes.sqla_mapper_args)
        mapper_kwargs['properties'] = props
        mapper(cls, table, *mapper_args, **mapper_kwargs)
        cls.__table__ = table

    return table
