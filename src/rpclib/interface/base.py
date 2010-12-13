
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
from rpclib.model.exception import Fault
from rpclib.util.odict import odict

import rpclib.namespace.soap
_ns_xsd = rpclib.namespace.soap.xsd

class ValidationError(Fault):
    pass

class SchemaInfo(object):
    def __init__(self):
        self.elements = odict()
        self.types = odict()

class Base(object):
    def __init__(self, parent, services, tns, name=None):
        self.__ns_counter = 0

        self.parent = parent
        self.services = services
        self.__tns = tns
        self.__name = name

        self.call_routes = {}
        self.namespaces = odict()
        self.classes = {}
        self.imports = {}

        self.nsmap = dict(rpclib.namespace.soap.const_nsmap)
        self.prefmap = dict(rpclib.namespace.soap.const_prefmap)

        self.nsmap['tns']=tns
        self.prefmap[tns]='tns'

        self.populate_interface()

    def has_class(self, cls):
        retval = False
        ns_prefix = cls.get_namespace_prefix(self)

        if ns_prefix in rpclib.namespace.soap.const_nsmap:
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
            return pref != pref_tns

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
                    self.imports[pref_tns].add(self.app.nsmap[t_pref])

                ref = seq.get('ref', '')
                r_pref = ref.split(':')[0]

                if r_pref and is_valid_import(r_pref):
                    self.imports[pref_tns].add(self.app.nsmap[r_pref])

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
        retval = self.__name

        if retval is None:
            retval = self.parent.__class__.__name__.split('.')[-1]

        return retval

    name = property(get_name)

    def get_tns(self):
        """Returns default namespace that is seen in the targetNamespace
        attribute of the definitions tag.

        Not meant to be overridden.
        """
        retval = self.__tns

        if retval is None:
            service_name = self.get_name()

            if self.__class__.__module__ == '__main__':
                retval = '.'.join((service_name, service_name))
            else:
                retval = '.'.join((self.__class__.__module__, service_name))

            if retval.startswith('rpclib'):
                retval = self.services[0].get_tns()

        return retval

    def populate_interface(self, types=None):
        # FIXME: should also somehow freeze child classes' _type_info dictionaries.

        # populate call routes
        for s in self.services:
            s.__tns__ = self.get_tns()
            inst = self.parent.get_service(s)

            for method in inst.public_methods:
                method_name = "{%s}%s" % (self.get_tns(), method.name)

                if method_name in self.call_routes:
                    o = self.call_routes[method_name]
                    raise Exception("%s.%s.%s overwrites %s.%s.%s" %
                                    (s.__module__, s.__name__, method.name,
                                     o.__module__, o.__name__, method.name))

                else:
                    logger.debug('adding method %r' % method_name)
                    self.call_routes[method_name] = s
                    self.call_routes[method.name] = s

        # populate types
        for s in self.services:
            inst = self.parent.get_service(s)
            if inst.__in_header__ != None:
                inst.__in_header__.resolve_namespace(inst.__in_header__,
                                                                inst.get_tns())
                inst.__in_header__.add_to_schema(self)

            if inst.__out_header__ != None:
                inst.__out_header__.resolve_namespace(inst.__out_header__,
                                                                inst.get_tns())
                inst.__out_header__.add_to_schema(self)

            for method in inst.public_methods:
                method.in_message.add_to_schema(self)
                method.out_message.add_to_schema(self)

                for fault in method.faults:
                    fault.add_to_schema(self)

                if method.in_header is None:
                    method.in_header = inst.__in_header__
                else:
                    method.in_header.add_to_schema(self)

                if method.out_header is None:
                    method.out_header = inst.__out_header__
                else:
                    method.out_header.add_to_schema(self)

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
