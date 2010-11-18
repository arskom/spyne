
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
logger = logging.getLogger("rpclib._base")

import warnings
import traceback

from rpclib.model.exception import Fault

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

class MethodDescriptor(object):
    '''This class represents the method signature of a soap method,
    and is returned by the rpc decorator.
    '''

    def __init__(self, name, public_name, in_message, out_message, doc,
                 is_callback=False, is_async=False, mtom=False, in_header=None,
                 out_header=None):

        self.name = name
        self.public_name = public_name
        self.in_message = in_message
        self.out_message = out_message
        self.doc = doc
        self.is_callback = is_callback
        self.is_async = is_async
        self.mtom = mtom
        self.in_header = in_header
        self.out_header = out_header

class Application(object):
    transport = None

    class NO_WRAPPER:
        pass
    class IN_WRAPPER:
        pass
    class OUT_WRAPPER:
        pass

    def __init__(self, services, protocol_class, interface_class, *args, **kwargs):
        '''Constructor.

        @param An iterable of ServiceBase subclasses that define the exposed
               services.
        @param The targetNamespace attribute of the exposed service.
        @param The name attribute of the exposed service.
        '''

        self.protocol = protocol_class(self)
        self.interface = interface_class(self, services, *args, **kwargs)
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

    def serialize(self, ctx, wrapper, out_object):
        """Takes a MethodContext instance and the object to be serialied.
        Returns the corresponding xml structure as an lxml.etree._Element
        instance.

        Not meant to be overridden.
        """
        return self.protocol.serialize(ctx, wrapper, out_object)

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
