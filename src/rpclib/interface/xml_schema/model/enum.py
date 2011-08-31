
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

from lxml import etree

import rpclib.const.xml_ns
_ns_xsd = rpclib.const.xml_ns.xsd

def enum_add(interface, cls):
    if not interface.has_class(cls):
        simple_type = etree.Element('{%s}simpleType' % _ns_xsd)
        simple_type.set('name', cls.get_type_name())

        restriction = etree.SubElement(simple_type,
                                            '{%s}restriction' % _ns_xsd)
        restriction.set('base', '%s:string' %
                                interface.get_namespace_prefix(_ns_xsd))

        for v in cls.__values__:
            enumeration = etree.SubElement(restriction,
                                            '{%s}enumeration' % _ns_xsd)
            enumeration.set('value', v)

        interface.add_simple_type(cls, simple_type)
