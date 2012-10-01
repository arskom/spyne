
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

"""This module is DEPRECATED. Create your own TableModel using
:func:`spyne.model.complex.TTableModel`
"""


import logging
logger = logging.getLogger(__name__)

import sqlalchemy

from sqlalchemy import Column
from sqlalchemy.orm import RelationshipProperty

from sqlalchemy.ext.declarative import DeclarativeMeta

from sqlalchemy.dialects.postgresql import UUID

from spyne.model import primitive
from spyne.model import binary
from spyne.model import complex
from spyne.model.complex import Array
from spyne.model.complex import TypeInfo
from spyne.model.complex import ComplexModelBase
from spyne.model.complex import ComplexModelMeta


_type_map = {
    sqlalchemy.Text: primitive.String,
    sqlalchemy.String: primitive.String,
    sqlalchemy.Unicode: primitive.String,
    sqlalchemy.UnicodeText: primitive.String,

    sqlalchemy.Float: primitive.Float,
    sqlalchemy.Numeric: primitive.Decimal,
    sqlalchemy.BigInteger: primitive.Integer,
    sqlalchemy.Integer: primitive.Integer,
    sqlalchemy.SmallInteger: primitive.Integer,

    sqlalchemy.Binary: binary.ByteArray,
    sqlalchemy.LargeBinary: binary.ByteArray,
    sqlalchemy.Boolean: primitive.Boolean,
    sqlalchemy.DateTime: primitive.DateTime,
    sqlalchemy.Date: primitive.Date,
    sqlalchemy.Time: primitive.Time,

    sqlalchemy.orm.relation: complex.Array,

    UUID: primitive.String(pattern="%(x)s{8}-%(x)s{4}-%(x)s{4}-%(x)s{4}-%(x)s{12}"
                                            % {'x': '[a-fA-F0-9]'}, name='uuid')
}


def _process_item(v):
    """This function maps sqlalchemy types to spyne types."""

    rpc_type = None
    if isinstance(v, Column):
        if isinstance(v.type, sqlalchemy.Enum):
            if v.type.convert_unicode:
                rpc_type = primitive.Unicode(values=v.type.enums)
            else:
                rpc_type = primitive.String(values=v.type.enums)

        elif v.type in _type_map:
            rpc_type = _type_map[v.type]

        elif type(v.type) in _type_map:
            rpc_type = _type_map[type(v.type)]

        else:
            raise Exception("soap_type was not found. maybe _type_map needs a "
                            "new entry. %r" % v)

    elif isinstance(v, RelationshipProperty):
        v.enable_typechecks = False
        # FIXME: Distinguish between *ToMany and *ToOne relationship.
        # rpc_type = v.argument
        rpc_type = Array(v.argument)

    return rpc_type


def _is_interesting(k, v):
    if k.startswith('__'):
        return False

    if isinstance(v, Column):
        return True

    if isinstance(v, RelationshipProperty):
        if getattr(v.argument, '_type_info', None) is None:
            logger.warning("the argument to relationship should be a reference "
                           "to the real column, not a string.")
            return False

        else:
            return True


class TableModelMeta(DeclarativeMeta, ComplexModelMeta):
    """This class uses the information in class definition dictionary to build
    the _type_info dictionary that spyne relies on. It otherwise leaves
    SQLAlchemy and its information alone.
    """

    def __new__(cls, cls_name, cls_bases, cls_dict):
        if cls_dict.get("__type_name__", None) is None:
            cls_dict["__type_name__"] = cls_name

        if cls_dict.get("_type_info", None) is None:
            cls_dict["_type_info"] = _type_info = TypeInfo()

            def check_mixin_inheritance(bases):
                for b in bases:
                    check_mixin_inheritance(b.__bases__)

                    for k, v in vars(b).items():
                        if _is_interesting(k, v):
                            _type_info[k] = _process_item(v)

            check_mixin_inheritance(cls_bases)

            def check_same_table_inheritance(bases):
                for b in bases:
                    check_same_table_inheritance(b.__bases__)

                    table = getattr(b, '__table__', None)

                    if not (table is None):
                        for c in table.c:
                            _type_info[c.name] = _process_item(c)

            check_same_table_inheritance(cls_bases)

            # include from table
            table = cls_dict.get('__table__', None)
            if not (table is None):
                for c in table.c:
                    _type_info[c.name] = _process_item(c)

            # own attributes
            for k, v in cls_dict.items():
                if _is_interesting(k, v):
                    _type_info[k] = _process_item(v)

        return DeclarativeMeta.__new__(cls, cls_name, cls_bases, cls_dict)


class TableModel(ComplexModelBase):
    """The main base class for complex types shared by both SQLAlchemy and
    spyne. Classes that inherit from this class should also inherit from
    an sqlalchemy.declarative base class. See the :ref:`manual-sqlalchemy`
    section for more info.
    """

    __metaclass__ = TableModelMeta
    _decl_class_registry = {}
