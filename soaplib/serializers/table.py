
#
# soaplib - Copyright (C) 2010 Arskom Ltd. www.arskom.com.tr
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

import inspect

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
    sqlalchemy.Numeric: soap.Double,
    sqlalchemy.Integer: soap.Integer,
    sqlalchemy.SmallInteger: soap.Integer,

    sqlalchemy.Boolean: soap.Boolean,
    sqlalchemy.DateTime: soap.DateTime,
    sqlalchemy.orm.relation: soap.Array,
}

class TableSerializerMeta(DeclarativeMeta):
    def __init__(cls, name, bases, dict_):
        types = cls
        members = dict(inspect.getmembers(types))
        cls.soap_members = {}
        cls.namespace = None

        for k, v in members.items():
            if isinstance(v, Column):
                if v.type in _type_map:
                    soap_type = _type_map[v.type]
                elif type(v.type) in _type_map:
                    soap_type = _type_map[type(v.type)]
                else:
                    raise Exception("soap_type was not found. maybe _type_map "
                                    "needs a new entry.")

                cls.soap_members[k]=soap_type;

            elif v is soap.Array:
                if v.type in _type_map:
                    soap_type = soap.Array(_type_map[v.type])
                elif type(v.type) in _type_map:
                    soap_type = soap.Array(_type_map[type(v.type)])
                else:
                    raise Exception("soap_type was not found. maybe _type_map "
                                    "needs a new entry.")

                cls.soap_members[k]=soap_type;

        DeclarativeMeta.__init__(cls, name, bases, dict_)

class TableSerializer(ClassSerializerBase):
    __metaclass__ = TableSerializerMeta
    _decl_class_registry={}
