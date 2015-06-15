
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

from sqlalchemy import sql
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql.base import PGUuid
from sqlalchemy.dialects.postgresql.base import ischema_names, PGTypeCompiler, ARRAY
from sqlalchemy.sql.sqltypes import Concatenable
from sqlalchemy.sql.type_api import UserDefinedType


@compiles(PGUuid, "sqlite")
def compile_uuid_sqlite(type_, compiler, **kw):
    return "BLOB"



class PGLTree(Concatenable, UserDefinedType):
    """Postgresql `ltree` type."""

    class Comparator(Concatenable.Comparator):
        def ancestor_of(self, other):
            if isinstance(other, list):
                return self.op('@>')(sql.cast(other, ARRAY(PGLTree)))
            else:
                return self.op('@>')(other)

        def descendant_of(self, other):
            if isinstance(other, list):
                return self.op('<@')(sql.cast(other, ARRAY(PGLTree)))
            else:
                return self.op('<@')(other)

        def lquery(self, other):
            if isinstance(other, list):
                return self.op('?')(sql.cast(other, ARRAY(PGLQuery)))
            else:
                return self.op('~')(other)

        def ltxtquery(self, other):
            return self.op('@')(other)

    comparator_factory = Comparator

    __visit_name__ = 'LTREE'


class PGLQuery(UserDefinedType):
    """Postresql `lquery` type."""

    __visit_name__ = 'LQUERY'


class PGLTxtQuery(UserDefinedType):
    """Postresql `ltxtquery` type."""

    __visit_name__ = 'LTXTQUERY'


ischema_names['ltree'] = PGLTree
ischema_names['lquery'] = PGLQuery
ischema_names['ltxtquery'] = PGLTxtQuery


def visit_LTREE(self, type_, **kw):
    return 'LTREE'


def visit_LQUERY(self, type_, **kw):
    return 'LQUERY'


def visit_LTXTQUERY(self, type_, **kw):
    return 'LTXTQUERY'


PGTypeCompiler.visit_LTREE = visit_LTREE
PGTypeCompiler.visit_LQUERY = visit_LQUERY
PGTypeCompiler.visit_LTXTQUERY = visit_LTXTQUERY
