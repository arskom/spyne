
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

import traceback

import rpclib.interface.base
import rpclib.protocol.base
from rpclib.model.exception import Fault

from collections import deque

class MethodContext(object):
    def __init__(self):
        self.service = None
        self.service_class = None

        self.in_error = None
        self.in_header_doc = None
        self.in_body_doc = None

        self.out_error = None
        self.out_header_doc = None
        self.out_body_doc = None

        self.method_name = None
        self.descriptor = None

    def __repr__(self):
        retval = deque()
        for k,v in self.__dict__.items():
            if isinstance(v,dict):
                ret = deque(['{'])
                items = v.items()
                items.sort()
                for k2,v2 in items:
                    ret.append('\t\t%r: %r,' % (k2, v2))
                ret.append('\t}')
                ret='\n'.join(ret)
                retval.append("\n\t%s=%s" % (k,ret))
            else:
                retval.append("\n\t%s=%r" % (k,v))

        retval.append('\n)')
        return ''.join((self.__class__.__name__, '(', ', '.join(retval), ')'))

class Application(object):
    transport = None

    def __init__(self, services, interface_class, in_protocol_class, out_protocol_class=None, *args, **kwargs):
        '''Constructor.

        @param An iterable of ServiceBase subclasses that define the exposed
               services.
        @param The targetNamespace attribute of the exposed service.
        @param The name attribute of the exposed service.
        '''

        if out_protocol_class is None:
            out_protocol_class = in_protocol_class

        assert issubclass(interface_class, rpclib.interface.base.Base), interface_class
        assert issubclass(in_protocol_class, rpclib.protocol.base.Base), in_protocol_class
        assert issubclass(out_protocol_class, rpclib.protocol.base.Base), out_protocol_class

        self.interface = interface_class(self, services, *args, **kwargs)
        self.in_protocol = in_protocol_class(self)
        self.out_protocol = out_protocol_class(self)
        self.services = services

        self.__public_methods = {}
        self.__classes = {}

    def get_class(self, key):
        return self.interface.get_class(key)

    def get_class_instance(self, key):
        return self.interface.get_class_instance(key)

    def process_request(self, ctx, req_obj):
        """Takes a MethodContext instance and the native request object.
        Returns the response to the request as a native python object.

        Not meant to be overridden.
        """

        try:
            # implementation hook
            ctx.service.on_method_call(ctx.method_name,req_obj,ctx.in_body_doc)

            # retrieve the method
            func = getattr(ctx.service, ctx.descriptor.name)

            # call the method
            retval = ctx.service.call_wrapper(func, req_obj)

        except Fault, e:
            stacktrace=traceback.format_exc()
            logger.error(stacktrace)

            retval = e

        except Exception, e:
            stacktrace=traceback.format_exc()
            logger.error(stacktrace)

            retval = Fault('Server', str(e))

        # implementation hook
        if isinstance(retval, Fault):
            ctx.service.on_method_exception_object(retval)
            self.on_exception_object(retval)

        else:
            ctx.service.on_method_return_object(retval)

        return retval

    def get_service_class(self, method_name):
        """This call maps method names to the services that will handle them.

        Override this function to alter the method mappings. Just try not to get
        too crazy with regular expressions :)
        """

        return self.interface.call_routes[method_name]

    def get_service(self, service, http_req_env=None):
        """The function that maps service classes to service instances.

        Override this function to e.g. pass additional parameters to service
        constructors.
        """

        return service(http_req_env)

    def _has_callbacks(self):
        retval = False

        for s in self.services:
            if self.get_service(s)._has_callbacks():
                return True

        return retval

    def on_exception_object(self, exc):
        '''Called when the app throws an exception. (might be inside or outside
        the service call).

        @param The exception object
        '''

    def on_exception_doc(self, fault_doc):
        '''Called when the app throws an exception. (might be inside or outside
        the service call.

        @param The document root containing the serialized form of the exception.
        '''
