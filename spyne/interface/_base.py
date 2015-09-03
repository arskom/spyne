
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

from collections import deque, defaultdict

import spyne.interface

from spyne import EventManager, MethodDescriptor
from spyne.const import xml_ns as namespace

from spyne.model import ModelBase
from spyne.model import Array, Iterable
from spyne.model import ComplexModelBase
from spyne.model.complex import XmlModifier
from spyne.util.six import get_function_name


def _generate_method_id(cls, descriptor):
    return '.'.join([
            cls.__module__,
            cls.__name__,
            descriptor.name,
        ])


class Interface(object):
    """The ``Interface`` class holds all information needed to build an
    interface document.

    :param app: A :class:`spyne.application.Application` instance.
    """

    def __init__(self, app=None, import_base_namespaces=False):
        self.__ns_counter = 0
        self.__app = None
        self.url = None
        self.classes = {}
        self.imports = {}
        self.service_method_map = {}
        self.method_id_map = {}
        self.nsmap = {}
        self.prefmap = {}
        self.member_methods = deque()
        self.method_descriptor_id_to_key = {}
        self.service_attrs = defaultdict(dict)

        self.import_base_namespaces = import_base_namespaces
        self.app = app

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
        self.member_methods = deque()

        self.nsmap['tns'] = self.get_tns()
        self.prefmap[self.get_tns()] = 'tns'
        self.deps = defaultdict(set)

    def has_class(self, cls):
        """Returns true if the given class is already included in the interface
        object somewhere."""

        ns = cls.get_namespace()
        tn = cls.get_type_name()

        c = self.classes.get('{%s}%s' % (ns, tn))
        if c is None:
            return False

        if issubclass(c, ComplexModelBase) and \
                                              issubclass(cls, ComplexModelBase):
            o1 = getattr(cls, '__orig__', None) or cls
            o2 = getattr(c, '__orig__', None) or c

            if o1 is o2:
                return True

            # So that "Array"s and "Iterable"s don't conflict.
            if set((o1, o2)) == set((Array, Iterable)):
                return True

            raise ValueError("classes %r and %r have conflicting names." %
                                                                       (cls, c))
        return True

    def get_class(self, key):
        """Returns the class definition that corresponds to the given key.
        Keys are in '{namespace}class_name' form.

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

    def add_method(self, method):
        """Generator method that adds the given method descriptor to the
        interface. Also extracts and yields all the types found in there.

        :param method: A :class:`MethodDescriptor` instance
        :returns: Sequence of :class:`spyne.model.ModelBase` subclasses.
        """

        if not (method.in_header is None):
            if not isinstance(method.in_header, (list, tuple)):
                method.in_header = (method.in_header,)

            for in_header in method.in_header:
                in_header.resolve_namespace(in_header, self.get_tns())
                if method.aux is None:
                    yield in_header
                in_header_ns = in_header.get_namespace()
                if in_header_ns != self.get_tns() and \
                                             self.is_valid_import(in_header_ns):
                    self.imports[self.get_tns()].add(in_header_ns)

        if not (method.out_header is None):
            if not isinstance(method.out_header, (list, tuple)):
                method.out_header = (method.out_header,)

            for out_header in method.out_header:
                out_header.resolve_namespace(out_header, self.get_tns())
                if method.aux is None:
                    yield out_header
                out_header_ns = out_header.get_namespace()
                if out_header_ns != self.get_tns() and \
                                            self.is_valid_import(out_header_ns):
                    self.imports[self.get_tns()].add(out_header_ns)

        if method.faults is None:
            method.faults = []
        elif not (isinstance(method.faults, (list, tuple))):
            method.faults = (method.faults,)

        for fault in method.faults:
            fault.__namespace__ = self.get_tns()
            fault.resolve_namespace(fault, self.get_tns())
            if method.aux is None:
                yield fault

        method.in_message.resolve_namespace(method.in_message, self.get_tns())
        in_message_ns = method.in_message.get_namespace()
        if in_message_ns != self.get_tns() and \
                                            self.is_valid_import(in_message_ns):
            self.imports[self.get_tns()].add(method.in_message.get_namespace())

        if method.aux is None:
            yield method.in_message

        method.out_message.resolve_namespace(method.out_message, self.get_tns())
        assert not method.out_message.get_type_name() is method.out_message.Empty

        out_message_ns = method.out_message.get_namespace()
        if out_message_ns != self.get_tns() and \
                                           self.is_valid_import(out_message_ns):
            self.imports[self.get_tns()].add(out_message_ns)

        if method.aux is None:
            yield method.out_message

        for p in method.patterns:
            p.endpoint = method

    def process_method(self, s, method):
        assert isinstance(method, MethodDescriptor)

        method_key = '{%s}%s' % (self.app.tns, method.name)

        if issubclass(s, ComplexModelBase) and method.in_message_name_override:
            method_key = '{%s}%s.%s' % (self.app.tns,
                                                 s.get_type_name(), method.name)
        key = _generate_method_id(s, method)
        if key in self.method_id_map:
            c = self.method_id_map[key].parent_class
            if c is s:
                pass
            elif c.__orig__ is None:
                assert c is s.__orig__, "%r.%s conflicts with %r.%s" % \
                                        (c, key, s.__orig__, key)
            elif s.__orig__ is None:
                assert c.__orig__ is s, "%r.%s conflicts with %r.%s" % \
                                        (c.__orig__, key, s, key)
            else:
                assert c.__orig__ is s.__orig__, "%r.%s conflicts with %r.%s" % \
                                        (c.__orig__, key, s.__orig__, key)
            return

        logger.debug('  adding method %s.%s to match %r tag.', s.__name__,
                                 get_function_name(method.function), method_key)

        self.method_id_map[key] = method

        val = self.service_method_map.get(method_key, None)
        if val is None:
            val = self.service_method_map[method_key] = []

        if len(val) == 0:
            val.append(method)

        elif method.aux is not None:
            val.append(method)

        elif val[0].aux is not None:
            val.insert(method, 0)

        else:
            om = val[0]
            os = om.service_class
            if os is None:
                os = om.parent_class
            raise ValueError("\nThe message %r defined in both '%s.%s'"
                                                         " and '%s.%s'"
                                    % (method.name, s.__module__,  s.__name__,
                                                   os.__module__, os.__name__))

    def check_method(self, method):
        """Override this if you need to cherry-pick methods added to the
        interface document."""

        return True

    def populate_interface(self, types=None):
        """Harvests the information stored in individual classes' _type_info
        dictionaries. It starts from function definitions and includes only
        the used objects.
        """

        # populate types
        for s in self.services:
            logger.debug("populating '%s.%s (%s)' types...", s.__module__,
                                        s.__name__, s.get_service_key(self.app))

            for method in s.public_methods.values():
                if method.in_header is None:
                    method.in_header = s.__in_header__
                if method.out_header is None:
                    method.out_header = s.__out_header__
                if method.aux is None:
                    method.aux = s.__aux__
                if method.aux is not None:
                    method.aux.methods.append(_generate_method_id(s, method))

                if not self.check_method(method):
                    logger.debug("method %s' discarded by check_method",
                                                               method.class_key)
                    continue

                logger.debug("  enumerating classes for method '%s'",
                                                               method.class_key)
                for cls in self.add_method(method):
                    self.add_class(cls)

        # populate call routes for service methods
        for s in self.services:
            self.service_attrs[s]['tns'] = self.get_tns()
            logger.debug("populating '%s.%s' routes...", s.__module__,
                                                                     s.__name__)
            for method in s.public_methods.values():
                self.process_method(s, method)

        # populate call routes for member methods
        for cls, descriptor in self.member_methods:
            self.process_method(cls.__orig__ or cls, descriptor)

        # populate method descriptor id to method key map
        self.method_descriptor_id_to_key = dict(((id(v[0]), k)
                                    for k,v in self.service_method_map.items()))

        logger.debug("From this point on, you're not supposed to make any "
                     "changes to the class and method structure of the exposed "
                     "services.")

    tns = property(get_tns)

    def get_namespace_prefix(self, ns):
        """Returns the namespace prefix for the given namespace. Creates a new
        one automatically if it doesn't exist.

        Not meant to be overridden.
        """

        if not (isinstance(ns, str) or isinstance(ns, unicode)):
            raise TypeError(ns)

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

    def add_class(self, cls, add_parent=True):
        if self.has_class(cls):
            return

        ns = cls.get_namespace()
        tn = cls.get_type_name()

        assert ns is not None, ('either assign a namespace to the class or call'
                        ' cls.resolve_namespace(cls, "some_default_ns") on it.')

        if not (ns in self.imports) and self.is_valid_import(ns):
            self.imports[ns] = set()

        class_key = '{%s}%s' % (ns, tn)
        logger.debug('    adding class %r for %r', repr(cls), class_key)

        assert class_key not in self.classes, ("Somehow, you're trying to "
            "overwrite %r by %r for class key %r." %
                                      (self.classes[class_key], cls, class_key))

        assert not (cls.get_type_name() is cls.Empty), cls

        self.deps[cls]  # despite the appearances, this is not totally useless.
        self.classes[class_key] = cls
        if ns == self.get_tns():
            self.classes[tn] = cls

        # add parent class
        extends = getattr(cls, '__extends__', None)
        while extends is not None and \
                                   (extends.get_type_name() is ModelBase.Empty):
            extends = getattr(extends, '__extends__', None)

        if add_parent and extends is not None:
            assert issubclass(extends, ModelBase)
            self.deps[cls].add(extends)
            self.add_class(extends)
            parent_ns = extends.get_namespace()
            if parent_ns != ns and not parent_ns in self.imports[ns] and \
                                                self.is_valid_import(parent_ns):
                self.imports[ns].add(parent_ns)
                logger.debug("    importing %r to %r because %r extends %r",
                                            parent_ns, ns, cls.get_type_name(),
                                            extends.get_type_name())

        # add fields
        if issubclass(cls, ComplexModelBase):
            for k, v in cls._type_info.items():
                if v is None:
                    continue

                self.deps[cls].add(v)

                logger.debug("    adding %s.%s = %r", cls.get_type_name(), k, v)
                if v.get_namespace() is None:
                    v.resolve_namespace(v, ns)

                self.add_class(v)

                if v.get_namespace() is None and cls.get_namespace() is not None:
                    v.resolve_namespace(v, cls.get_namespace())

                child_ns = v.get_namespace()
                if child_ns != ns and not child_ns in self.imports[ns] and \
                                                 self.is_valid_import(child_ns):
                    self.imports[ns].add(child_ns)
                    logger.debug("    importing %r to %r for %s.%s(%r)",
                                       child_ns, ns, cls.get_type_name(), k, v)

                if issubclass(v, XmlModifier):
                    self.add_class(v.type)

                    child_ns = v.type.get_namespace()
                    if child_ns != ns and not child_ns in self.imports[ns] and \
                                                 self.is_valid_import(child_ns):
                        self.imports[ns].add(child_ns)
                        logger.debug("    importing %r to %r for %s.%s(%r)",
                                    child_ns, ns, v.get_type_name(), k, v.type)

            if cls.Attributes.methods is not None:
                logger.debug("    populating member methods for '%s.%s'...",
                                       cls.get_namespace(), cls.get_type_name())

                for method_key, descriptor in cls.Attributes.methods.items():
                    assert hasattr(cls, method_key)

                    self.member_methods.append((cls, descriptor))
                    for c in self.add_method(descriptor):
                        self.add_class(c)

            if cls.Attributes._subclasses is not None:
                logger.debug("    adding subclasses of '%s.%s'...",
                                       cls.get_namespace(), cls.get_type_name())

                for c in cls.Attributes._subclasses:
                    c.resolve_namespace(c, ns)

                    child_ns = c.get_namespace()
                    if child_ns == ns:
                        if not self.has_class(c):
                            self.add_class(c, add_parent=False)
                            self.deps[c].add(cls)
                    else:
                        logger.debug("    not adding %r to %r because it would "
                            "cause circular imports because %r extends %r and "
                            "they don't have the same namespace", child_ns,
                                     ns, c.get_type_name(), cls.get_type_name())

    def is_valid_import(self, ns):
        """This will return False for base namespaces unless told otherwise."""

        if ns is None:
            raise ValueError(ns)

        return self.import_base_namespaces or not (ns in namespace.const_prefmap)


class AllYourInterfaceDocuments(object):
    # AreBelongToUs
    def __init__(self, interface, wsdl11=None):
        self.wsdl11 = wsdl11
        if self.wsdl11 is None and spyne.interface.HAS_WSDL:
            from spyne.interface.wsdl import Wsdl11
            self.wsdl11 = Wsdl11(interface)


class InterfaceDocumentBase(object):
    """Base class for all interface document implementations.

    :param interface: A :class:`spyne.interface.InterfaceBase` instance.
    """

    def __init__(self, interface):
        self.interface = interface
        self.event_manager = EventManager(self)

    def build_interface_document(self):
        """This function is supposed to be called just once, as late as possible
        into the process start. It builds the interface document and caches it
        somewhere. The overriding function should never call the overridden
        function as this may result in the same event firing more than once.
        """

        raise NotImplementedError('Extend and override.')

    def get_interface_document(self):
        """This function is called by server transports that try to satisfy the
        request for the interface document. This should just return a previously
        cached interface document.
        """

        raise NotImplementedError('Extend and override.')
