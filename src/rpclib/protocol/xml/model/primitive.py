
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

from rpclib.util.etreeconv import etree_to_dict
from rpclib.util.etreeconv import dict_to_etree
from rpclib.protocol.xml.model._base import nillable_value
from rpclib.protocol.xml.model._base import nillable_element

@nillable_element
def xml_from_element(prot, cls, element):
    children = element.getchildren()
    retval = None

    if children:
        retval = element.getchildren()[0]

    return retval

@nillable_value
def xml_to_parent_element(prot, cls, value, tns, parent_elt, name='retval'):
    if isinstance(value, str) or isinstance(value, unicode):
        value = etree.fromstring(value)

    e = etree.SubElement(parent_elt, '{%s}%s' % (tns, name))
    e.append(value)

@nillable_value
def dict_to_parent_element(prot, cls, value, tns, parent_elt, name='retval'):
    e = etree.SubElement(parent_elt, '{%s}%s' % (tns, name))
    dict_to_etree(value, e)

@nillable_element
def dict_from_element(prot, cls, element):
    children = element.getchildren()
    if children:
        return etree_to_dict(element)

    return None
