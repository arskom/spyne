
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

"""
This module contains the :class:`Service` class and its helper objects.
"""

import logging
logger = logging.getLogger(__name__)

from spyne.util.six.moves.collections_abc import Sequence

from spyne.evmgr import EventManager
from spyne.util import six
from spyne.util.oset import oset


class ServiceBaseMeta(type):
    """Adds event managers."""

    def __init__(self, cls_name, cls_bases, cls_dict):
        super(ServiceBaseMeta, self).__init__(cls_name, cls_bases, cls_dict)

        self.public_methods = {}
        self.event_manager = EventManager(self,
                                      self.__get_base_event_handlers(cls_bases))

    def __get_base_event_handlers(self, cls_bases):
        handlers = {}

        for base in cls_bases:
            evmgr = getattr(base, 'event_manager', None)
            if evmgr is None:
                continue

            for k, v in evmgr.handlers.items():
                handler = handlers.get(k, oset())
                for h in v:
                    handler.add(h)
                handlers[k] = handler

        return handlers

class ServiceMeta(ServiceBaseMeta):
    """Creates the :class:`spyne.MethodDescriptor` objects by iterating over
    tagged methods.
    """

    def __init__(self, cls_name, cls_bases, cls_dict):
        super(ServiceMeta, self).__init__(cls_name, cls_bases, cls_dict)

        self.__has_aux_methods = self.__aux__ is not None
        has_nonaux_methods = None

        for k, v in cls_dict.items():
            if not hasattr(v, '_is_rpc'):
                continue

            descriptor = v(_default_function_name=k, _service_class=self)

            # these two lines are needed for staticmethod wrapping to work
            setattr(self, k, staticmethod(descriptor.function))
            descriptor.reset_function(getattr(self, k))

            try:
                getattr(self, k).descriptor = descriptor
            except AttributeError:
                pass
                # FIXME: this fails with builtins. Temporary hack while we
                # investigate whether we really need this or not

            self.public_methods[k] = descriptor
            if descriptor.aux is None and self.__aux__ is None:
                has_nonaux_methods = True
            else:
                self.__has_aux_methods = True

            if self.__has_aux_methods and has_nonaux_methods:
                raise Exception("You can't mix primary and "
                                "auxiliary methods in a single service definition.")

    def is_auxiliary(self):
        return self.__has_aux_methods


# FIXME: To be renamed to ServiceBase in Spyne 3
@six.add_metaclass(ServiceBaseMeta)
class ServiceBaseBase(object):
    __in_header__ = None
    """The incoming header object that the methods under this service definition
    accept."""

    __out_header__ = None
    """The outgoing header object that the methods under this service definition
    accept."""

    __service_name__ = None
    """The name of this service definition as exposed in the interface document.
    Defaults to the class name."""

    __service_module__ = None
    """This is used for internal idenfitication of the service class,
    to override the ``__module__`` attribute."""

    __port_types__ = ()
    """WSDL-Specific portType mappings"""

    __aux__ = None
    """The auxiliary method type. When set, the ``aux`` property of every method
    defined under this service is set to this value. The _aux flag in the @srpc
    decorator overrides this."""

    @classmethod
    def get_service_class_name(cls):
        return cls.__name__

    @classmethod
    def get_service_name(cls):
        if cls.__service_name__ is None:
            return cls.__name__
        else:
            return cls.__service_name__

    @classmethod
    def get_service_module(cls):
        if cls.__service_module__ is None:
            return cls.__module__
        else:
            return cls.__service_module__

    @classmethod
    def get_internal_key(cls):
        return "%s.%s" % (cls.get_service_module(), cls.get_service_name())

    @classmethod
    def get_port_types(cls):
        return cls.__port_types__

    @classmethod
    def _has_callbacks(cls):
        """Determines if this service definition has callback methods or not."""

        for method in cls.public_methods.values():
            if method.is_callback:
                return True

        return False

    @classmethod
    def get_context(cls):
        """Returns a user defined context. Override this in your ServiceBase
        subclass to customize context generation."""
        return None

    @classmethod
    def call_wrapper(cls, ctx, args=None):
        """Called in place of the original method call. You can override this to
        do your own exception handling.

        :param ctx: The method context.

        The overriding function must call this function by convention.
        """

        if ctx.function is not None:
            if args is None:
                args = ctx.in_object

                assert not isinstance(args, six.string_types)

                # python3 wants a proper sequence as *args
                if not isinstance(args, Sequence):
                    args = tuple(args)

                if not ctx.descriptor.no_ctx:
                    args = (ctx,) + tuple(args)

            return ctx.function(*args)

    @classmethod
    def initialize(cls, app):
        pass


@six.add_metaclass(ServiceMeta)
class Service(ServiceBaseBase):
    """The ``Service`` class is the base class for all service definitions.

    The convention is to have public methods defined under a subclass of this
    class along with common properties of public methods like header classes or
    auxiliary processors. The :func:`spyne.decorator.srpc` decorator or its
    wrappers should be used to flag public methods.

    This class is designed to be subclassed just once. You're supposed to
    combine Service subclasses in order to get the public method mix you
    want.

    It is a natural abstract base class, because it's of no use without any
    method definitions, hence the 'Base' suffix in the name.

    This class supports the following events:
        * ``method_call``
            Called right before the service method is executed

        * ``method_return_object``
            Called right after the service method is executed

        * ``method_exception_object``
            Called when an exception occurred in a service method, before the
            exception is serialized.

        * ``method_accept_document``
            Called by the transport right after the incoming stream is parsed to
            the incoming protocol's document type.

        * ``method_return_document``
            Called by the transport right after the outgoing object is
            serialized to the outgoing protocol's document type.

        * ``method_exception_document``
            Called by the transport right before the outgoing exception object
            is serialized to the outgoing protocol's document type.

        * ``method_return_string``
            Called by the transport right before passing the return string to
            the client.

        * ``method_exception_string``
            Called by the transport right before passing the exception string to
            the client.
    """


# FIXME: To be deleted in Spyne 3
ServiceBase = Service
