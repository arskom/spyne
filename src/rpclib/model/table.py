
#
# rpclib - Copyright (C) Rpclib contributors.
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

"""This module aims to bridge SQLAlchemy and rpclib types by building a
_type_info dictionary using the information held in class attributes by
sqlalchemy.Column instances.

While this module seems to be working fine for the documented purposes, the
flexibility of SQLAlchemy and complexity of its internals leave much to be
tested. Also considering the vast amount of non-supported sqlalchemy and rpclib
features, this module should be treated as EXPERIMENTAL. Please use with care
and do bring up any issues you experience with this module to the attention of
rpclib or SQLAlchemy developers.
"""

import logging
logger = logging.getLogger(__name__)

import sqlalchemy

from sqlalchemy import Column
from sqlalchemy.orm import RelationshipProperty

from sqlalchemy.ext.declarative import DeclarativeMeta

from sqlalchemy.dialects.postgresql import UUID

from rpclib.model.complex import TypeInfo
from rpclib.model.complex import ComplexModelBase
from rpclib.model.complex import ComplexModelMeta
from rpclib.model import primitive
from rpclib.model import binary
from rpclib.model import complex


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

    UUID: primitive.String
}


def _process_item(v):
    """This function maps sqlalchemy types to rpclib types."""

    rpc_type = None
    if isinstance(v, Column):
        if v.type in _type_map:
            rpc_type = _type_map[v.type]
        elif type(v.type) in _type_map:
            rpc_type = _type_map[type(v.type)]
        else:
            raise Exception("soap_type was not found. maybe _type_map needs a new "
                            "entry. %r" % v)
    elif isinstance(v, RelationshipProperty):
        rpc_type = v.argument

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
    the _type_info dictionary that rpclib relies on. It otherwise leaves
    SQLAlchemy and its information alone.
    """

    def __new__(cls, cls_name, cls_bases, cls_dict):
        if cls_dict.get("__type_name__", None) is None:
            cls_dict["__type_name__"] = cls_name

        if cls_dict.get("_type_info", None) is None:
            cls_dict["_type_info"] = _type_info = TypeInfo()

            # mixin inheritance
            for b in cls_bases:
                for k, v in vars(b).items():
                    if _is_interesting(k, v):
                        _type_info[k] = _process_item(v)

            # same table inheritance
            for b in cls_bases:
                table = getattr(b, '__table__', None)

                if not (table is None):
                    for c in table.c:
                        _type_info[c.name] = _process_item(c)

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
    rpclib. Classes that inherit from this class should also inherit from
    an sqlalchemy.declarative base class. See the :ref:`manual-sqlalchemy`
    section for more info.
    """

    __metaclass__ = TableModelMeta
    _decl_class_registry = {}

    @classmethod
    def customize(cls, **kwargs):
        cls_name, cls_bases, cls_dict = ComplexModelBase._s_customize(
                                                                  cls, **kwargs)

        retval = ComplexModelMeta.__new__(ComplexModelMeta, cls_name,
                                                            cls_bases, cls_dict)

        return retval

TableSerializer = TableModel
"""DEPRECATED. Use TableModel instead."""
