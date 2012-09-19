
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

from spyne.model.fault import Fault
from spyne.interface import Interface
from spyne._base import EventManager
from spyne.util.appreg import register_application


def get_fault_string_from_exception(e):
    return str(e)

def return_traceback_in_unhandled_exceptions():
    """Call this function first thing in your main function to return tracebacks
    to your clients in case of unhandled exceptions.
    """

    global get_fault_string_from_exception

    import traceback
    def _get_fault_string_from_exception(e):
        return traceback.format_exc()
    get_fault_string_from_exception = _get_fault_string_from_exception

class Application(object):
    '''The Application class is the glue between one or more service
    definitions, input and output protocols.

    :param services:     An iterable of ServiceBase subclasses that define
                         the exposed services.
    :param tns:          The targetNamespace attribute of the exposed
                         service.
    :param name:         The optional name attribute of the exposed service.
                         The default is the name of the application class
                         which is by default 'Application'.
    :param in_protocol:  A ProtocolBase instance that denotes the input
                         protocol. It's only optional for NullServer transport.
    :param out_protocol: A ProtocolBase instance that denotes the output
                         protocol. It's only optional for NullServer transport.
    :param interface:    Ignored. Kept for backwards-compatibility purposes.

    Supported events:
        * method_call:
            Called right before the service method is executed

        * method_return_object:
            Called right after the service method is executed

        * method_exception_object:
            Called when an exception occurred in a service method, before the
            exception is serialized.

        * method_context_constructed:
            Called from the constructor of the MethodContext instance.

        * method_context_destroyed:
            Called from the destructor of the MethodContext instance.
    '''

    transport = None

    def __init__(self, services, tns, name=None,
                           in_protocol=None, out_protocol=None, interface=None):
        self.services = services
        self.tns = tns
        self.name = name

        if self.name is None:
            self.name = self.__class__.__name__.split('.')[-1]

        self.event_manager = EventManager(self)
        self.error_handler = None

        self.interface = Interface(self)
        self.in_protocol = in_protocol
        self.out_protocol = out_protocol

        self.in_protocol.set_app(self)
        self.out_protocol.set_app(self)

        register_application(self)

        self.reinitialize()

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
                # otherwise, the return value should already be wrapped in an
                # iterable.
                ctx.out_object = [ctx.out_object]

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

            ctx.out_error = Fault('Server', get_fault_string_from_exception(e))

            # fire events
            self.event_manager.fire_event('method_exception_object', ctx)
            if ctx.service_class != None:
                ctx.service_class.event_manager.fire_event(
                                                'method_exception_object', ctx)

    def call_wrapper(self, ctx):
        """This method calls the call_wrapper method in the service definition.
        This can be overridden to make an application-wide custom exception
        management.
        """

        return ctx.service_class.call_wrapper(ctx)

    def _has_callbacks(self):
        return self.interface._has_callbacks()

    def reinitialize(self):
        from spyne.server import ServerBase

        server = ServerBase(self)
        aux_memo = set()
        for s,d in self.interface.method_id_map.values():
            if d.aux is not None and not id(d.aux) in aux_memo:
                d.aux.initialize(server)
                aux_memo.add(id(d.aux))

    def __hash__(self):
        return hash(tuple([id(s) for s in self.services]))
