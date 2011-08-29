
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

import logging
logger = logging.getLogger(__name__)

import warnings
from rpclib.util.odict import odict

import rpclib.const.xml_ns
_ns_xsd = rpclib.const.xml_ns.xsd

class SchemaInfo(object):
    def __init__(self):
        self.elements = odict()
        self.types = odict()

class InterfaceBase(object):
    def __init__(self, app, import_base_namespaces=False):
        self.__ns_counter = 0

        self.set_app(app)

        # FIXME: this belongs in the wsdl class
        self.import_base_namespaces = import_base_namespaces

        self.service_mapping = {}
        self.method_mapping = {}

        self.url = None

        self.populate_interface()

    def set_app(self, value):
        self.__app = value

    @property
    def app(self):
        return self.__app

    @property
    def services(self):
        return self.__app.services

    def reset_interface(self):
        self.namespaces = odict()
        self.classes = {}
        self.imports = {}

        self.nsmap = dict(rpclib.const.xml_ns.const_nsmap)
        self.prefmap = dict(rpclib.const.xml_ns.const_prefmap)

        self.nsmap['tns'] = self.get_tns()
        self.prefmap[self.get_tns()] = 'tns'

    def has_class(self, cls):
        retval = False
        ns_prefix = cls.get_namespace_prefix(self)

        if ns_prefix in rpclib.const.xml_ns.const_nsmap:
            retval = True

        else:
            type_name = cls.get_type_name()

            if ((ns_prefix in self.namespaces) and
                               (type_name in self.namespaces[ns_prefix].types)):
                retval = True

        return retval

    def get_schema_info(self, prefix):
        if prefix in self.namespaces:
            schema = self.namespaces[prefix]
        else:
            schema = self.namespaces[prefix] = SchemaInfo()

        return schema

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

        self.classes['{%s}%s' % (ns,tn)] = cls
        if ns == self.get_tns():
            self.classes[tn] = cls

    def add_complex_type(self, cls, node):
        ns = cls.get_namespace()
        tn = cls.get_type_name()
        pref = cls.get_namespace_prefix(self)

        self.__check_imports(cls, node)
        schema_info = self.get_schema_info(pref)
        schema_info.types[tn] = node

        self.classes['{%s}%s' % (ns,tn)] = cls
        if ns == self.get_tns():
            self.classes[tn] = cls

    def get_class(self, key):
        return self.classes[key]

    def get_class_instance(self, key):
        return self.classes[key]()

    def get_name(self):
        """Returns service name that is seen in the name attribute of the
        definitions tag.

        Not meant to be overridden.
        """
        return self.app.name

    def get_tns(self):
        """Returns default namespace that is seen in the targetNamespace
        attribute of the definitions tag.

        Not meant to be overridden.
        """
        return self.app.tns

    def populate_interface(self, types=None):
        # FIXME: should also somehow freeze child classes' _type_info
        #        dictionaries.

        self.reset_interface()

        # populate types
        for s in self.services:
            for method in s.public_methods.values():
                if method.in_header is None:
                    method.in_header = s.__in_header__
                if method.out_header is None:
                    method.out_header = s.__out_header__

                if not (method.in_header is None):
                    if isinstance(method.in_header, (list, tuple)):
                        in_headers = method.in_header
                    else:
                        in_headers = (method.in_header,)
                    for in_header in in_headers:
                        in_header.resolve_namespace(in_header, self.get_tns())
                        in_header.add_to_schema(self)

                if not (method.out_header is None):
                    if isinstance(method.out_header, (list,tuple)):
                        out_headers = method.out_header
                    else:
                        out_headers = (method.out_header,)
                    for out_header in out_headers:
                        out_header.resolve_namespace(out_header, self.get_tns())
                        out_header.add_to_schema(self)

                method.in_message.resolve_namespace(method.in_message,
                                                                 self.get_tns())
                method.in_message.add_to_schema(self)

                method.out_message.resolve_namespace(method.out_message,
                                                                 self.get_tns())
                method.out_message.add_to_schema(self)

                for fault in method.faults:
                    fault.resolve_namespace(fault, self.get_tns())
                    fault.add_to_schema(self)

        # populate call routes
        for s in self.services:
            s.__tns__ = self.get_tns()
            logger.debug("populating '%s.%s'" % (s.__module__, s.__name__))
            for method in s.public_methods.values():
                o = self.method_mapping.get(method.key)
                if not (o is None):
                    raise Exception("\nThe message %r defined in both '%s.%s'"
                                                                " and '%s.%s'"
                      % (method.key, s.__module__, s.__name__,
                                          o.__module__, o.__name__,
                        ))

                else:
                    logger.debug('\tadding method %r to match %r tag.' %
                                                      (method.name, method.key))
                    self.service_mapping[method.key] = s
                    self.method_mapping[method.key] = method

    tns = property(get_tns)

    def get_namespace_prefix(self, ns):
        """Returns the namespace prefix for the given namespace. Creates a new
        one automatically if it doesn't exist.

        Not meant to be overridden.
        """

        if ns == "__main__":
            warnings.warn("Namespace is '__main__'", Warning )

        assert ns != "rpclib.model.base"

        assert (isinstance(ns, str) or isinstance(ns, unicode)), ns

        if not (ns in self.prefmap):
            pref = "s%d" % self.__ns_counter
            while pref in self.nsmap:
                self.__ns_counter += 1
                pref = "s%d" % self.__ns_counter

            self.prefmap[ns] = pref
            self.nsmap[pref] = ns

            self.__ns_counter += 1

        else:
            pref = self.prefmap[ns]

        return pref
