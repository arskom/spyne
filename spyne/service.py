
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

from spyne._base import BODY_STYLE_EMPTY
import logging
logger = logging.getLogger(__name__)

from spyne._base import BODY_STYLE_BARE
from spyne._base import EventManager
from spyne.util.oset import oset

'''This module contains the :class:`ServiceBase` class and its helper objects.
'''

class ServiceBaseMeta(type):
    '''Creates the :class:`spyne.MethodDescriptor` objects by iterating over
    tagged methods.
    '''

    def __init__(self, cls_name, cls_bases, cls_dict):
        super(ServiceBaseMeta, self).__init__(cls_name, cls_bases, cls_dict)

        self.__has_aux_methods = self.__aux__ is not None
        self.public_methods = {}
        self.event_manager = EventManager(self,
                                      self.__get_base_event_handlers(cls_bases))

        for k, v in cls_dict.items():
            if hasattr(v, '_is_rpc'):
                descriptor = v(_default_function_name=k)

                # these two lines are needed for staticmethod wrapping to work
                setattr(self, k, staticmethod(descriptor.function))
                descriptor.reset_function(getattr(self, k))

                self.public_methods[k] = descriptor
                if descriptor.aux is None:
                    if self.__has_aux_methods and self.__aux__ is None:
                        raise Exception("you can't mix primary and "
                            "auxiliary methods in a single service definition.")
                else:
                    self.__has_aux_methods = True

                for p in descriptor.patterns:
                    p.endpoint = k

    def __get_base_event_handlers(self, cls_bases):
        handlers = {}

        for base in cls_bases:
            evmgr = getattr(base, 'event_manager', None)
            if evmgr is None:
                continue

            for k, v in evmgr.handlers.items():
                handler=handlers.get(k, oset())
                for h in v:
                    handler.add(h)
                handlers[k]=handler

        return handlers

    def is_auxiliary(self):
        return self.__has_aux_methods


class ServiceBase(object):
    '''The ``ServiceBase`` class is the base class for all service definitions.

    The convention is to have public methods defined under a subclass of this
    class along with common properties of public methods like header classes or
    auxiliary processors. The :func:`spyne.decorator.srpc` decorator or its
    wrappers should be used to flag public methods.

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
    '''

    __metaclass__ = ServiceBaseMeta

    __tns__ = None
    """For internal use only. You should use the ``tns`` argument to the
    :class:`spyne.application.Application` constructor to define the target
    namespace."""

    __in_header__ = None
    """The incoming header object that the methods under this service definition
    accept."""

    __out_header__ = None
    """The outgoing header object that the methods under this service definition
    accept."""

    __service_name__ = None
    """The name of this service definition as exposed in the interface document.
    Defaults to the class name."""

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
    def get_service_key(cls):
        return '{%s}%s' % (cls.get_tns(), cls.get_service_name())

    @classmethod
    def get_service_name(cls):
        if cls.__service_name__ is None:
            return cls.__name__
        else:
            return cls.__service_name__

    @classmethod
    def get_port_types(cls):
        return cls.__port_types__

    @classmethod
    def get_tns(cls):
        if not (cls.__tns__ is None):
            return cls.__tns__

        retval = cls.__module__
        if cls.__module__ == '__main__':
            service_name = cls.get_service_class_name().split('.')[-1]
            retval = '.'.join((service_name, service_name))

        return retval

    @classmethod
    def _has_callbacks(cls):
        '''Determines if this service definition has callback methods or not.'''

        for method in cls.public_methods.values():
            if method.is_callback:
                return True

        return False

    @classmethod
    def call_wrapper(cls, ctx):
        '''Called in place of the original method call. You can override this to
        do your own exception handling.

        :param ctx: The method context.

        The overriding function must call this function by convention.
        '''

        if ctx.descriptor.body_style is BODY_STYLE_BARE:
            ctx.in_object = [ctx.in_object]
        elif ctx.descriptor.body_style is BODY_STYLE_EMPTY:
            ctx.in_object = []

        if ctx.descriptor.no_ctx:
            return ctx.function(*ctx.in_object)
        else:
            return ctx.function(ctx, *ctx.in_object)

    @classmethod
    def get_method_id(cls, descriptor):
        return '.'.join([
                cls.__module__,
                cls.__name__,
                descriptor.name,
            ])
