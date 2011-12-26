
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


"""This module contains the Application class, to which every other rpclib
component is integrated.
"""


import logging
logger = logging.getLogger(__name__)

from rpclib.model.fault import Fault
from rpclib._base import EventManager

class Application(object):
    '''This class is the glue between one or more service definitions,
    interface and protocol choices.

    :param services:     An iterable of ServiceBase subclasses that define
                         the exposed services.
    :param tns:          The targetNamespace attribute of the exposed
                         service.
    :param interface:    An InterfaceBase instance that sets the service
                         definition document standard.
    :param in_protocol:  A ProtocolBase instance that defines the input
                         protocol.
    :param out_protocol: A ProtocolBase instance that defines the output
                         protocol.
    :param name:         The optional name attribute of the exposed service.
                         The default is the name of the application class
                         which is, by default, 'Application'.

    Supported events:
        * method_call
            Called right before the service method is executed

        * method_return_object
            Called right after the service method is executed

        * method_exception_object
            Called when an exception occurred in a service method, before the
            exception is serialized.

        * method_context_constructed
            Called from the constructor of the MethodContext instance.

        * method_context_destroyed
            Called from the destructor of the MethodContext instance.
    '''

    transport = None

    def __init__(self, services, tns, interface, in_protocol, out_protocol,
                                        name=None, supports_fanout_methods=False):

        self.services = services
        self.tns = tns
        self.name = name
        self.supports_fanout_methods = supports_fanout_methods

        if self.name is None:
            self.name = self.__class__.__name__.split('.')[-1]

        self.in_protocol = in_protocol
        self.in_protocol.set_app(self)

        self.out_protocol = out_protocol
        self.out_protocol.set_app(self)

        self.interface = interface
        self.interface.set_app(self)

        self.__public_methods = {}
        self.__classes = {}

        self.event_manager = EventManager(self)
        self.error_handler = None

    def process_request(self, ctx):
        """Takes a MethodContext instance. Returns the response to the request
        as a native python object. If the function throws an exception, it
        returns None and sets the exception object to ctx.out_error.

        Overriding this method would break event management. So this is not
        meant to be overridden unless you know what you're doing.
        """

        try:
            # fire events
            self.event_manager.fire_event('method_call', ctx)
            ctx.service_class.event_manager.fire_event('method_call', ctx)

            # call the method
            ctx.out_object = self.call_wrapper(ctx)

            # out object is always an iterable of return values. see
            # MethodContext docstrings for more info
            if len(ctx.descriptor.out_message._type_info) == 0:
                ctx.out_object = [None]
            elif len(ctx.descriptor.out_message._type_info) == 1:
                ctx.out_object = [ctx.out_object]
            # otherwise, the return value should already be wrapped in an
            # iterable.

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
                                                'method_exception_object', ctx)

        except Exception, e:
            logger.exception(e)

            ctx.out_error = Fault('Server', str(e))

            # fire events
            self.event_manager.fire_event('method_exception_object', ctx)
            if ctx.service_class != None:
                ctx.service_class.event_manager.fire_event(
                                                'method_exception_object', ctx)

    def call_wrapper(self, ctx):
        """This method calls the call_wrapper method in the service definition.
        This can be overridden to make an application-wide custom exception
        management."""

        return ctx.service_class.call_wrapper(ctx)

    def _has_callbacks(self):
        return self.interface._has_callbacks()
