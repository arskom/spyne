
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

import sqlalchemy
from sqlalchemy import Column

from sqlalchemy.ext.declarative import DeclarativeMeta
from soaplib.serializers.clazz import ClassSerializerBase
from soaplib.serializers import primitive as soap

_type_map = {
    sqlalchemy.Text: soap.String,
    sqlalchemy.String: soap.String,
    sqlalchemy.Unicode: soap.String,
    sqlalchemy.UnicodeText: soap.String,

    sqlalchemy.Float: soap.Float,
    sqlalchemy.Double: soap.Double,
    sqlalchemy.Decimal: soap.Decimal,
    sqlalchemy.Numeric: soap.Double,
    sqlalchemy.Integer: soap.Integer,
    sqlalchemy.SmallInteger: soap.Integer,

    sqlalchemy.Boolean: soap.Boolean,
    sqlalchemy.DateTime: soap.DateTime,
    sqlalchemy.orm.relation: soap.Array,
}

class TableSerializerMeta(DeclarativeMeta):
    # FIXME: ClassSerializerMeta ile birlestirilecek
    def __init__(cls, cls_name, cls_bases, cls_dict):
        cls._type_info = {}
        cls.__type_name__ = cls.__name__
        cls.set_namespace(cls.__module__)

        for k, v in cls_dict.items():
            if k == '__namespace__':
                cls.set_namespace(v)

            elif k == '__type_name__':
                cls.__type_name__ = v

            elif not k.startswith('__'):
                if isinstance(v, Column):
                    if v.type in _type_map:
                        rpc_type = _type_map[v.type]
                    elif type(v.type) in _type_map:
                        rpc_type = _type_map[type(v.type)]
                    else:
                        raise Exception("soap_type was not found. maybe _type_map "
                                        "needs a new entry.")

                    cls._type_info[k]=rpc_type

        DeclarativeMeta.__init__(cls, cls_name, cls_bases, cls_dict)

class TableSerializer(ClassSerializerBase):
    __metaclass__ = TableSerializerMeta
    _decl_class_registry={}
