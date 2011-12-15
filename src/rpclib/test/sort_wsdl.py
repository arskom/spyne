#!/usr/bin/python
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

"""Quick hack to sort the wsdl. it's helpful when comparing the wsdl output
from two rpclib versions.
"""

ns_wsdl = "http://schemas.xmlsoap.org/wsdl/"
ns_schema = "http://www.w3.org/2001/XMLSchema"

import sys

from lxml import etree

def cache_order(l, ns):
    return dict([ ("{%s}%s" % (ns, a), l.index(a)) for a in l])

wsdl_order = ('types', 'message', 'service', 'portType', 'binding')
wsdl_order = cache_order(wsdl_order, ns_wsdl)

schema_order = ('import', 'element', 'simpleType', 'complexType')
schema_order = cache_order(schema_order, ns_schema)

parser = etree.XMLParser(remove_blank_text=True)

def main():
    tree = etree.parse(sys.stdin, parser=parser)

    l0 = []
    type_node = None

    for e in tree.getroot():
        if e.tag == "{%s}types" % ns_wsdl:
            assert type_node is None
            type_node = e
        else:
            l0.append(e)
            e.getparent().remove(e)

    l0.sort(key=lambda e: (wsdl_order[e.tag], e.attrib['name']))
    for e in l0:
        tree.getroot().append(e)

    for e in tree.getroot():
        if e.tag in ("{%s}portType" % ns_wsdl, "{%s}binding" % ns_wsdl, "{%s}operation" % ns_wsdl):
            nodes = []
            for p in e.getchildren():
                nodes.append(p)

            nodes.sort(key=lambda e: e.attrib.get('name', '0'))

            for p in nodes:
                e.append(p)

    schemas = []

    for e in type_node:
        schemas.append(e)
        e.getparent().remove(e)

    schemas.sort(key=lambda e: e.attrib["targetNamespace"])

    for s in schemas:
        type_node.append(s)

    for s in schemas:
        nodes = []
        for e in s:
            nodes.append(e)
            e.getparent().remove(e)

        nodes.sort(key=lambda e: (schema_order[e.tag], e.attrib.get('name', '\0')))

        for e in nodes:
            s.append(e)

    tree.write(sys.stdout, encoding="UTF-8", xml_declaration=True)

    return 0

if __name__ == '__main__':
    sys.exit(main())
