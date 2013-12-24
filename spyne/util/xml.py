
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


"""The `spyne.util.xml` module contains various Xml and Xml Schema related
utility functions.
"""

from lxml import etree

from os.path import dirname
from os.path import abspath

from spyne.interface import Interface
from spyne.interface.xml_schema import XmlSchema
from spyne.interface.xml_schema import parser
from spyne.interface.xml_schema.defn import TYPE_MAP

from spyne.protocol.xml import XmlDocument


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
        m.resolve_namespace(m, default_namespace)
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

    interface = Interface(fake_app)
    for m in models:
        interface.add_class(m)

    schema = XmlSchema(interface)
    schema.build_validation_schema()

    return schema.validation_schema


def _dig(par):
    for elt in par:
        elt.tag = elt.tag.split('}')[-1]
        _dig(elt)


xml_object = XmlDocument()

def get_object_as_xml(value, cls=None, root_tag_name=None, no_namespace=None):
    '''Returns an ElementTree representation of a
    :class:`spyne.model.complex.ComplexModel` subclass.

    :param value: The instance of the class to be serialized.
    :param value: The root tag string to use. Defaults to the output of
        ``value.__class__.get_type_name_ns()``.
    '''

    if cls is None:
        cls = value.__class__

    if cls.get_namespace() is None and no_namespace is None:
        no_namespace = True

    if no_namespace is None:
        no_namespace = False

    parent = etree.Element("parent")

    xml_object.to_parent(None, cls, value, cls.get_namespace(),
                                                          parent, root_tag_name)

    if no_namespace:
        _dig(parent)
        etree.cleanup_namespaces(parent)

    return parent[0]


def get_xml_as_object(elt, cls):
    """Returns a native :class:`spyne.model.complex.ComplexModel` child from an
    ElementTree representation of the same class.

    :param elt: The xml document to be deserialized.
    :param cls: The class the xml document represents.
    """

    return xml_object.from_element(None, cls, elt)


def parse_schema_string(s, files={}, repr=parser.Thier_repr(with_ns=False)):
    elt = etree.fromstring(s, parser=parser.PARSER)
    return parser.parse_schema(parser.ParsingCtx(files, repr=repr), elt)


def parse_schema_element(elt, files={}, repr=parser.Thier_repr(with_ns=False)):
    return parser.parse_schema(parser.ParsingCtx(files, repr=repr), elt)


def parse_schema_file(file_name, files={}, repr=parser.Thier_repr(with_ns=False)):
    elt = etree.fromstring(open(file_name).read(), parser=parser.PARSER)
    return parser.parse_schema(parser.ParsingCtx(files,
                    abspath(dirname(file_name)), repr=repr), elt)
