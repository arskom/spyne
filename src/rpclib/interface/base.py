
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

import rpclib
from rpclib.model.exception import Fault
from rpclib.util.odict import odict

class ValidationError(Fault):
    pass

class SchemaInfo(object):
    def __init__(self):
        self.elements = odict()
        self.types = odict()

class FuckingException(Exception):
    """An exception you definitely need to get rid of."""

class SchemaEntries(object):
    def __init__(self, app):
        self.namespaces = odict()
        self.imports = {}
        self.tns = app.get_tns()
        self.app = app
        self.classes = {}

    def has_class(self, cls):
        retval = False
        ns_prefix = cls.get_namespace_prefix(self.app)

        if ns_prefix in rpclib.const_nsmap:
            retval = True

        else:
            type_name = cls.get_type_name()

            if (ns_prefix in self.namespaces) and \
                              (type_name in self.namespaces[ns_prefix].types):
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
        pref_tns = cls.get_namespace_prefix(self.app)

        def is_valid_import(pref):
            return not (
                (pref in rpclib.const_nsmap) or (pref == pref_tns)
            )

        if not (pref_tns in self.imports):
            self.imports[pref_tns] = set()

        for c in node:
            if c.tag == "{%s}complexContent" % rpclib.ns_xsd:
                seq = c.getchildren()[0].getchildren()[0] # FIXME: ugly, isn't it?

                extension = c.getchildren()[0]
                if extension.tag == '{%s}extension' % rpclib.ns_xsd:
                    pref = extension.attrib['base'].split(':')[0]
                    if is_valid_import(pref):
                        self.imports[pref_tns].add(self.app.nsmap[pref])
            else:
                seq = c

            if seq.tag == '{%s}sequence' % rpclib.ns_xsd:
                for e in seq:
                    pref = e.attrib['type'].split(':')[0]
                    if is_valid_import(pref):
                        self.imports[pref_tns].add(self.app.nsmap[pref])

            elif seq.tag == '{%s}restriction' % rpclib.ns_xsd:
                pref = seq.attrib['base'].split(':')[0]
                if is_valid_import(pref):
                    self.imports[pref_tns].add(self.app.nsmap[pref])

            else:
                raise FuckingException("i guess you need to hack some more")

    def add_element(self, cls, node):
        schema_info = self.get_schema_info(cls.get_namespace_prefix(self.app))
        schema_info.elements[cls.get_type_name()] = node

    def add_simple_type(self, cls, node):
        ns = cls.get_namespace()
        tn = cls.get_type_name()
        pref = cls.get_namespace_prefix(self.app)

        self.__check_imports(cls, node)
        schema_info = self.get_schema_info(pref)
        schema_info.types[tn] = node

        self.classes['{%s}%s' % (ns,tn)] = cls
        if ns == self.app.get_tns():
            self.classes[tn] = cls

    def add_complex_type(self, cls, node):
        ns = cls.get_namespace()
        tn = cls.get_type_name()
        pref = cls.get_namespace_prefix(self.app)

        self.__check_imports(cls, node)
        schema_info = self.get_schema_info(pref)
        schema_info.types[tn] = node

        self.classes['{%s}%s' % (ns,tn)] = cls
        if ns == self.app.get_tns():
            self.classes[tn] = cls

class Base(object):
    def get_class(self, key):
        return self.classes[key]

    def get_class_instance(self, key):
        return self.classes[key]()
