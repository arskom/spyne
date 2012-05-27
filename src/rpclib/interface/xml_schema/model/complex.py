
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

from rpclib.const import xml_ns as namespace
from rpclib.model.complex import XmlAttribute
from rpclib.model.primitive import AnyXml
from rpclib.util.etreeconv import dict_to_etree

def complex_add(document, cls):
    complex_type = etree.Element("{%s}complexType" % namespace.xsd)
    complex_type.set('name', cls.get_type_name())

    if cls.Annotations.doc != '' or cls.Annotations.appinfo != None:
        annotation = etree.SubElement(complex_type, "{%s}annotation" %
                                                              namespace.xsd)
        if cls.Annotations.doc != '':
            doc = etree.SubElement(annotation, "{%s}documentation" %
                                                              namespace.xsd)
            doc.text = cls.Annotations.doc

        _ai = cls.Annotations.appinfo;
        if _ai != None:
            appinfo = etree.SubElement(annotation, "{%s}appinfo" %
                                                              namespace.xsd)
            if isinstance(_ai, dict):
                dict_to_etree(_ai, appinfo)
            elif isinstance(_ai, str) or isinstance(_ai, unicode):
                appinfo.text = _ai
            elif isinstance(_ai, etree._Element):
                appinfo.append(_ai)
            else:
                from rpclib.util.xml import get_object_as_xml

                appinfo.append(get_object_as_xml(_ai))

    sequence_parent = complex_type
    extends = getattr(cls, '__extends__', None)
    if not (extends is None):
        if (extends.get_type_name() == cls.get_type_name() and
                                extends.get_namespace() == cls.get_namespace()):
            raise Exception("%r can't extend %r because they are all '{%s}%s'"
                    % (cls, extends, cls.get_type_name(), cls.get_namespace()))

        else:
            complex_content = etree.SubElement(complex_type,
                                       "{%s}complexContent" % namespace.xsd)
            extension = etree.SubElement(complex_content,
                                       "{%s}extension" % namespace.xsd)
            extension.set('base', extends.get_type_name_ns(document.interface))
            sequence_parent = extension

    sequence = etree.SubElement(sequence_parent, '{%s}sequence' %
                                                              namespace.xsd)

    for k, v in cls._type_info.items():
        if issubclass(v, XmlAttribute):
            attribute = etree.SubElement(complex_type,
                                        '{%s}attribute' % namespace.xsd)
            v.describe(k, attribute, document)
            continue

        if not issubclass(v, cls):
            document.add(v)

        member = etree.SubElement(sequence, v.Attributes.schema_tag)
        if v.Attributes.schema_tag == '{%s}element' % namespace.xsd:
            member.set('name', k)
            member.set('type', v.get_type_name_ns(document.interface))

        elif v.Attributes.schema_tag == '{%s}any' % namespace.xsd and \
                                                    (issubclass(v, AnyXml)):
            if v.Attributes.namespace is not None:
                member.set('namespace', v.Attributes.namespace)
            if v.Attributes.process_contents is not None:
                member.set('processContents', v.Attributes.process_contents)

        else:
            raise ValueError("Unhandled schema_tag / type combination. %r %r"
                    % (v, v.Attributes.schema_tag))

        if v.Attributes.min_occurs != 1: # 1 is the xml schema default
            member.set('minOccurs', str(v.Attributes.min_occurs))
        if v.Attributes.max_occurs != 1: # 1 is the xml schema default
            val = v.Attributes.max_occurs
            if val == float('inf'):
                val = 'unbounded'
            else:
                val = str(val)

            member.set('maxOccurs', val)

        if bool(v.Attributes.nillable) != False: # False is the xml schema default
            member.set('nillable', 'true')

    document.add_complex_type(cls, complex_type)

    # simple node
    element = etree.Element('{%s}element' % namespace.xsd)
    element.set('name', cls.get_type_name())
    element.set('type', cls.get_type_name_ns(document.interface))

    document.add_element(cls, element)

def alias_add(document, cls):
    element = etree.Element('{%s}element' % namespace.xsd)
    element.set('name', cls.get_type_name())
    element.set('type', cls._target.get_type_name_ns(document.interface))

    document.add_element(cls, element)
