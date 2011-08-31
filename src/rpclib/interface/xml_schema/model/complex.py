
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

from rpclib.const import xml_ns as namespace
from rpclib.model import ModelBase
from rpclib.model.complex import XMLAttribute

def complex_add(interface, cls):
    if cls.get_type_name() is ModelBase.Empty:
        (child, ) = cls._type_info.values()
        cls.__type_name__ = '%sArray' % child.get_type_name()

    if not interface.has_class(cls):
        extends = getattr(cls, '__extends__', None)
        if not (extends is None):
            interface.add(extends)

        complex_type = etree.Element("{%s}complexType" % namespace.xsd)
        complex_type.set('name', cls.get_type_name())

        sequence_parent = complex_type
        if not (extends is None):
            complex_content = etree.SubElement(complex_type,
                                       "{%s}complexContent" % namespace.xsd)
            extension = etree.SubElement(complex_content,
                                       "{%s}extension" % namespace.xsd)
            extension.set('base', extends.get_type_name_ns(interface))
            sequence_parent = extension

        sequence = etree.SubElement(sequence_parent, '{%s}sequence' %
                                                                 namespace.xsd)

        for k, v in cls._type_info.items():
            if isinstance(v, XMLAttribute):
                attribute = etree.SubElement(complex_type,
                                            '{%s}attribute' % namespace.xsd)
                v.describe(k, attribute)
                continue

            if v != cls:
                interface.add(v)

            member = etree.SubElement(sequence, '{%s}element' % namespace.xsd)
            member.set('name', k)
            member.set('type', v.get_type_name_ns(interface))

            if v.Attributes.min_occurs != 1: # 1 is the xml schema default
                member.set('minOccurs', str(v.Attributes.min_occurs))
            if v.Attributes.max_occurs != 1: # 1 is the xml schema default
                member.set('maxOccurs', str(v.Attributes.max_occurs))

            if bool(v.Attributes.nillable) == True:
                member.set('nillable', 'true')
            #else:
            #    member.set('nillable', 'false')

            if v.Annotations.doc != '':
                annotation = etree.SubElement(member, "{%s}annotation",
                                                              namespace.xsd)
                doc = etree.SubElement(annotation, "{%s}documentation",
                                                              namespace.xsd)
                doc.text = v.Annotations.doc

        interface.add_complex_type(cls, complex_type)

        # simple node
        element = etree.Element('{%s}element' % namespace.xsd)
        element.set('name', cls.get_type_name())
        element.set('type', cls.get_type_name_ns(interface))

        interface.add_element(cls, element)

def alias_add(interface, cls):
    if not interface.has_class(cls._target):
        interface.add(cls._target)
    element = etree.Element('{%s}element' % namespace.xsd)
    element.set('name', cls.get_type_name())
    element.set('type', cls._target.get_type_name_ns(interface.app))

    interface.add_element(cls, element)
