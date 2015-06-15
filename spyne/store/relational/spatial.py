
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
from sqlalchemy.sql.type_api import UserDefinedType


class PGGeometry(UserDefinedType):
    """Geometry type for Postgis 2"""

    class PlainWkt:
        pass

    class PlainWkb:
        pass

    def __init__(self, geometry_type='GEOMETRY', srid=4326, dimension=2,
                 format='wkt'):
        self.geometry_type = geometry_type.upper()
        self.name = 'geometry'
        self.srid = int(srid)
        self.dimension = dimension
        self.format = format

        if self.format == 'wkt':
            self.format = PGGeometry.PlainWkt
        elif self.format == 'wkb':
            self.format = PGGeometry.PlainWkb

    def get_col_spec(self):
        return '%s(%s,%d)' % (self.name, self.geometry_type, self.srid)

    def column_expression(self, col):
        if self.format is PGGeometry.PlainWkb:
            return sql.func.ST_AsBinary(col, type_=self)
        if self.format is PGGeometry.PlainWkt:
            return sql.func.ST_AsText(col, type_=self)

    def result_processor(self, dialect, coltype):
        if self.format is PGGeometry.PlainWkt:
            def process(value):
                if value is not None:
                    return value

        if self.format is PGGeometry.PlainWkb:
            def process(value):
                if value is not None:
                    return sql.func.ST_AsBinary(value, self.srid)

        return process

    def bind_expression(self, bindvalue):
        if self.format is PGGeometry.PlainWkt:
            return sql.func.ST_GeomFromText(bindvalue, self.srid)


Geometry = PGGeometry


@compiles(PGGeometry)
def compile_geometry(type_, compiler, **kw):
    return '%s(%s,%d)' % (type_.name, type_.geometry_type, type_.srid)


@compiles(PGGeometry, "sqlite")
def compile_geometry_sqlite(type_, compiler, **kw):
    return "BLOB"
