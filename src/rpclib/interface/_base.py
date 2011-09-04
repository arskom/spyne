
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
    def __init__(self, app=None):
        self.__ns_counter = 0

        self.service_mapping = {}
        self.method_mapping = {}

        self.url = None

        self.__app = None
        self.set_app(app)

    def set_app(self, value):
        assert self.__app is None, "One interface instance should belong to one " \
                                   "application instance."

        self.__app = value
        self.populate_interface()

    @property
    def app(self):
        return self.__app

    @property
    def services(self):
        if self.__app:
            return self.__app.services
        return []

    def reset_interface(self):
        self.namespaces = odict()
        self.classes = {}
        self.imports = {}

    def has_class(self, cls):
        ns_prefix = cls.get_namespace_prefix(self)
        type_name = cls.get_type_name()

        return ((ns_prefix in self.namespaces) and
                           (type_name in self.namespaces[ns_prefix].types))

    def get_schema_info(self, prefix):
        if prefix in self.namespaces:
            schema = self.namespaces[prefix]
        else:
            schema = self.namespaces[prefix] = SchemaInfo()

        return schema

    def get_class(self, key):
        return self.classes[key]

    def get_class_instance(self, key):
        return self.classes[key]()

    def get_name(self):
        """Returns service name that is seen in the name attribute of the
        definitions tag.

        Not meant to be overridden.
        """
        if self.app:
            return self.app.name

    def get_tns(self):
        """Returns default namespace that is seen in the targetNamespace
        attribute of the definitions tag.

        Not meant to be overridden.
        """
        if self.app:
            return self.app.tns

    def populate_interface(self, types=None):
        # FIXME: should also somehow freeze child classes' _type_info
        #        dictionaries.

        self.reset_interface()

        # populate types
        for s in self.services:
            logger.debug("populating '%s.%s' types..." % (s.__module__, s.__name__))
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
                        self.add(in_header)

                if not (method.out_header is None):
                    if isinstance(method.out_header, (list,tuple)):
                        out_headers = method.out_header
                    else:
                        out_headers = (method.out_header,)

                    for out_header in out_headers:
                        out_header.resolve_namespace(out_header, self.get_tns())
                        self.add(out_header)

                method.in_message.resolve_namespace(method.in_message,
                                                                 self.get_tns())
                self.add(method.in_message)

                method.out_message.resolve_namespace(method.out_message,
                                                                 self.get_tns())
                self.add(method.out_message)

                for fault in method.faults:
                    fault.resolve_namespace(fault, self.get_tns())
                    self.add(fault)

        # populate call routes
        for s in self.services:
            s.__tns__ = self.get_tns()
            logger.debug("populating '%s.%s' methods..." % (s.__module__, s.__name__))
            for method in s.public_methods.values():
                o = self.service_mapping.get(method.key)
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

        if not (isinstance(ns, str) or isinstance(ns, unicode)):
            raise TypeError(ns)

        if ns == "__main__":
            warnings.warn("Namespace is '__main__'", Warning )

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

    def add(self, cls):
        raise NotImplementedError('Extend and override.')
