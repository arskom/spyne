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

"""This module contains the utility methods that convert an ElementTree
hierarchy to python dicts and vice versa.
"""

try:
    from collections.abc import Sized
except ImportError:  # Python 2
    from collections import Sized

from lxml import etree

from spyne.util import six
from spyne.util.odict import odict


def root_dict_to_etree(d):
    """Converts a dictionary to an xml hiearchy. Just like a valid xml document,
    the dictionary must have a single element. The format of the child
    dictionaries is the same as :func:`dict_to_etree`.
    """

    assert len(d) == 1, "Incoming dict len must be exactly 1. Data: %r" % d

    key, = d.keys()
    retval = etree.Element(key)
    for val in d.values():
        break

    if val is None:
        return retval

    if isinstance(val, dict) or isinstance(val, odict):
        dict_to_etree(val, retval)
    elif not isinstance(val, Sized) or isinstance(val, six.string_types):
        retval.text = str(val)
    else:
        for a in val:
            dict_to_etree(a, retval)

    return retval


def dict_to_etree(d, parent):
    """Takes a the dict whose value is either None or an instance of dict, odict
    or an iterable. The iterables can contain either other dicts/odicts or
    str/unicode instances.
    """

    for k, v in d.items():
        if v is None:
            etree.SubElement(parent, k)

        elif isinstance(v, six.string_types):
            etree.SubElement(parent, k).text = v

        elif isinstance(v, dict) or isinstance(v, odict):
            child = etree.SubElement(parent, k)
            dict_to_etree(v, child)

        elif not isinstance(v, Sized):
            etree.SubElement(parent, k).text = str(v)

        elif len(v) == 0:
            etree.SubElement(parent, k)

        else:
            for e in v:
                child = etree.SubElement(parent, k)
                if isinstance(e, dict) or isinstance(e, odict):
                    dict_to_etree(e, child)
                else:
                    child.text = str(e)


def root_etree_to_dict(element, iterable=(list, list.append)):
    """Takes an xml root element and returns the corresponding dict. The second
    argument is a pair of iterable type and the function used to add elements to
    the iterable. The xml attributes are ignored.
    """

    return {element.tag: iterable[0]([etree_to_dict(element, iterable)])}


def etree_to_dict(element, iterable=(list, list.append)):
    """Takes an xml root element and returns the corresponding dict. The second
    argument is a pair of iterable type and the function used to add elements to
    the iterable. The xml attributes are ignored.
    """

    if (element.text is None) or element.text.isspace():
        retval = odict()
        for elt in element:
            if not (elt.tag in retval):
                retval[elt.tag] = iterable[0]()
            iterable[1](retval[elt.tag], etree_to_dict(elt, iterable))

    else:
        retval = element.text

    return retval


def etree_strip_namespaces(element):
    """Removes any namespace information form the given element recursively."""

    retval = etree.Element(element.tag.rpartition('}')[-1])
    retval.text = element.text
    for a in element.attrib:
        retval.attrib[a.rpartition('}')[-1]] = element.attrib[a]

    for e in element:
        retval.append(etree_strip_namespaces(e))

    return retval
