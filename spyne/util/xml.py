
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
from inspect import isgenerator

from lxml import etree

from os.path import dirname
from os.path import abspath

from spyne import ServiceBase, Application, srpc
from spyne.context import FakeContext
from spyne.interface import Interface
from spyne.interface.xml_schema import XmlSchema
from spyne.interface.xml_schema.parser import XmlSchemaParser, Thier_repr, PARSER
from spyne.protocol import ProtocolMixin
from spyne.protocol.cloth import XmlCloth

from spyne.protocol.xml import XmlDocument
from spyne.util.appreg import unregister_application
from spyne.util.six import BytesIO
from spyne.util.tlist import tlist


class FakeApplication(object):
    def __init__(self, default_namespace):
        self.tns = default_namespace
        self.services = ()
        self.classes = ()


def get_schema_documents(models, default_namespace=None):
    """Returns the schema documents in a dict whose keys are namespace prefixes
    and values are Element objects.

    :param models: A list of spyne.model classes that will be represented in
                   the schema.
    """

    if default_namespace is None:
        default_namespace = models[0].get_namespace()

    fake_app = FakeApplication(default_namespace)

    interface = Interface(fake_app)
    for m in models:
        m.resolve_namespace(m, default_namespace)
        interface.add_class(m)
    interface.populate_interface(fake_app)

    document = XmlSchema(interface)
    document.build_interface_document()

    return document.get_interface_document()


def get_validation_schema(models, default_namespace=None):
    """Returns the validation schema object for the given models.

    :param models: A list of spyne.model classes that will be represented in
                   the schema.
    """

    if default_namespace is None:
        default_namespace = models[0].get_namespace()

    fake_app = FakeApplication(default_namespace)

    interface = Interface(fake_app)
    for m in models:
        m.resolve_namespace(m, default_namespace)
        interface.add_class(m)

    schema = XmlSchema(interface)
    schema.build_validation_schema()

    return schema.validation_schema


def _dig(par):
    for elt in par:
        elt.tag = elt.tag.split('}')[-1]
        _dig(elt)


_xml_object = XmlDocument()


def get_object_as_xml(inst, cls=None, root_tag_name=None, no_namespace=False):
    """Returns an ElementTree representation of a
    :class:`spyne.model.complex.ComplexModel` subclass.

    :param inst: The instance of the class to be serialized.
    :param cls: The class to be serialized. Optional.
    :param root_tag_name: The root tag string to use. Defaults to the output of
        ``value.__class__.get_type_name_ns()``.
    :param no_namespace: When true, namespace information is discarded.
    """

    if cls is None:
        cls = inst.__class__

    parent = etree.Element("parent")
    _xml_object.to_parent(None, cls, inst, parent, cls.get_namespace(),
                                                                  root_tag_name)
    if no_namespace:
        _dig(parent)
        etree.cleanup_namespaces(parent)

    return parent[0]


def get_object_as_xml_polymorphic(inst, cls=None, root_tag_name=None,
                                                            no_namespace=False):
    """Returns an ElementTree representation of a
    :class:`spyne.model.complex.ComplexModel` subclass.

    :param inst: The instance of the class to be serialized.
    :param cls: The class to be serialized. Optional.
    :param root_tag_name: The root tag string to use. Defaults to the output of
        ``value.__class__.get_type_name_ns()``.
    :param no_namespace: When true, namespace information is discarded.
    """

    if cls is None:
        cls = inst.__class__

    if no_namespace:
        app = Application([ServiceBase], tns="",
                                     out_protocol=XmlDocument(polymorphic=True))
    else:
        tns = cls.get_namespace()
        if tns is None:
            raise ValueError(
                "Either set a namespace for %r or pass no_namespace=True"
                                                                      % (cls, ))

        class _DummyService(ServiceBase):
            @srpc(cls)
            def f(_):
                pass

        app = Application([_DummyService], tns=tns,
                                     out_protocol=XmlDocument(polymorphic=True))

    unregister_application(app)

    parent = etree.Element("parent", nsmap=app.interface.nsmap)

    app.out_protocol.to_parent(None, cls, inst, parent, cls.get_namespace(),
                                                                  root_tag_name)

    if no_namespace:
        _dig(parent)

    etree.cleanup_namespaces(parent)

    return parent[0]


def get_xml_as_object_polymorphic(elt, cls):
    """Returns a native :class:`spyne.model.complex.ComplexModel` child from an
    ElementTree representation of the same class.

    :param elt: The xml document to be deserialized.
    :param cls: The class the xml document represents.
    """

    tns = cls.get_namespace()
    if tns is None:
        raise ValueError("Please set a namespace for %r" % (cls, ))

    class _DummyService(ServiceBase):
        @srpc(cls)
        def f(_):
            pass

    app = Application([_DummyService], tns=tns,
                                      in_protocol=XmlDocument(polymorphic=True))

    unregister_application(app)

    return app.in_protocol.from_element(FakeContext(app=app), cls, elt)


def get_object_as_xml_cloth(inst, cls=None, no_namespace=False, encoding='utf8'):
    """Returns an ElementTree representation of a
    :class:`spyne.model.complex.ComplexModel` subclass.

    :param inst: The instance of the class to be serialized.
    :param cls: The class to be serialized. Optional.
    :param root_tag_name: The root tag string to use. Defaults to the output of
        ``value.__class__.get_type_name_ns()``.
    :param no_namespace: When true, namespace information is discarded.
    """

    if cls is None:
        cls = inst.__class__

    if cls.get_namespace() is None and no_namespace is None:
        no_namespace = True

    if no_namespace is None:
        no_namespace = False

    ostr = BytesIO()
    xml_cloth = XmlCloth(use_ns=(not no_namespace))
    ctx = FakeContext()
    with etree.xmlfile(ostr, encoding=encoding) as xf:
        ctx.outprot_ctx.doctype_written = False
        ctx.protocol.prot_stack = tlist([], ProtocolMixin)
        tn = cls.get_type_name()
        ret = xml_cloth.subserialize(ctx, cls, inst, xf, tn)

        assert not isgenerator(ret)

    return ostr.getvalue()


def get_xml_as_object(elt, cls):
    """Returns a native :class:`spyne.model.complex.ComplexModel` child from an
    ElementTree representation of the same class.

    :param elt: The xml document to be deserialized.
    :param cls: The class the xml document represents.
    """
    return _xml_object.from_element(None, cls, elt)


def parse_schema_string(s, files={}, repr_=Thier_repr(with_ns=False),
                                                         skip_errors=False):
    """Parses a schema string and returns a _Schema object.

    :param s: The string or bytes object that contains the schema document.
    :param files: A dict that maps namespaces to path to schema files that
        contain the schema document for those namespaces.
    :param repr_: A callable that functions as `repr`.
    :param skip_errors: Skip parsing errors and return a partial schema.
        See debug log for details.

    :return: :class:`spyne.interface.xml_schema.parser._Schema` instance.
    """

    elt = etree.fromstring(s, parser=PARSER)
    return XmlSchemaParser(files, repr_=repr_,
                            skip_errors=skip_errors).parse_schema(elt)


def parse_schema_element(elt, files={}, repr_=Thier_repr(with_ns=False),
                                                         skip_errors=False):
    """Parses a `<xs:schema>` element and returns a _Schema object.

    :param elt: The `<xs:schema>` element, an lxml.etree._Element instance.
    :param files: A dict that maps namespaces to path to schema files that
        contain the schema document for those namespaces.
    :param repr_: A callable that functions as `repr`.
    :param skip_errors: Skip parsing errors and return a partial schema.
        See debug log for details.

    :return: :class:`spyne.interface.xml_schema.parser._Schema` instance.
    """

    return XmlSchemaParser(files, repr_=repr_,
                            skip_errors=skip_errors).parse_schema(elt)


def parse_schema_file(file_name, files=None, repr_=Thier_repr(with_ns=False),
                                                         skip_errors=False):
    """Parses a schema file and returns a _Schema object. Schema files typically
    have the `*.xsd` extension.

    :param file_name: The path to the file that contains the schema document
        to be parsed.
    :param files: A dict that maps namespaces to path to schema files that
        contain the schema document for those namespaces.
    :param repr_: A callable that functions as `repr`.
    :param skip_errors: Skip parsing errors and return a partial schema.
        See debug log for details.

    :return: :class:`spyne.interface.xml_schema.parser._Schema` instance.
    """

    if files is None:
        files = dict()

    elt = etree.fromstring(open(file_name, 'rb').read(), parser=PARSER)
    wd = abspath(dirname(file_name))
    return XmlSchemaParser(files, wd, repr_=repr_,
                            skip_errors=skip_errors).parse_schema(elt)
