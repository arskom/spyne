
from lxml import etree

import rpclib.const.xml_ns

_ns_xsd = rpclib.const.xml_ns.xsd

def fault_add_to_schema(interface, cls):
    app = interface.app
    complex_type = etree.Element('{%s}complexType' % _ns_xsd)
    complex_type.set('name', '%sFault' % cls.get_type_name())

    extends = getattr(cls, '__extends__', None)
    if extends is not None:
        complex_content = etree.SubElement(complex_type,
                                        '{%s}complexContent' % _ns_xsd)
        extension = etree.SubElement(complex_content, "{%s}extension"
                                                                  % _ns_xsd)
        extension.set('base', extends.get_type_name_ns(app))
        sequence_parent = extension
    else:
        sequence_parent = complex_type

    etree.SubElement(sequence_parent, '{%s}sequence' % _ns_xsd)

    interface.add_complex_type(cls, complex_type)

    top_level_element = etree.Element('{%s}element' % _ns_xsd)
    top_level_element.set('name', cls.get_type_name())
    top_level_element.set('{%s}type' % _ns_xsd,
                          '%sFault' % cls.get_type_name_ns(app))

    interface.add_element(cls, top_level_element)
