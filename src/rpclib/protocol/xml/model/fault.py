
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
_ns_soap_env = rpclib.const.xml_ns.soap_env

_pref_soap_env = rpclib.const.xml_ns.const_prefmap[_ns_soap_env]


def fault_to_parent_element(prot, cls, value, tns, parent_elt, name=None):
    element = etree.SubElement(parent_elt, "{%s}Fault" % _ns_soap_env)

    etree.SubElement(element, 'faultcode').text = '%s:%s' % (_pref_soap_env, value.faultcode)
    etree.SubElement(element, 'faultstring').text = value.faultstring
    etree.SubElement(element, 'faultactor').text = value.faultactor
    if value.detail != None:
        etree.SubElement(element, 'detail').append(value.detail)


def fault_from_element(prot, cls, element):
    code = element.find('faultcode').text
    string = element.find('faultstring').text
    factor = element.find('faultactor').text
    detail = element.find('detail')

    return cls(faultcode=code, faultstring=string, faultactor=factor,
                                                                  detail=detail)
