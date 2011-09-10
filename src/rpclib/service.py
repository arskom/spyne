
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

from rpclib._base import EventManager
from rpclib.util.oset import oset

class ServiceBaseMeta(type):
    def __init__(self, cls_name, cls_bases, cls_dict):
        super(ServiceBaseMeta, self).__init__(cls_name, cls_bases, cls_dict)

        self.public_methods = {}
        self.event_manager = EventManager(self,
                                      self.__get_base_event_handlers(cls_bases))

        for k, v in cls_dict.iteritems():
            if hasattr(v, '_is_rpc'):
                descriptor = v(_default_function_name=k)
                self.public_methods[k] = descriptor
                setattr(self, k, staticmethod(descriptor.function))
                descriptor.function = getattr(self, k)

    def __get_base_event_handlers(self, cls_bases):
        handlers = {}

        for base in cls_bases:
            evmgr = getattr(base,'event_manager',None)
            if evmgr is None:
                continue

            for k,v in evmgr.handlers.items():
                handler=handlers.get(k,oset())
                for h in v:
                    handler.add(h)
                handlers[k]=handler

        return handlers

class ServiceBase(object):
    '''This class serves as the base for all service definitions. Subclasses of
    this class will use the srpc decorator or its wrappers to flag methods to be
    exposed.

    It is a natural abstract base class, because it's of no use without any
    method definitions, hence the 'Base' suffix in the name.
    '''

    __metaclass__ = ServiceBaseMeta

    __tns__ = None
    """For internal use only. You should use the tns argument to the Application
    constructor to define the target namespace."""

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

    @classmethod
    def get_service_class_name(cls):
        return cls.__name__

    @classmethod
    def get_service_name(cls):
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
        '''
        if ctx.descriptor.no_ctx:
            return ctx.descriptor.function(*ctx.in_object)
        else:
            return ctx.descriptor.function(ctx, *ctx.in_object)
