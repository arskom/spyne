
#
# soaplib - Copyright (C) Soaplib contributors.
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

"""
The soaplib.core.model.table module is EXPERIMENTAL. It does not support
inheritance, it is supposedly buggy and possibly slow.
"""

import logging
logger = logging.getLogger(__name__)

import sqlalchemy
from sqlalchemy import Column

from sqlalchemy.ext.declarative import DeclarativeMeta
from soaplib.core.model.clazz import TypeInfo
from soaplib.core.model.clazz import ClassModelBase
from soaplib.core.model import primitive
from soaplib.core.model import clazz

_type_map = {
    sqlalchemy.Text: primitive.String,
    sqlalchemy.String: primitive.String,
    sqlalchemy.Unicode: primitive.String,
    sqlalchemy.UnicodeText: primitive.String,

    sqlalchemy.Float: primitive.Float,
    sqlalchemy.Numeric: primitive.Double,
    sqlalchemy.Integer: primitive.Integer,
    sqlalchemy.SmallInteger: primitive.Integer,

    sqlalchemy.Boolean: primitive.Boolean,
    sqlalchemy.DateTime: primitive.DateTime,
    sqlalchemy.Numeric: primitive.Decimal,
    sqlalchemy.orm.relation: clazz.Array,
}

def parse_cls_dict(cls_dict):
    cls_dict["_type_info"] = _type_info = TypeInfo()

    for k, v in cls_dict.items():
        if not k.startswith('__'):
            if isinstance(v, Column):
                if v.type in _type_map:
                    rpc_type = _type_map[v.type]
                elif type(v.type) in _type_map:
                    rpc_type = _type_map[type(v.type)]
                else:
                    raise Exception("soap_type was not found. maybe "
                                    "_type_map needs a new entry.")

                _type_info[k]=rpc_type

class TableSerializerMeta(DeclarativeMeta):
    def __new__(cls, cls_name, cls_bases, cls_dict):
        if cls_dict.get("__type_name__", None) is None:
            cls_dict["__type_name__"] = cls_name

        if cls_dict.get("_type_info", None) is None:
            parse_cls_dict(cls_dict)

        return DeclarativeMeta.__new__(cls, cls_name, cls_bases, cls_dict)

class TableSerializer(ClassModelBase):
    __metaclass__ = TableSerializerMeta
    _decl_class_registry={}
