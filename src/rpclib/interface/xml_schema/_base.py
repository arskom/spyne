
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

"""This module contains the implementation of the Xml Schema standard and its
helper methods and objects."""

import logging
logger = logging.getLogger(__name__)

import shutil
import tempfile

import rpclib.const.xml_ns

from lxml import etree

from rpclib.util.cdict import cdict

from rpclib.interface import InterfaceDocumentBase
from rpclib.model import SimpleModel
from rpclib.model.primitive import Decimal
from rpclib.model.primitive import String
from rpclib.model.complex import ComplexModelBase
from rpclib.model.enum import EnumBase
from rpclib.model.fault import Fault
from rpclib.util.odict import odict

from rpclib.interface.xml_schema.model import simple_add
from rpclib.interface.xml_schema.model.complex import complex_add
from rpclib.interface.xml_schema.model.fault import fault_add
from rpclib.interface.xml_schema.model.enum import enum_add

from rpclib.interface.xml_schema.model import simple_get_restriction_tag
from rpclib.interface.xml_schema.model.primitive import string_get_restriction_tag
from rpclib.interface.xml_schema.model.primitive import decimal_get_restriction_tag

_add_handlers = cdict({
    object: lambda interface, cls: None,
    SimpleModel: simple_add,
    ComplexModelBase: complex_add,
    Fault: fault_add,
    EnumBase: enum_add,
})

_get_restriction_tag_handlers = cdict({
    object: lambda self, cls: None,
    SimpleModel: simple_get_restriction_tag,
    String: string_get_restriction_tag,
    Decimal: decimal_get_restriction_tag,
})

_ns_xsd = rpclib.const.xml_ns.xsd
_ns_wsa = rpclib.const.xml_ns.wsa
_ns_wsdl = rpclib.const.xml_ns.wsdl
_ns_soap = rpclib.const.xml_ns.soap
_pref_wsa = rpclib.const.xml_ns.const_prefmap[_ns_wsa]


class SchemaInfo(object):
    def __init__(self):
        self.elements = odict()
        self.types = odict()


class XmlSchema(InterfaceDocumentBase):
    """The implementation of the  Xml Schema object definition document
    standard.
    """

    def __init__(self, interface):
        InterfaceDocumentBase.__init__(self, interface)

        self.schema_dict = {}
        self.validation_schema = None
        self.namespaces = odict()

    def add(self, cls):
        handler = _add_handlers[cls]
        handler(self, cls)

    def get_restriction_tag(self, cls):
        handler = _get_restriction_tag_handlers[cls]
        return handler(self, cls)

    def build_schema_nodes(self, with_schema_location=False):
        self.schema_dict = {}

        for cls in self.interface.classes.values():
            self.add(cls)

        for pref in self.namespaces:
            schema = self.get_schema_node(pref)

            # append import tags
            for namespace in self.interface.imports[self.interface.nsmap[pref]]:
                import_ = etree.SubElement(schema, "{%s}import" % _ns_xsd)
                import_.set("namespace", namespace)
                if with_schema_location:
                    import_.set('schemaLocation', "%s.xsd" %
                                   self.interface.get_namespace_prefix(namespace))

                sl = rpclib.const.xml_ns.schema_location.get(namespace, None)
                if not (sl is None):
                    import_.set('schemaLocation', sl)

            # append simpleType and complexType tags
            for node in reversed(self.namespaces[pref].types.values()):
                schema.append(node)

            # append element tags
            for node in self.namespaces[pref].elements.values():
                schema.append(node)

        self.interface.event_manager.fire_event('document_built', self.schema_dict)

    def build_validation_schema(self):
        """Build application schema specifically for xml validation purposes.
        """

        self.build_schema_nodes(with_schema_location=True)

        pref_tns = self.interface.get_namespace_prefix(self.interface.tns)
        tmp_dir_name = tempfile.mkdtemp()
        logger.debug("generating schema for targetNamespace=%r, prefix: %r in dir %r"
                                   % (self.interface.tns, pref_tns, tmp_dir_name))

        # serialize nodes to files
        for k, v in self.schema_dict.items():
            file_name = '%s/%s.xsd' % (tmp_dir_name, k)
            f = open(file_name, 'wb')
            etree.ElementTree(v).write(f, pretty_print=True)
            f.close()
            logger.debug("writing %r for ns %s" % (file_name, self.interface.nsmap[k]))

        f = open('%s/%s.xsd' % (tmp_dir_name, pref_tns), 'r')

        logger.debug("building schema...")
        self.validation_schema = etree.XMLSchema(etree.parse(f))

        logger.debug("schema %r built, cleaning up..." % self.validation_schema)
        f.close()

        shutil.rmtree(tmp_dir_name)
        logger.debug("removed %r" % tmp_dir_name)

    def get_schema_node(self, pref):
        """Return schema node for the given namespace prefix."""
        # create schema node
        if not (pref in self.schema_dict):
            schema = etree.Element("{%s}schema" % _ns_xsd, nsmap=self.interface.nsmap)

            schema.set("targetNamespace", self.interface.nsmap[pref])
            schema.set("elementFormDefault", "qualified")

            self.schema_dict[pref] = schema

        else:
            schema = self.schema_nodes[pref]

        return schema

    def get_interface_document(self):
        return self.schema_dict

    def build_interface_document(self):
        self.build_schema_nodes()

    def add_element(self, cls, node):
        pref = cls.get_namespace_prefix(self.interface)

        schema_info = self.get_schema_info(pref)
        schema_info.elements[cls.get_type_name()] = node

    def add_simple_type(self, cls, node):
        tn = cls.get_type_name()
        pref = cls.get_namespace_prefix(self.interface)

        schema_info = self.get_schema_info(pref)
        schema_info.types[tn] = node

    def add_complex_type(self, cls, node):
        tn = cls.get_type_name()
        pref = cls.get_namespace_prefix(self.interface)

        schema_info = self.get_schema_info(pref)
        schema_info.types[tn] = node

    def get_schema_info(self, prefix):
        """Returns the SchemaInfo object for the corresponding namespace. It
        creates it if it doesn't exist.

        The SchemaInfo object holds the simple and complex type definitions
        for a given namespace."""

        if prefix in self.namespaces:
            schema = self.namespaces[prefix]
        else:
            schema = self.namespaces[prefix] = SchemaInfo()

        return schema
