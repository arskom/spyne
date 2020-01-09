
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


from sqlalchemy.ext.compiler import compiles

from sqlalchemy.dialects.postgresql import INET
from spyne.store.relational import PGXml, PGJson, PGHtml, PGJsonB, \
    PGObjectJson, PGFileJson


@compiles(PGXml)
def compile_xml(type_, compiler, **kw):
    return "xml"


@compiles(PGHtml)
def compile_html(type_, compiler, **kw):
    return "text"


@compiles(PGJson)
def compile_json(type_, compiler, **kw):
    return type_.get_col_spec()


@compiles(PGJsonB)
def compile_jsonb(type_, compiler, **kw):
    return type_.get_col_spec()


@compiles(PGObjectJson)
def compile_ojson(type_, compiler, **kw):
    return type_.get_col_spec()


@compiles(PGFileJson)
def compile_fjson(type_, compiler, **kw):
    return type_.get_col_spec()


@compiles(INET)
def compile_inet(type_, compiler, **kw):
    return "inet"



@compiles(PGXml, "firebird")
def compile_xml_firebird(type_, compiler, **kw):
    return "blob"


@compiles(PGHtml, "firebird")
def compile_html_firebird(type_, compiler, **kw):
    return "blob"


@compiles(PGJson, "firebird")
def compile_json_firebird(type_, compiler, **kw):
    return "blob"


@compiles(PGJsonB, "firebird")
def compile_jsonb_firebird(type_, compiler, **kw):
    return "blob"


@compiles(PGObjectJson, "firebird")
def compile_ojson_firebird(type_, compiler, **kw):
    return "blob"


@compiles(PGFileJson, "firebird")
def compile_fjson_firebird(type_, compiler, **kw):
    return "blob"


@compiles(INET, "firebird")
def compile_inet_firebird(type_, compiler, **kw):
    # http://pubs.opengroup.org/onlinepubs/9699919799/basedefs/netinet_in.h.html
    # INET6_ADDRSTRLEN
    return "varchar(45)"
