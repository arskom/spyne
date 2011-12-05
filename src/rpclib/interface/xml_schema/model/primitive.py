
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

from rpclib.const.xml_ns import xsd as _ns_xs
from rpclib.model.primitive import String
from rpclib.model.primitive import Decimal
from rpclib.interface.xml_schema.model._base import simple_get_restriction_tag


def string_get_restriction_tag(interface, cls):
    restriction = simple_get_restriction_tag(interface, cls)

    # length
    if cls.Attributes.min_len == cls.Attributes.max_len:
        length = etree.SubElement(restriction, '{%s}length' % _ns_xs)
        length.set('value', str(cls.Attributes.min_len))

    else:
        if cls.Attributes.min_len != String.Attributes.min_len:
            min_l = etree.SubElement(restriction, '{%s}minLength' % _ns_xs)
            min_l.set('value', str(cls.Attributes.min_len))

        if cls.Attributes.max_len != String.Attributes.max_len:
            max_l = etree.SubElement(restriction, '{%s}maxLength' % _ns_xs)
            max_l.set('value', str(cls.Attributes.max_len))

    # pattern
    if cls.Attributes.pattern != String.Attributes.pattern:
        pattern = etree.SubElement(restriction, '{%s}pattern' % _ns_xs)
        pattern.set('value', cls.Attributes.pattern)

    return restriction

def decimal_get_restriction_tag(interface, cls):
    restriction = simple_get_restriction_tag(interface, cls)

    if cls.Attributes.gt != Decimal.Attributes.gt:
        min_l = etree.SubElement(restriction, '{%s}minExclusive' % _ns_xs)
        min_l.set('value', str(cls.Attributes.gt))

    if cls.Attributes.ge != Decimal.Attributes.ge:
        min_l = etree.SubElement(restriction, '{%s}minInclusive' % _ns_xs)
        min_l.set('value', str(cls.Attributes.ge))

    if cls.Attributes.lt != Decimal.Attributes.lt:
        min_l = etree.SubElement(restriction, '{%s}maxExclusive' % _ns_xs)
        min_l.set('value', str(cls.Attributes.lt))

    if cls.Attributes.le != Decimal.Attributes.le:
        min_l = etree.SubElement(restriction, '{%s}maxInclusive' % _ns_xs)
        min_l.set('value', str(cls.Attributes.le))

    return restriction
