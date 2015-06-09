
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

#
# FIXME: Supports e.g.
#     MULTIPOINT (10 40, 40 30, 20 20, 30 10)
#
# but not:
#     MULTIPOINT ((10 40), (40 30), (20 20), (30 10))
#
from spyne.model import SimpleModel
from spyne.model.primitive.string import Unicode


FLOAT_PATTERN = r'-?[0-9]+\.?[0-9]*(e-?[0-9]+)?'


_rinse_and_repeat = r'\s*\(%s\s*(,\s*%s)*\)\s*'
def _get_one_point_pattern(dim):
    return ' +'.join([FLOAT_PATTERN] * dim)

def _get_point_pattern(dim):
    return r'POINT\s*\(%s\)' % _get_one_point_pattern(dim)

def _get_one_multipoint_pattern(dim):
    one_point = _get_one_point_pattern(dim)
    return _rinse_and_repeat % (one_point, one_point)

def _get_multipoint_pattern(dim):
    return r'MULTIPOINT\s*%s' % _get_one_multipoint_pattern(dim)


def _get_one_line_pattern(dim):
    one_point = _get_one_point_pattern(dim)
    return _rinse_and_repeat % (one_point, one_point)

def _get_linestring_pattern(dim):
    return r'LINESTRING\s*%s' % _get_one_line_pattern(dim)

def _get_one_multilinestring_pattern(dim):
    one_line = _get_one_line_pattern(dim)
    return _rinse_and_repeat % (one_line, one_line)

def _get_multilinestring_pattern(dim):
    return r'MULTILINESTRING\s*%s' % _get_one_multilinestring_pattern(dim)


def _get_one_polygon_pattern(dim):
    one_line = _get_one_line_pattern(dim)
    return _rinse_and_repeat % (one_line, one_line)

def _get_polygon_pattern(dim):
    return r'POLYGON\s*%s' % _get_one_polygon_pattern(dim)

def _get_one_multipolygon_pattern(dim):
    one_line = _get_one_polygon_pattern(dim)
    return _rinse_and_repeat % (one_line, one_line)

def _get_multipolygon_pattern(dim):
    return r'MULTIPOLYGON\s*%s' % _get_one_multipolygon_pattern(dim)


class Point(Unicode):
    """A point type whose native format is a WKT string. You can use
    :func:`shapely.wkt.loads` to get a proper point type.

    It's a subclass of the :class:`Unicode` type, so regular Unicode constraints
    apply. The only additional parameter is the number of dimensions.

    :param dim: Number of dimensons.
    """

    __type_name__ = None

    class Attributes(Unicode.Attributes):
        dim = None

    @staticmethod
    def Value(x, y, prec=15):
        return ('POINT(%%3.%(prec)sf %%3.%(prec)sf)' % {'prec': prec}) % (x,y)

    def __new__(cls, dim=None, **kwargs):
        assert dim in (None, 2, 3)
        if dim is not None:
            kwargs['dim'] = dim
            kwargs['pattern'] = _get_point_pattern(dim)
            kwargs['type_name'] = 'point%dd' % dim

        retval = SimpleModel.__new__(cls, **kwargs)
        retval.__namespace__ = 'http://spyne.io/schema'
        retval.__extends__ = Unicode
        retval.__orig__ = Unicode
        return retval


class Line(Unicode):
    """A line type whose native format is a WKT string. You can use
    :func:`shapely.wkt.loads` to get a proper line type.

    It's a subclass of the :class:`Unicode` type, so regular Unicode constraints
    apply. The only additional parameter is the number of dimensions.

    :param dim: Number of dimensons.
    """

    __type_name__ = None

    class Attributes(Unicode.Attributes):
        dim = None

    def __new__(cls, dim=None, **kwargs):
        assert dim in (None, 2, 3)
        if dim is not None:
            kwargs['dim'] = dim
            kwargs['pattern'] = _get_linestring_pattern(dim)
            kwargs['type_name'] = 'line%dd' % dim

        retval = SimpleModel.__new__(cls, **kwargs)
        retval.__namespace__ = 'http://spyne.io/schema'
        retval.__extends__ = Unicode
        retval.__orig__ = Unicode
        return retval

LineString = Line


class Polygon(Unicode):
    """A polygon type whose native format is a WKT string. You can use
    :func:`shapely.wkt.loads` to get a proper polygon type.

    It's a subclass of the :class:`Unicode` type, so regular Unicode constraints
    apply. The only additional parameter is the number of dimensions.

    :param dim: Number of dimensons.
    """
    __type_name__ = None

    class Attributes(Unicode.Attributes):
        dim = None

    def __new__(cls, dim=None, **kwargs):
        assert dim in (None, 2, 3)
        if dim is not None:
            kwargs['dim'] = dim
            kwargs['pattern'] = _get_polygon_pattern(dim)
            kwargs['type_name'] = 'polygon%dd' % dim

        retval = SimpleModel.__new__(cls, **kwargs)
        retval.__namespace__ = 'http://spyne.io/schema'
        retval.__extends__ = Unicode
        retval.__orig__ = Unicode
        return retval


class MultiPoint(Unicode):
    """A MultiPoint type whose native format is a WKT string. You can use
    :func:`shapely.wkt.loads` to get a proper MultiPoint type.

    It's a subclass of the :class:`Unicode` type, so regular Unicode constraints
    apply. The only additional parameter is the number of dimensions.

    :param dim: Number of dimensons.
    """

    __type_name__ = None

    class Attributes(Unicode.Attributes):
        dim = None

    def __new__(cls, dim=None, **kwargs):
        assert dim in (None, 2, 3)
        if dim is not None:
            kwargs['dim'] = dim
            kwargs['pattern'] = _get_multipoint_pattern(dim)
            kwargs['type_name'] = 'multiPoint%dd' % dim

        retval = SimpleModel.__new__(cls, **kwargs)
        retval.__namespace__ = 'http://spyne.io/schema'
        retval.__extends__ = Unicode
        retval.__orig__ = Unicode
        return retval


class MultiLine(Unicode):
    """A MultiLine type whose native format is a WKT string. You can use
    :func:`shapely.wkt.loads` to get a proper MultiLine type.

    It's a subclass of the :class:`Unicode` type, so regular Unicode constraints
    apply. The only additional parameter is the number of dimensions.

    :param dim: Number of dimensons.
    """

    __type_name__ = None

    class Attributes(Unicode.Attributes):
        dim = None

    def __new__(cls, dim=None, **kwargs):
        assert dim in (None, 2, 3)
        if dim is not None:
            kwargs['dim'] = dim
            kwargs['pattern'] = _get_multilinestring_pattern(dim)
            kwargs['type_name'] = 'multiLine%dd' % dim

        retval = SimpleModel.__new__(cls, **kwargs)
        retval.__namespace__ = 'http://spyne.io/schema'
        retval.__extends__ = Unicode
        retval.__orig__ = Unicode
        return retval

MultiLineString = MultiLine


class MultiPolygon(Unicode):
    """A MultiPolygon type whose native format is a WKT string. You can use
    :func:`shapely.wkt.loads` to get a proper MultiPolygon type.

    It's a subclass of the :class:`Unicode` type, so regular Unicode constraints
    apply. The only additional parameter is the number of dimensions.

    :param dim: Number of dimensons.
    """

    __type_name__ = None

    class Attributes(Unicode.Attributes):
        dim = None

    def __new__(cls, dim=None, **kwargs):
        assert dim in (None, 2, 3)
        if dim is not None:
            kwargs['dim'] = dim
            kwargs['pattern'] = _get_multipolygon_pattern(dim)
            kwargs['type_name'] = 'multipolygon%dd' % dim

        retval = SimpleModel.__new__(cls, **kwargs)
        retval.__namespace__ = 'http://spyne.io/schema'
        retval.__extends__ = Unicode
        retval.__orig__ = Unicode
        return retval

