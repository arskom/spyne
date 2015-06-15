
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

from spyne.store.relational._base import add_column
from spyne.store.relational._base import gen_sqla_info
from spyne.store.relational._base import gen_spyne_info
from spyne.store.relational._base import get_pk_columns

from spyne.store.relational.document import PGXml, PGObjectXml, PGHtml
from spyne.store.relational.document import PGJson, PGObjectJson, PGFileJson
from spyne.store.relational.simple import PGLTree, PGLQuery, PGLTxtQuery
from spyne.store.relational.spatial import PGGeometry
