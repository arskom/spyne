
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

"""The ``spyne.interface.xml_schema.model`` module contains type-specific logic
for schema generation."""

import logging
logger = logging.getLogger(__name__)

import decimal

from lxml import etree

from spyne.model.complex import XmlAttribute
from spyne.model.primitive import AnyXml
from spyne.util.etreeconv import dict_to_etree
from spyne.model.primitive import Unicode
from spyne.util import memoize

from spyne.const.xml_ns import xsd as _ns_xs
from spyne.const.xml_ns import xsd as _ns_xsd


def simple_get_restriction_tag(document, cls):
    simple_type = etree.Element('{%s}simpleType' % _ns_xsd)
    simple_type.set('name', cls.get_type_name())
    document.add_simple_type(cls, simple_type)

    restriction = etree.SubElement(simple_type, '{%s}restriction' % _ns_xsd)
    restriction.set('base', cls.__base_type__.get_type_name_ns(document.interface))

    for v in cls.Attributes.values:
        enumeration = etree.SubElement(restriction, '{%s}enumeration' % _ns_xsd)
        enumeration.set('value', str(v))

    return restriction


def simple_add(interface, cls):
    if not cls.is_default(cls):
        interface.get_restriction_tag(cls)


def complex_add(document, cls):
    complex_type = etree.Element("{%s}complexType" % _ns_xsd)
    complex_type.set('name', cls.get_type_name())

    if cls.Annotations.doc != '' or cls.Annotations.appinfo != None or \
                                             cls.Annotations.__use_parent_doc__:
        annotation = etree.SubElement(complex_type, "{%s}annotation" % _ns_xsd)
        if cls.Annotations.doc != '' or cls.Annotations.__use_parent_doc__:
            doc = etree.SubElement(annotation, "{%s}documentation" % _ns_xsd)
            if cls.Annotations.__use_parent_doc__:
                doc.text = getattr(cls, '__doc__')
            else:
                doc.text = cls.Annotations.doc

        _ai = cls.Annotations.appinfo;
        if _ai != None:
            appinfo = etree.SubElement(annotation, "{%s}appinfo" % _ns_xsd)
            if isinstance(_ai, dict):
                dict_to_etree(_ai, appinfo)
            elif isinstance(_ai, str) or isinstance(_ai, unicode):
                appinfo.text = _ai
            elif isinstance(_ai, etree._Element):
                appinfo.append(_ai)
            else:
                from spyne.util.xml import get_object_as_xml

                appinfo.append(get_object_as_xml(_ai))

    sequence_parent = complex_type
    extends = getattr(cls, '__extends__', None)

    type_info = cls._type_info
    if extends is not None:
        if (extends.get_type_name() == cls.get_type_name() and
                                extends.get_namespace() == cls.get_namespace()):
            raise Exception("%r can't extend %r because they are both '{%s}%s'"
                    % (cls, extends, cls.get_type_name(), cls.get_namespace()))

        if extends.Attributes.exc_interface:
            # If the parent class is private, it won't be in the schema, so we
            # need to act as if its attributes are part of cls as well.
            type_info = cls.get_simple_type_info(cls)
        else:
            complex_content = etree.SubElement(complex_type,
                                                "{%s}complexContent" % _ns_xsd)
            extension = etree.SubElement(complex_content,
                                                    "{%s}extension" % _ns_xsd)
            extension.set('base', extends.get_type_name_ns(document.interface))
            sequence_parent = extension

    sequence = etree.SubElement(sequence_parent, '{%s}sequence' % _ns_xsd)

    for k, v in type_info.items():
        if issubclass(v, XmlAttribute):
            attribute = etree.SubElement(complex_type,
                                        '{%s}attribute' % _ns_xsd)
            v.describe(k, attribute, document)
            continue

        if v.Attributes.exc_interface:
            continue

        if not issubclass(v, cls):
            document.add(v)

        member = etree.SubElement(sequence, v.Attributes.schema_tag)
        if v.Attributes.schema_tag == '{%s}element' % _ns_xsd:
            member.set('name', k)
            member.set('type', v.get_type_name_ns(document.interface))

        elif v.Attributes.schema_tag == '{%s}any' % _ns_xsd and \
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
            if val == decimal.Decimal('inf'):
                val = 'unbounded'
            else:
                val = str(val)

            member.set('maxOccurs', val)

        if bool(v.Attributes.nillable) != False: # False is the xml schema default
            member.set('nillable', 'true')

    document.add_complex_type(cls, complex_type)

    # simple node
    element = etree.Element('{%s}element' % _ns_xsd)
    element.set('name', cls.get_type_name())
    element.set('type', cls.get_type_name_ns(document.interface))

    document.add_element(cls, element)


def alias_add(document, cls):
    t, = cls._type_info.values()
    element = etree.Element('{%s}element' % _ns_xsd)
    element.set('name', cls.get_type_name())
    if t is None:
        etree.SubElement(element, "{%s}complexType" % _ns_xsd)
    else:
        element.set('type', t.get_type_name_ns(document.interface))

    document.add_element(cls, element)


def enum_add(document, cls):
    simple_type = etree.Element('{%s}simpleType' % _ns_xsd)
    simple_type.set('name', cls.get_type_name())

    restriction = etree.SubElement(simple_type,
                                        '{%s}restriction' % _ns_xsd)
    restriction.set('base', '%s:string' %
                            document.interface.get_namespace_prefix(_ns_xsd))

    for v in cls.__values__:
        enumeration = etree.SubElement(restriction,
                                        '{%s}enumeration' % _ns_xsd)
        enumeration.set('value', v)

    document.add_simple_type(cls, simple_type)


def fault_add(document, cls):
    extends = getattr(cls, '__extends__', None)
    if not (extends is None):
        document.add(extends)

    complex_type = etree.Element("{%s}complexType" % _ns_xsd)
    complex_type.set('name', cls.get_type_name())

    #sequence = etree.SubElement(complex_type, '{%s}sequence' % _ns_xsd)

    document.add_complex_type(cls, complex_type)

    # simple node
    element = etree.Element('{%s}element' % _ns_xsd)
    element.set('name', cls.get_type_name())
    element.set('type', cls.get_type_name_ns(document.interface))

    document.add_element(cls, element)


def unicode_get_restriction_tag(interface, cls):
    restriction = simple_get_restriction_tag(interface, cls)

    # length
    if cls.Attributes.min_len == cls.Attributes.max_len:
        length = etree.SubElement(restriction, '{%s}length' % _ns_xs)
        length.set('value', str(cls.Attributes.min_len))

    else:
        if cls.Attributes.min_len != Unicode.Attributes.min_len:
            min_l = etree.SubElement(restriction, '{%s}minLength' % _ns_xs)
            min_l.set('value', str(cls.Attributes.min_len))

        if cls.Attributes.max_len != Unicode.Attributes.max_len:
            max_l = etree.SubElement(restriction, '{%s}maxLength' % _ns_xs)
            max_l.set('value', str(cls.Attributes.max_len))

    # pattern
    if cls.Attributes.pattern != Unicode.Attributes.pattern:
        pattern = etree.SubElement(restriction, '{%s}pattern' % _ns_xs)
        pattern.set('value', cls.Attributes.pattern)

    return restriction


@memoize
def Tget_range_restriction_tag(T):
    def _get_range_restriction_tag(interface, cls):
        restriction = simple_get_restriction_tag(interface, cls)

        if cls.Attributes.gt != T.Attributes.gt:
            min_l = etree.SubElement(restriction, '{%s}minExclusive' % _ns_xs)
            min_l.set('value', cls.to_string(cls.Attributes.gt))

        if cls.Attributes.ge != T.Attributes.ge:
            min_l = etree.SubElement(restriction, '{%s}minInclusive' % _ns_xs)
            min_l.set('value', cls.to_string(cls.Attributes.ge))

        if cls.Attributes.lt != T.Attributes.lt:
            min_l = etree.SubElement(restriction, '{%s}maxExclusive' % _ns_xs)
            min_l.set('value', cls.to_string(cls.Attributes.lt))

        if cls.Attributes.le != T.Attributes.le:
            min_l = etree.SubElement(restriction, '{%s}maxInclusive' % _ns_xs)
            min_l.set('value', cls.to_string(cls.Attributes.le))

        if cls.Attributes.pattern != T.Attributes.pattern:
            pattern = etree.SubElement(restriction, '{%s}pattern' % _ns_xs)
            pattern.set('value', cls.Attributes.pattern)

        return restriction

    return _get_range_restriction_tag
