
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

class ServiceBaseMeta(type):
    def __init__(self, cls_name, cls_bases, cls_dict):
        super(ServiceBaseMeta, self).__init__(cls_name, cls_bases, cls_dict)

        self.public_methods = []
        self.event_manager = EventManager(self,
                                      self.__get_base_event_handlers(cls_bases))

        for func_name, func in cls_dict.iteritems():
            if callable(func) and hasattr(func, '_is_rpc'):
                descriptor = func(_method_descriptor=True)
                self.public_methods.append(descriptor)

                setattr(self, func_name, staticmethod(func))

    def __get_base_event_handlers(self, cls_bases):
        handlers = {}

        for base in cls_bases:
            evmgr = getattr(base,'event_manager',None)
            if evmgr is None:
                continue

            for k,v in evmgr.handlers.items():
                h=handlers.get(k,[])
                h.extend(v)
                handlers[k]=h

        return handlers

class ServiceBase(object):
    '''This class serves as the base for all service definitions.  Subclasses of
    this class will use the rpc decorator to flag methods to be exposed via soap.

    It is a natural abstract base class, because it's of no use without any
    method definitions, hence the 'Base' suffix in the name.
    '''

    __metaclass__ = ServiceBaseMeta

    __tns__ = None
    __in_header__ = None
    __out_header__ = None
    __service_name__ = None
    __port_types__ = ()

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
    def get_method(cls, name):
        '''Returns the method descriptor based on element name.'''

        for method in cls.public_methods:
            type_name = method.in_message.get_type_name()
            if '{%s}%s' % (cls.get_tns(), type_name) == name:
                return method

        for method in cls.public_methods:
            if method.public_name == name:
                return method

        raise Exception('Method "%s" not found' % name)

    @classmethod
    def _has_callbacks(cls):
        '''Determines if this object has callback methods or not.'''

        for method in cls.public_methods:
            if method.is_callback:
                return True

        return False

    @classmethod
    def call_wrapper(cls, ctx, call, params):
        '''Called in place of the original method call.

        @param the original method call
        @param the arguments to the call
        '''
        if ctx.descriptor.no_ctx:
            return call(*params)
        else:
            return call(ctx, *params)
