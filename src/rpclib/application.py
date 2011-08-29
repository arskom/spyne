
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

from rpclib.model.fault import Fault
from rpclib._base import EventManager

class Application(object):
    transport = None

    def __init__(self, services, interface_class, in_protocol_class,
                                      out_protocol_class=None, *args, **kwargs):
        '''Constructor.

        @param An iterable of ServiceBase subclasses that define the exposed
               services.
        @param The targetNamespace attribute of the exposed service.
        @param The name attribute of the exposed service.
        '''

        if out_protocol_class is None:
            out_protocol_class = in_protocol_class

        self.interface = interface_class(self, services, *args, **kwargs)

        self.in_protocol = in_protocol_class(self)
        self.out_protocol = out_protocol_class(self)

        self.__public_methods = {}
        self.__classes = {}

        self.event_manager = EventManager(self)
        self.error_handler = None

    def process_request(self, ctx, req_obj):
        """Takes a MethodContext instance and the native request object.
        Returns the response to the request as a native python object.

        Not meant to be overridden.
        """

        try:
            # implementation hook
            ctx.service_class.event_manager.fire_event('method_call', ctx)

            # call the method
            ctx.out_object = ctx.service_class.call_wrapper(ctx, ctx.descriptor.function, req_obj)

            # fire events
            self.event_manager.fire_event('method_return_object', ctx)
            ctx.service_class.event_manager.fire_event(
                                                    'method_return_object', ctx)

        except Fault, e:
            logger.exception(e)

            ctx.out_error = e

            # fire events
            self.event_manager.fire_event('method_exception_object', ctx)
            if ctx.service_class != None:
                ctx.service_class.event_manager.fire_event(
                                                    'method_return_object', ctx)

        except Exception, e:
            logger.exception(e)

            ctx.out_error = Fault('Server', str(e))

            # fire events
            self.event_manager.fire_event('method_exception_object', ctx)
            if ctx.service_class != None:
                ctx.service_class.event_manager.fire_event(
                                                    'method_return_object', ctx)

    def _has_callbacks(self):
        return self.interface._has_callbacks()
