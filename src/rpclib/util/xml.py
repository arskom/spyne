
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

from rpclib.interface.xml_schema import XmlSchema
from rpclib.protocol.xml import XmlObject

"""Module that contains various xml utilities."""

class FakeApplication(object):
    pass

def get_schema_documents(models, default_namespace=None):
    '''Returns the schema documents in a dict whose keys are namespace prefixes
    and values are Element objects.

    :param models: A list of rpclib.model classes that will be represented in
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

    interface.build_interface_document()

    return interface.get_interface_document()

def get_validation_schema(models, default_namespace=None):
    '''Returns the validation schema object for the given models.

    :param models: A list of rpclib.model classes that will be represented in
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

def get_object_as_xml(value):
    '''Returns an ElementTree representation of a :class:`rpclib.model.complex.ComplexModel`
    child.

    :param value: The instance of the class to be serialized.
    '''

    xml_object = XmlObject()
    parent = etree.Element("parent")

    xml_object.to_parent_element(value.__class__, value, value.get_namespace(), parent)

    return parent[0]
