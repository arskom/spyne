
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

from rpclib.interface import InterfaceBase
from rpclib.model import SimpleModel
from rpclib.model.primitive import String
from rpclib.model.primitive import Decimal
from rpclib.model.complex import ComplexModelBase
from rpclib.model.enum import EnumBase
from rpclib.model.fault import Fault

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

class XmlSchema(InterfaceBase):
    """The implementation of the  Xml Schema object definition document
    standard.
    """

    def __init__(self, app=None, import_base_namespaces=False):
        self.schema_dict = {}
        self.validation_schema = None
        self.import_base_namespaces = import_base_namespaces

        InterfaceBase.__init__(self, app)

    def add(self, cls):
        handler = _add_handlers[cls]
        handler(self, cls)

    def get_restriction_tag(self, cls):
        handler = _get_restriction_tag_handlers[cls]
        return handler(self, cls)

    def build_schema_nodes(self, with_schema_location=False):
        self.schema_dict = {}
        for pref in self.namespaces:
            schema = self.get_schema_node(pref)

            # append import tags
            for namespace in self.imports[pref]:
                import_ = etree.SubElement(schema, "{%s}import" % _ns_xsd)
                import_.set("namespace", namespace)
                if with_schema_location:
                    import_.set('schemaLocation', "%s.xsd" %
                                           self.get_namespace_prefix(namespace))

                sl = rpclib.const.xml_ns.schema_location.get(namespace, None)
                if not (sl is None):
                    import_.set('schemaLocation', sl)

            # append simpleType and complexType tags
            for node in reversed(self.namespaces[pref].types.values()):
                schema.append(node)

            # append element tags
            for node in self.namespaces[pref].elements.values():
                schema.append(node)

    def build_validation_schema(self):
        """Build application schema specifically for xml validation purposes.
        """

        self.build_schema_nodes(with_schema_location=True)

        pref_tns = self.get_namespace_prefix(self.get_tns())
        tmp_dir_name = tempfile.mkdtemp()
        logger.debug("generating schema for targetNamespace=%r, prefix: %r in dir %r"
                                   % (self.get_tns(), pref_tns, tmp_dir_name))

        logger.debug
        # serialize nodes to files
        for k, v in self.schema_dict.items():
            file_name = '%s/%s.xsd' % (tmp_dir_name, k)
            f = open(file_name, 'wb')
            etree.ElementTree(v).write(f, pretty_print=True)
            f.close()
            logger.debug("writing %r for ns %s" % (file_name, self.nsmap[k]))

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
            schema = etree.Element("{%s}schema" % _ns_xsd, nsmap=self.nsmap)

            schema.set("targetNamespace", self.nsmap[pref])
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
        pref = cls.get_namespace_prefix(self)

        schema_info = self.get_schema_info(pref)
        schema_info.elements[cls.get_type_name()] = node

    def add_simple_type(self, cls, node):
        ns = cls.get_namespace()
        tn = cls.get_type_name()
        pref = cls.get_namespace_prefix(self)

        self.__check_imports(cls, node)
        schema_info = self.get_schema_info(pref)
        schema_info.types[tn] = node

        class_key = '{%s}%s' % (ns, tn)
        logger.debug('\tadding class %r for %r' % (repr(cls), class_key))

        self.classes[class_key] = cls
        if ns == self.get_tns():
            self.classes[tn] = cls

    def add_complex_type(self, cls, node):
        ns = cls.get_namespace()
        tn = cls.get_type_name()
        pref = cls.get_namespace_prefix(self)

        self.__check_imports(cls, node)
        schema_info = self.get_schema_info(pref)
        schema_info.types[tn] = node

        class_key = '{%s}%s' % (ns, tn)
        logger.debug('\tadding class %r for %r' % (repr(cls), class_key))

        self.classes[class_key] = cls
        if ns == self.get_tns():
            self.classes[tn] = cls

    def has_class(self, cls):
        ns_prefix = cls.get_namespace_prefix(self)
        if ns_prefix in rpclib.const.xml_ns.const_nsmap:
            return True

        else:
            return InterfaceBase.has_class(self, cls)

    # FIXME: this is an ugly hack. we need proper dependency management
    def __check_imports(self, cls, node):
        pref_tns = cls.get_namespace_prefix(self)

        def is_valid_import(pref):
            return pref != pref_tns and (
                    self.import_base_namespaces or
                    (not (pref in rpclib.const.xml_ns.const_nsmap))
                )

        if not (pref_tns in self.imports):
            self.imports[pref_tns] = set()

        for c in node:
            if c.tag == "{%s}complexContent" % _ns_xsd:
                extension = c.getchildren()[0]

                if extension.tag == '{%s}extension' % _ns_xsd:
                    pref = extension.attrib['base'].split(':')[0]
                    if is_valid_import(pref):
                        self.imports[pref_tns].add(self.nsmap[pref])
                    seq = extension.getchildren()[0]

                else:
                    seq = c.getchildren()[0]

            else:
                seq = c

            if seq.tag == '{%s}sequence' % _ns_xsd:
                for e in seq:
                    pref = e.attrib['type'].split(':')[0]
                    if is_valid_import(pref):
                        self.imports[pref_tns].add(self.nsmap[pref])

            elif seq.tag == '{%s}restriction' % _ns_xsd:
                pref = seq.attrib['base'].split(':')[0]
                if is_valid_import(pref):
                    self.imports[pref_tns].add(self.nsmap[pref])

            elif seq.tag == '{%s}attribute' % _ns_xsd:
                typ = seq.get('type', '')
                t_pref = typ.split(':')[0]

                if t_pref and is_valid_import(t_pref):
                    self.imports[pref_tns].add(self.nsmap[t_pref])

                ref = seq.get('ref', '')
                r_pref = ref.split(':')[0]

                if r_pref and is_valid_import(r_pref):
                    self.imports[pref_tns].add(self.nsmap[r_pref])

            else:
                raise Exception("i guess you need to hack some more")
