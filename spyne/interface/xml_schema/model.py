
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

from decimal import Decimal as D
from collections import deque, defaultdict

from lxml import etree

from spyne.model import ModelBase, XmlAttribute, AnyXml, Unicode, XmlData, \
    Decimal, Integer
from spyne.const.xml import NS_XSD, XSD
from spyne.util import memoize
from spyne.util.cdict import cdict
from spyne.util.etreeconv import dict_to_etree
from spyne.util.six import string_types
from spyne.protocol.xml import XmlDocument
_prot = XmlDocument()

# In Xml Schema, some customizations do not need a class to be extended -- they
# are specified in-line in the parent class definition, like nullable or
# min_occurs. The dict below contains list of parameters that do warrant a
# proper subclass definition for each type. This must be updated as the Xml
# Schema implementation makes progress.
ATTR_NAMES = cdict({
    ModelBase: set(['values']),
    Decimal: set(['pattern', 'gt', 'ge', 'lt', 'le', 'values', 'total_digits',
                                                            'fraction_digits']),
    Integer: set(['pattern', 'gt', 'ge', 'lt', 'le', 'values', 'total_digits']),
    Unicode: set(['values', 'min_len', 'max_len', 'pattern']),
})

def xml_attribute_add(cls, name, element, document):
    element.set('name', name)
    element.set('type', cls.type.get_type_name_ns(document.interface))

    if cls._use is not None:
        element.set('use', cls._use)

    d = cls.type.Attributes.default

    if d is not None:
        element.set('default', _prot.to_unicode(cls.type, d))


def _check_extension_attrs(cls):
    """Make sure only customizations that need a restriction tag generate one"""

    extends = cls.__extends__

    eattrs = extends.Attributes
    cattrs = cls.Attributes

    ckeys = set([k for k in vars(cls.Attributes) if not k.startswith('_')])
    ekeys = set([k for k in vars(extends.Attributes) if not k.startswith('_')])

    # get the attributes different from the parent class
    diff = set()
    for k in (ckeys | ekeys):
        if getattr(eattrs, k, None) != getattr(cattrs, k, None):
            diff.add(k)

    # compare them with what comes from ATTR_NAMES
    attr_names = ATTR_NAMES[cls]
    retval = None
    while extends is not None:
        retval = extends
        if len(diff & attr_names) > 0:
            return extends
        extends = extends.__extends__

    return retval

# noinspection PyDefaultArgument
def simple_get_restriction_tag(document, cls):
    extends = _check_extension_attrs(cls)
    if extends is None:
        return

    simple_type = etree.Element(XSD('simpleType'))

    simple_type.set('name', cls.get_type_name())
    document.add_simple_type(cls, simple_type)

    restriction = etree.SubElement(simple_type, XSD('restriction'))
    restriction.set('base', extends.get_type_name_ns(document.interface))

    for v in cls.Attributes.values:
        enumeration = etree.SubElement(restriction, XSD('enumeration'))
        enumeration.set('value', XmlDocument().to_unicode(cls, v))

    return restriction


def simple_add(document, cls, tags):
    if not cls.is_default(cls):
        document.get_restriction_tag(cls)

def byte_array_add(document, cls, tags):
    simple_add(document, cls, tags)


def complex_add(document, cls, tags):
    complex_type = etree.Element(XSD('complexType'))
    complex_type.set('name', cls.get_type_name())

    doc_text = cls.get_documentation()
    if doc_text or cls.Annotations.appinfo is not None:
        annotation = etree.SubElement(complex_type, XSD('annotation'))
        if doc_text:
            doc = etree.SubElement(annotation, XSD('documentation'))
            doc.text = doc_text

        _ai = cls.Annotations.appinfo
        if _ai is not None:
            appinfo = etree.SubElement(annotation, XSD('appinfo'))
            if isinstance(_ai, dict):
                dict_to_etree(_ai, appinfo)

            elif isinstance(_ai, string_types):
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
                                                          XSD('complexContent'))
            extension = etree.SubElement(complex_content, XSD('extension'))
            extension.set('base', extends.get_type_name_ns(document.interface))
            sequence_parent = extension

    if cls.Attributes._xml_tag_body_as is not None:
        for xtba_key, xtba_type in cls.Attributes._xml_tag_body_as:
            _sc = etree.SubElement(sequence_parent, XSD('simpleContent'))
            xtba_ext = etree.SubElement(_sc, XSD('extension'))
            xtba_ext.attrib['base'] = xtba_type.type.get_type_name_ns(
                                                             document.interface)

    sequence = etree.Element(XSD('sequence'))

    deferred = deque()
    choice_tags = defaultdict(lambda: etree.Element(XSD('choice')))
    all_tags = defaultdict(lambda: etree.Element(XSD('all')))

    for k, v in type_info.items():
        assert isinstance(k, string_types)
        assert issubclass(v, ModelBase)

        a = v.Attributes
        if a.exc_interface:
            continue

        if issubclass(v, XmlData):
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

        type_name_ns = v.get_type_name_ns(document.interface)
        if v.__extends__ is not None and v.__orig__ is not None and \
                                              _check_extension_attrs(v) is None:
            type_name_ns = v.__orig__.get_type_name_ns(document.interface)

        member = etree.Element(a.schema_tag)
        if a.schema_tag == XSD('element'):
            member.set('name', name)
            member.set('type', type_name_ns)

        elif a.schema_tag == XSD('any') and issubclass(v, AnyXml):
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
            if val in (D('inf'), float('inf')):
                val = 'unbounded'
            else:
                val = str(val)

            member.set('maxOccurs', val)

        if a.default is not None:
            member.set('default', _prot.to_unicode(v, a.default))

        if bool(a.nillable) != False: # False is the xml schema default
            member.set('nillable', 'true')

        v_doc_text = v.get_documentation()
        if v_doc_text:
            # Doesn't support multi-language documentation
            annotation = etree.SubElement(member, XSD('annotation'))
            doc = etree.SubElement(annotation, XSD('documentation'))
            doc.text = v_doc_text

        if all([a.xml_choice_group, a.xml_all_group]):
            raise ValueError("Cannot specify xml_choice_group and xml_all_group"
                             " at the same time. Class: %r. Groups: %r"
                             % (cls.__name__,
                                [a.xml_choice_group, a.xml_all_group]))
        elif a.xml_choice_group is not None:
            choice_tags[a.xml_choice_group].append(member)
        elif a.xml_all_group is not None:
            all_tags[a.xml_all_group].append(member)
        else:
            sequence.append(member)

    sequence.extend(choice_tags.values())

    if len(sequence) == 0:
        if len(all_tags) > 1:
            raise ValueError("Cannot specify more than one xml_all_group"
                             " at the same time. Class: %r. Groups: %r"
                             % (cls.__name__, [key for key in all_tags.keys()]))
        sequence_parent.extend(all_tags.values())
    else:
        sequence_parent.append(sequence)

    _ext_elements = dict()
    for k,v in deferred:
        attribute = etree.Element(XSD('attribute'))
        xml_attribute_add(v, k, attribute, document)

        if cls.Attributes._xml_tag_body_as is None:
            sequence_parent.append(attribute)
        else:
            xtba_ext.append(attribute)

    document.add_complex_type(cls, complex_type)

    # simple node
    complex_type_name = cls.Attributes.sub_name or cls.get_type_name()
    element = etree.Element(XSD('element'))
    element.set('name', complex_type_name)
    element.set('type', cls.get_type_name_ns(document.interface))

    document.add_element(cls, element)


def enum_add(document, cls, tags):
    simple_type = etree.Element(XSD('simpleType'))
    simple_type.set('name', cls.get_type_name())

    restriction = etree.SubElement(simple_type, XSD('restriction'))
    restriction.set('base', '%s:string' %
                               document.interface.get_namespace_prefix(NS_XSD))

    for v in cls.__values__:
        enumeration = etree.SubElement(restriction, XSD('enumeration'))
        enumeration.set('value', v)

    document.add_simple_type(cls, simple_type)

fault_add = complex_add


def unicode_get_restriction_tag(document, cls):
    restriction = simple_get_restriction_tag(document, cls)
    if restriction is None:
        return

    # length
    if cls.Attributes.min_len == cls.Attributes.max_len:
        length = etree.SubElement(restriction, XSD('length'))
        length.set('value', str(cls.Attributes.min_len))

    else:
        if cls.Attributes.min_len != Unicode.Attributes.min_len:
            min_l = etree.SubElement(restriction, XSD('minLength'))
            min_l.set('value', str(cls.Attributes.min_len))

        if cls.Attributes.max_len != Unicode.Attributes.max_len:
            max_l = etree.SubElement(restriction, XSD('maxLength'))
            max_l.set('value', str(cls.Attributes.max_len))

    # pattern
    if cls.Attributes.pattern != Unicode.Attributes.pattern:
        pattern = etree.SubElement(restriction, XSD('pattern'))
        pattern.set('value', cls.Attributes.pattern)

    return restriction


prot = XmlDocument()


def Tget_range_restriction_tag(T):
    """The get_range_restriction template function. Takes a primitive, returns
    a function that generates range restriction tags.
    """

    from spyne.model.primitive import Decimal
    from spyne.model.primitive import Integer

    if issubclass(T, Decimal):
        def _get_float_restrictions(prot, restriction, cls):
            if cls.Attributes.fraction_digits != T.Attributes.fraction_digits:
                elt = etree.SubElement(restriction, XSD('fractionDigits'))
                elt.set('value', prot.to_unicode(cls,
                                                cls.Attributes.fraction_digits))

        def _get_integer_restrictions(prot, restriction, cls):
            if cls.Attributes.total_digits != T.Attributes.total_digits:
                elt = etree.SubElement(restriction, XSD('totalDigits'))
                elt.set('value', prot.to_unicode(cls,
                                                   cls.Attributes.total_digits))

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
        restriction = simple_get_restriction_tag(document, cls)
        if restriction is None:
            return

        if cls.Attributes.gt != T.Attributes.gt:
            elt = etree.SubElement(restriction, XSD('minExclusive'))
            elt.set('value', prot.to_unicode(cls, cls.Attributes.gt))

        if cls.Attributes.ge != T.Attributes.ge:
            elt = etree.SubElement(restriction, XSD('minInclusive'))
            elt.set('value', prot.to_unicode(cls, cls.Attributes.ge))

        if cls.Attributes.lt != T.Attributes.lt:
            elt = etree.SubElement(restriction, XSD('maxExclusive'))
            elt.set('value', prot.to_unicode(cls, cls.Attributes.lt))

        if cls.Attributes.le != T.Attributes.le:
            elt = etree.SubElement(restriction, XSD('maxInclusive'))
            elt.set('value', prot.to_unicode(cls, cls.Attributes.le))

        if cls.Attributes.pattern != T.Attributes.pattern:
            elt = etree.SubElement(restriction, XSD('pattern'))
            elt.set('value', cls.Attributes.pattern)

        _get_additional_restrictions(prot, restriction, cls)

        return restriction

    return _get_range_restriction_tag
