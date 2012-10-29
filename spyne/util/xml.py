
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

from lxml import etree

from spyne.interface import Interface
from spyne.interface.xml_schema import XmlSchema
from spyne.protocol.xml import XmlDocument

"""Module that contains various xml utilities."""

class FakeApplication(object):
    pass

def get_schema_documents(models, default_namespace=None):
    '''Returns the schema documents in a dict whose keys are namespace prefixes
    and values are Element objects.

    :param models: A list of spyne.model classes that will be represented in
                   the schema.

    '''

    if default_namespace is None:
        default_namespace = models[0].get_namespace()

    fake_app = FakeApplication()
    fake_app.tns = default_namespace
    fake_app.services = []

    interface = Interface(fake_app)
    for m in models:
        interface.add_class(m)
    interface.populate_interface(fake_app)

    document = XmlSchema(interface)
    document.build_interface_document()

    return document.get_interface_document()

def get_validation_schema(models, default_namespace=None):
    '''Returns the validation schema object for the given models.

    :param models: A list of spyne.model classes that will be represented in
                   the schema.

    '''

    if default_namespace is None:
        default_namespace = models[0].get_namespace()

    fake_app = FakeApplication()
    fake_app.tns = default_namespace
    fake_app.services = []

    interface = XmlSchema()
    interface.set_app(fake_app)
    for m in models:
        interface.add(m)

    interface.build_validation_schema()

    return interface.validation_schema


def _dig(par):
    for elt in par:
        elt.tag = elt.tag.split('}')[-1]
        _dig(elt)

def get_object_as_xml(value, cls=None, root_tag_name=None, no_namespace=False):
    '''Returns an ElementTree representation of a :class:`spyne.model.complex.ComplexModel`
    child.

    :param value: The instance of the class to be serialized.
    :param value: The root tag string to use. Defaults to the output of
        ``value.__class__.get_type_name_ns()``.
    '''

    if cls is None:
        cls = value.__class__
    xml_object = XmlDocument()
    parent = etree.Element("parent")

    xml_object.to_parent_element(cls, value, cls.get_namespace(),
                                                          parent, root_tag_name)

    if no_namespace:
        _dig(parent)
        etree.cleanup_namespaces(parent)

    return parent[0]

def get_xml_as_object(elt, cls):
    '''Returns a native :class:`spyne.model.complex.ComplexModel` child from an
    ElementTree representation of the same class.

    :param value: The class the xml document represents.
    :param value: The xml document to be deserialized.
    '''

    xml_object = XmlDocument()

    return xml_object.from_element(cls, elt)
