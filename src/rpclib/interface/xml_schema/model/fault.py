
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

def fault_add(interface, cls):
    if not interface.has_class(cls):
        extends = getattr(cls, '__extends__', None)
        if not (extends is None):
            interface.add(extends)

        complex_type = etree.Element("{%s}complexType" % _ns_xsd)
        complex_type.set('name', cls.get_type_name())

        #sequence = etree.SubElement(complex_type, '{%s}sequence' % _ns_xsd)

        interface.add_complex_type(cls, complex_type)

        # simple node
        element = etree.Element('{%s}element' % _ns_xsd)
        element.set('name', cls.get_type_name())
        element.set('type', cls.get_type_name_ns(interface))

        interface.add_element(cls, element)
