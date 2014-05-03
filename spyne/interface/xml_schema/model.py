
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

from collections import deque
from collections import defaultdict

from spyne.const.xml_ns import xsd as _ns_xsd

from spyne.model.complex import XmlAttribute
from spyne.model.primitive import AnyXml
from spyne.model.primitive import Unicode
from spyne.protocol.xml import XmlDocument
_prot = XmlDocument()

from spyne.util import memoize
from spyne.util.etreeconv import dict_to_etree


def xml_attribute_add(cls, name, element, document):
    element.set('name', name)
    element.set('type', cls.type.get_type_name_ns(document.interface))

    if cls._use is not None:
        element.set('use', cls._use)

    d = cls.type.Attributes.default

    if d is not None:
        element.set('default', _prot.to_string(cls.type, d))


def simple_get_restriction_tag(document, cls):
    simple_type = etree.Element('{%s}simpleType' % _ns_xsd)

    simple_type.set('name', cls.get_type_name())
    document.add_simple_type(cls, simple_type)

    restriction = etree.SubElement(simple_type, '{%s}restriction' % _ns_xsd)
    restriction.set('base', cls.__extends__.get_type_name_ns(
                                                            document.interface))

    for v in cls.Attributes.values:
        enumeration = etree.SubElement(restriction, '{%s}enumeration' % _ns_xsd)
        enumeration.set('value', str(v))

    return restriction


def simple_add(document, cls, tags):
    if not cls.is_default(cls):
        document.get_restriction_tag(cls)

def byte_array_add(interface, cls, tags):
    simple_add(interface, cls, tags)


def complex_add(document, cls, tags):
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
                    % (cls, extends, cls.get_namespace(), cls.get_type_name()))

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

    sequence = etree.Element('{%s}sequence' % _ns_xsd)

    deferred = deque()
    choice_tags = defaultdict(lambda: etree.Element('{%s}choice' % _ns_xsd))
    for k, v in type_info.items():
        a = v.Attributes
        if a.exc_interface:
            continue

        if issubclass(v, XmlAttribute):
            deferred.append((k,v))
            continue

        document.add(v, tags)

        name = a.sub_name
        if name is None:
            name = k
        #ns = a.sub_ns
        #if ns is not None:
        #    name = "{%s}%s" % (ns, name)

        member = etree.Element(a.schema_tag)
        if a.schema_tag == '{%s}element' % _ns_xsd:
            member.set('name', name)
            member.set('type', v.get_type_name_ns(document.interface))

        elif a.schema_tag == '{%s}any' % _ns_xsd and issubclass(v, AnyXml):
            if a.namespace is not None:
                member.set('namespace', a.namespace)
            if a.process_contents is not None:
                member.set('processContents', a.process_contents)

        else:
            raise ValueError("Unhandled schema_tag / type combination. %r %r"
                    % (v, a.schema_tag))

        if a.min_occurs != 1:  # 1 is the xml schema default
            member.set('minOccurs', str(a.min_occurs))

        if a.max_occurs != 1:  # 1 is the xml schema default
            val = a.max_occurs
            if val in (decimal.Decimal('inf'), float('inf')):
                val = 'unbounded'
            else:
                val = str(val)

            member.set('maxOccurs', val)

        if a.default is not None:
            member.set('default', _prot.to_string(v, a.default))

        if bool(a.nillable) != False: # False is the xml schema default
            member.set('nillable', 'true')

        if v.Annotations.doc != '':
            # Doesn't support multi-language documentation
            annotation = etree.SubElement(member, "{%s}annotation" % _ns_xsd)

            doc = etree.SubElement(annotation, "{%s}documentation" % _ns_xsd)
            doc.text = v.Annotations.doc

        if a.xml_choice_group is None:
            sequence.append(member)
        else:
            choice_tags[a.xml_choice_group].append(member)

    sequence.extend(choice_tags.values())

    if len(sequence) > 0:
        sequence_parent.append(sequence)

    _ext_elements = dict()
    for k,v in deferred:
        ao = v.attribute_of
        if ao is None: # others will be added at a later loop
            attribute = etree.SubElement(complex_type,'{%s}attribute' % _ns_xsd)
            xml_attribute_add(v, k, attribute, document)
            continue

        elts = complex_type.xpath("//xsd:element[@name='%s']" % ao,
                                                    namespaces={'xsd': _ns_xsd})

        if len(elts) == 0:
            raise ValueError("Element %r not found for XmlAttribute %r." %
                                                                        (ao, k))
        elif len(elts) > 1:
            raise Exception("Xpath returned more than one element %r "
                          "for %r. Not sure what's going on here." % (elts, ao))

        else:
            elt = elts[0]

        _ext = _ext_elements.get(ao, None)
        if _ext is None:
            _ct = etree.SubElement(elt, '{%s}complexType' % _ns_xsd)
            _sc = etree.SubElement(_ct, '{%s}simpleContent' % _ns_xsd)
            _ext = etree.SubElement(_sc, '{%s}extension' % _ns_xsd)
            _ext_elements[ao] = _ext
            _ext.attrib['base'] = elt.attrib['type']
            del elt.attrib['type']

        attribute = etree.SubElement(_ext, '{%s}attribute' % _ns_xsd)
        xml_attribute_add(v, k, attribute, document)

    document.add_complex_type(cls, complex_type)

    # simple node
    complex_type_name = cls.Attributes.sub_name or cls.get_type_name()
    element = etree.Element('{%s}element' % _ns_xsd)
    element.set('name', complex_type_name)
    element.set('type', cls.get_type_name_ns(document.interface))

    document.add_element(cls, element)


def enum_add(document, cls, tags):
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

fault_add = complex_add


def unicode_get_restriction_tag(interface, cls):
    restriction = simple_get_restriction_tag(interface, cls)

    # length
    if cls.Attributes.min_len == cls.Attributes.max_len:
        length = etree.SubElement(restriction, '{%s}length' % _ns_xsd)
        length.set('value', str(cls.Attributes.min_len))

    else:
        if cls.Attributes.min_len != Unicode.Attributes.min_len:
            min_l = etree.SubElement(restriction, '{%s}minLength' % _ns_xsd)
            min_l.set('value', str(cls.Attributes.min_len))

        if cls.Attributes.max_len != Unicode.Attributes.max_len:
            max_l = etree.SubElement(restriction, '{%s}maxLength' % _ns_xsd)
            max_l.set('value', str(cls.Attributes.max_len))

    # pattern
    if cls.Attributes.pattern != Unicode.Attributes.pattern:
        pattern = etree.SubElement(restriction, '{%s}pattern' % _ns_xsd)
        pattern.set('value', cls.Attributes.pattern)

    return restriction


@memoize
def Tget_range_restriction_tag(T):
    """The get_range_restriction template function. Takes a primitive, returns
    a function that generates range restriction tags.
    """

    from spyne.model.primitive import Decimal
    from spyne.model.primitive import Integer

    if issubclass(T, Decimal):
        def _get_float_restrictions(prot, restriction, cls):
            if cls.Attributes.fraction_digits != T.Attributes.fraction_digits:
                elt = etree.SubElement(restriction, '{%s}fractionDigits' % _ns_xsd)
                elt.set('value', prot.to_string(cls, cls.Attributes.fraction_digits))

        def _get_integer_restrictions(prot, restriction, cls):
            if cls.Attributes.total_digits != T.Attributes.total_digits:
                elt = etree.SubElement(restriction, '{%s}totalDigits' % _ns_xsd)
                elt.set('value', prot.to_string(cls, cls.Attributes.total_digits))

        if issubclass(T, Integer):
            def _get_additional_restrictions(prot, restriction, cls):
                _get_integer_restrictions(prot, restriction, cls)

        else:
            def _get_additional_restrictions(prot, restriction, cls):
                _get_integer_restrictions(prot, restriction, cls)
                _get_float_restrictions(prot, restriction, cls)

    else:
        def _get_additional_restrictions(prot, restriction, cls):
            pass

    def _get_range_restriction_tag(document, cls):
        prot = document.interface.app.in_protocol
        restriction = simple_get_restriction_tag(document, cls)

        if cls.Attributes.gt != T.Attributes.gt:
            elt = etree.SubElement(restriction, '{%s}minExclusive' % _ns_xsd)
            elt.set('value', prot.to_string(cls, cls.Attributes.gt))

        if cls.Attributes.ge != T.Attributes.ge:
            elt = etree.SubElement(restriction, '{%s}minInclusive' % _ns_xsd)
            elt.set('value', prot.to_string(cls, cls.Attributes.ge))

        if cls.Attributes.lt != T.Attributes.lt:
            elt = etree.SubElement(restriction, '{%s}maxExclusive' % _ns_xsd)
            elt.set('value', prot.to_string(cls, cls.Attributes.lt))

        if cls.Attributes.le != T.Attributes.le:
            elt = etree.SubElement(restriction, '{%s}maxInclusive' % _ns_xsd)
            elt.set('value', prot.to_string(cls, cls.Attributes.le))

        if cls.Attributes.pattern != T.Attributes.pattern:
            elt = etree.SubElement(restriction, '{%s}pattern' % _ns_xsd)
            elt.set('value', cls.Attributes.pattern)

        _get_additional_restrictions(prot, restriction, cls)

        return restriction

    return _get_range_restriction_tag
