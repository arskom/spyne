
#
# soaplib - Copyright (C) Soaplib contributors.
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

from soaplib.core.util.odict import odict

def root_dict_to_etree(d):
    assert len(d) == 1

    retval = etree.Element(d.keys()[0])
    for val in d.values():
        break

    if isinstance(val, dict) or isinstance(val, odict):
        dict_to_etree(retval, val)
    else:
        for a in val:
            dict_to_etree(retval, a)

    return retval

def dict_to_etree(parent, d):
    """the dict values are either dicts or iterables"""

    for k, v in d.items():
        if len(v) == 0:
            etree.SubElement(parent,k)

        elif isinstance(v, dict) or isinstance(v, odict):
            child = etree.SubElement(parent,k)
            dict_to_etree(child,v)

        else:
            for e in v:
                child=etree.SubElement(parent,k)
                if isinstance(e, dict) or isinstance(e, odict):
                    dict_to_etree(child,e)
                else:
                    child.text=str(e)

def root_etree_to_dict(element, iterable=(list, list.append)):
    return {element.tag: [etree_to_dict(element)]}

def etree_to_dict(element, iterable=(list,list.append)):
    if (element.text is None) or element.text.isspace():
        retval = odict()
        for elt in element:
            if not (elt.tag in retval):
                retval[elt.tag] = iterable[0]()
            iterable[1](retval[elt.tag], etree_to_dict(elt, iterable))

    else:
        retval = element.text

    return retval
