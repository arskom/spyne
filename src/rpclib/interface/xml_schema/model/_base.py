
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

import rpclib.const.xml_ns

from lxml import etree

_ns_xsi = rpclib.const.xml_ns.xsi
_ns_xsd = rpclib.const.xml_ns.xsd

def simple_get_restriction_tag(interface, cls):
    simple_type = etree.Element('{%s}simpleType' % _ns_xsd)
    simple_type.set('name', cls.get_type_name())
    interface.add_simple_type(cls, simple_type)

    restriction = etree.SubElement(simple_type, '{%s}restriction' % _ns_xsd)
    restriction.set('base', cls.__base_type__.get_type_name_ns(interface))

    for v in cls.Attributes.values:
        enumeration = etree.SubElement(restriction,
                                                '{%s}enumeration' % _ns_xsd)
        enumeration.set('value', str(v))

    return restriction

def simple_add(interface, cls):
    if not interface.has_class(cls) and not cls.is_default(cls):
        interface.get_restriction_tag(cls)
