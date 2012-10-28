
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

import logging
logger = logging.getLogger(__name__)

import warnings
import spyne.interface

from spyne import EventManager
from spyne.const import xml_ns as namespace
from spyne.const.suffix import TYPE_SUFFIX
from spyne.const.suffix import RESULT_SUFFIX
from spyne.const.suffix import RESPONSE_SUFFIX

from spyne.model import ModelBase
from spyne.model.complex import ComplexModelBase
from spyne.model.complex import Alias


class Interface(object):
    """The ``Interface`` class holds all information needed to build an
    interface document.

    :param app: A :class:`spyne.application.Application` instance.
    """

    def __init__(self, app=None, import_base_namespaces=False):
        self.__ns_counter = 0
        self.import_base_namespaces = import_base_namespaces

        self.url = None

        self.__app = None

        self.classes = {}
        self.imports = {}
        self.service_method_map = {}
        self.method_id_map = {}
        self.nsmap = {}
        self.prefmap = {}
        self.__app = app

        self.reset_interface()
        self.populate_interface()

    def set_app(self, value):
        assert self.__app is None, "One interface instance can belong to only " \
                                   "one application instance."

        self.__app = value
        self.reset_interface()
        self.populate_interface()

    def get_app(self):
        return self.__app

    app = property(get_app, set_app)

    @property
    def services(self):
        if self.__app:
            return self.__app.services
        return []

    def reset_interface(self):
        self.classes = {}
        self.imports = {self.get_tns(): set()}
        self.service_method_map = {}
        self.method_id_map = {}
        self.nsmap = dict(namespace.const_nsmap)
        self.prefmap = dict(namespace.const_prefmap)

        self.nsmap['tns'] = self.get_tns()
        self.prefmap[self.get_tns()] = 'tns'

    def has_class(self, cls):
        """Returns true if the given class is already included in the interface
        object somewhere."""

        return ('{%s}%s' % (cls.get_namespace(), cls.get_type_name())) in self.classes

    def get_class(self, key):
        """Returns the class definition that corresponds to the given key.
        Keys are in '{namespace}class_name' form, a.k.a. XML QName format.

        Not meant to be overridden.
        """
        return self.classes[key]

    def get_class_instance(self, key):
        """Returns the default class instance that corresponds to the given key.
        Keys are in '{namespace}class_name' form, a.k.a. XML QName format.
        Classes should not enforce arguments to the constructor.

        Not meant to be overridden.
        """
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

    def __test_type_name_validity(self, c):
        if c and  ( c.get_type_name().endswith(RESULT_SUFFIX) or
                    c.get_type_name().endswith(RESPONSE_SUFFIX) ):
            raise Exception("You can't use any type or method name ending "
                            "with one of %r unless you alter the "
                            "constants in the 'spyne.const.suffix' module.\n"
                            "This is for class %r."
                            % ((TYPE_SUFFIX, RESULT_SUFFIX, RESPONSE_SUFFIX),c))

    def populate_interface(self, types=None):
        """Harvests the information stored in individual classes' _type_info
        dictionaries. It starts from function definitions and includes only
        the used objects.
        """

        classes = []
        # populate types
        for s in self.services:
            logger.debug("populating '%s.%s (%s)' types..." % (s.__module__,
                                                s.__name__, s.get_service_key()))

            for method in s.public_methods.values():
                if method.in_header is None:
                    method.in_header = s.__in_header__
                if method.out_header is None:
                    method.out_header = s.__out_header__
                if method.aux is None:
                    method.aux = s.__aux__
                if method.aux is not None:
                    method.aux.methods.append(s.get_method_id(method))

                if not (method.in_header is None):
                    if isinstance(method.in_header, (list, tuple)):
                        in_headers = method.in_header
                    else:
                        in_headers = (method.in_header,)

                    for in_header in in_headers:
                        self.__test_type_name_validity(in_header)
                        in_header.resolve_namespace(in_header, self.get_tns())
                        classes.append(in_header)

                if not (method.out_header is None):
                    if isinstance(method.out_header, (list, tuple)):
                        out_headers = method.out_header
                    else:
                        out_headers = (method.out_header,)

                    for out_header in out_headers:
                        self.__test_type_name_validity(out_header)
                        out_header.resolve_namespace(out_header, self.get_tns())
                        classes.append(out_header)

                if method.faults is None:
                    method.faults = []
                elif not (isinstance(method.faults, (list, tuple))):
                    method.faults = (method.faults,)

                for fault in method.faults:
                    fault.__namespace__ = self.get_tns()
                    classes.append(fault)

                self.__test_type_name_validity(method.in_message)
                method.in_message.resolve_namespace(method.in_message,
                                                                 self.get_tns())
                classes.append(method.in_message)

                # we are not testing out_message with __test_type_name_validity
                # because they have RESPONSE_SUFFIX and RESULT_SUFFIX added
                # automatically. actually, they're what we're trying to protect.
                method.out_message.resolve_namespace(method.out_message,
                                                                 self.get_tns())
                classes.append(method.out_message)

        classes.sort(key=lambda cls: (cls.get_namespace(), cls.get_type_name()))
        for c in classes:
            self.add_class(c)

        # populate call routes
        for s in self.services:
            s.__tns__ = self.get_tns()
            logger.debug("populating '%s.%s' methods..." % (s.__module__,
                                                                    s.__name__))
            for method in s.public_methods.values():
                logger.debug('\tadding method %r to match %r tag.' %
                                                      (method.name, method.key))

                assert not s.get_method_id(method) in self.method_id_map

                self.method_id_map[s.get_method_id(method)] = (s, method)

                val = self.service_method_map.get(method.key, None)
                if val is None:
                    val = self.service_method_map[method.key] = []

                if len(val) == 0:
                    val.append((s, method))

                elif method.aux is not None:
                    val.append((s, method))

                elif val[0][1].aux is not None:
                    val.insert((s,method), 0)

                else:
                    os, om = val[0]
                    raise ValueError("\nThe message %r defined in both '%s.%s'"
                                                                " and '%s.%s'"
                                % (method.key, s.__module__, s.__name__,
                                               os.__module__, os.__name__,
                                ))

        logger.debug("From this point on, you're not supposed to make any changes "
                    "to the class & method structure of the exposed services.")

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

    def add_class(self, cls):
        if self.has_class(cls):
            return

        ns = cls.get_namespace()
        tn = cls.get_type_name()

        if not (ns in self.imports):
            self.imports[ns] = set()

        extends = getattr(cls, '__extends__', None)
        if not (extends is None):
            self.add_class(extends)
            parent_ns = extends.get_namespace()
            if parent_ns != ns and not parent_ns in self.imports[ns]:
                self.imports[ns].add(parent_ns)
                logger.debug("\timporting %r to %r because %r extends %r" % (
                    parent_ns, ns, cls.get_type_name(), extends.get_type_name()))

        class_key = '{%s}%s' % (ns, tn)
        logger.debug('\tadding class %r for %r' % (repr(cls), class_key))

        assert class_key not in self.classes, ("Somehow, you're trying to "
            "overwrite %r by %r for class key %r." %
                                      (self.classes[class_key], cls, class_key))
        self.classes[class_key] = cls

        if ns == self.get_tns():
            self.classes[tn] = cls

        if issubclass(cls, ComplexModelBase):
            # FIXME: this looks like a hack.
            if cls.get_type_name() is ModelBase.Empty:
                (child, ) = cls._type_info.values()
                cls.__type_name__ = '%sArray' % child.get_type_name()

            for k,v in cls._type_info.items():
                if v is None:
                    continue

                self.add_class(v)
                child_ns = v.get_namespace()
                if child_ns != ns and not child_ns in self.imports[ns] and \
                                                self.is_valid_import(child_ns):
                    self.imports[ns].add(child_ns)
                    logger.debug("\timporting %r to %r for %s.%s(%r)" %
                                      (child_ns, ns, cls.get_type_name(), k, v))

    def is_valid_import(self, ns):
        if ns is None:
            raise ValueError(ns)
        return self.import_base_namespaces or not (ns in namespace.const_prefmap)


class AllYourInterfaceDocuments(object):
    def __init__(self, interface):
        if spyne.interface.HAS_WSDL:
            from spyne.interface.wsdl import Wsdl11
            self.wsdl11 = Wsdl11(interface)
        else:
            self.wsdl11 = None


class InterfaceDocumentBase(object):
    """Base class for all interface document implementations.

    :param interface: A :class:`spyne.interface.InterfaceBase` instance.
    """

    def __init__(self, interface):
        self.interface = interface
        self.event_manager = EventManager(self)

    def build_interface_document(self, cls):
        """This function is supposed to be called just once, as late as possible
        into the process start. It builds the interface document and caches it
        somewhere. The overriding function should never call the overridden
        function as this may result in the same event firing more than once.
        """

        raise NotImplementedError('Extend and override.')

    def get_interface_document(self, cls):
        """This function is called by server transports that try to satisfy the
        request for the interface document. This should just return a previously
        cached interface document.
        """

        raise NotImplementedError('Extend and override.')
