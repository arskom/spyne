
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

"""A Postgresql serializer for Spyne objects.

Uses SQLAlchemy for mapping objects to relations.
"""

from spyne.store.relational import override
from spyne.store.relational._base import (
    add_column,
    gen_spyne_info,
    gen_sqla_info,
    get_pk_columns
)
from spyne.store.relational.document import (
    PGFileJson,
    PGHtml,
    PGJson,
    PGJsonB,
    PGObjectJson,
    PGObjectXml,
    PGXml
)
from spyne.store.relational.simple import PGLQuery, PGLTree, PGLTxtQuery
from spyne.store.relational.spatial import PGGeometry
