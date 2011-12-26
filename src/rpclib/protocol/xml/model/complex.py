
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

import logging
logger = logging.getLogger(__name__)

from lxml import etree

from rpclib.error import Fault
from rpclib.model.complex import XMLAttribute # FIXME: Rename this to XmlAttribute
from rpclib.protocol.xml.model._base import nillable_value
from rpclib.protocol.xml.model._base import nillable_element


def get_members_etree(prot, cls, inst, parent):
    parent_cls = getattr(cls, '__extends__', None)
    if not (parent_cls is None):
        get_members_etree(prot, parent_cls, inst, parent)

    for k, v in cls._type_info.items():
        try:
            subvalue = getattr(inst, k, None)
        except: # to guard against sqlalchemy throwing NoSuchColumnError
            subvalue = None

        if isinstance(v, XMLAttribute):
            v.marshall(k, subvalue, parent)
            continue

        mo = v.Attributes.max_occurs
        if subvalue is not None and (mo == 'unbounded' or mo > 1):
            for sv in subvalue:
                prot.to_parent_element(v, sv, cls.get_namespace(), parent, k)

        # Don't include empty values for non-nillable optional attributes.
        elif subvalue is not None or (not v.Attributes.nillable or v.Attributes.min_occurs > 0):
            prot.to_parent_element(v, subvalue, cls.get_namespace(), parent, k)


@nillable_value
def complex_to_parent_element(prot, cls, value, tns, parent_elt, name=None):
    if name is None:
        name = cls.get_type_name()

    element = etree.SubElement(parent_elt, "{%s}%s" % (tns, name))
    inst = cls.get_serialization_instance(value)

    get_members_etree(prot, cls, inst, element)


@nillable_element
def complex_from_element(prot, cls, element):
    inst = cls.get_deserialization_instance()

    flat_type_info = cls.get_flat_type_info(cls)

    # initialize instance
    for k in flat_type_info:
        setattr(inst, k, None)

    # this is for validating cls.Attributes.{min,max}_occurs
    frequencies = {}

    # parse input to set incoming data to related attributes.
    for c in element:
        if isinstance(c, etree._Comment):
            continue

        key = c.tag.split('}')[-1]
        freq = frequencies.get(key, 0)
        freq+=1
        frequencies[key] = freq


        member = flat_type_info.get(key, None)
        if member is None:
            continue

        if isinstance(member, XMLAttribute):
            value = element.get(key)

        else:
            mo = member.Attributes.max_occurs
            if mo == 'unbounded' or mo > 1:
                value = getattr(inst, key, None)
                if value is None:
                    value = []

                value.append(prot.from_element(member, c))

            else:
                value = prot.from_element(member, c)

        setattr(inst, key, value)

    if prot.validator is prot.SOFT_VALIDATION:
        for key, c in flat_type_info.items():
            val = frequencies.get(key, 0)
            if (        val < c.Attributes.min_occurs
                    or  (     c.Attributes.max_occurs != 'unbounded'
                          and val > c.Attributes.max_occurs )):
                raise Fault('Client.ValidationError',
                    '%r member does not respect frequency constraints' % key)

    return inst


@nillable_element
def array_from_element(prot, cls, element):
    retval = [ ]
    (serializer,) = cls._type_info.values()

    for child in element.getchildren():
        retval.append(prot.from_element(serializer, child))

    return retval


@nillable_element
def iterable_from_element(prot, cls, element):
    (serializer,) = cls._type_info.values()

    for child in element.getchildren():
        yield prot.from_element(serializer, child)
