
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

from time import time

from collections import deque

from spyne.const.xml_ns import DEFAULT_NS
from spyne.util.oset import oset

class BODY_STYLE_WRAPPED: pass
class BODY_STYLE_EMPTY: pass
class BODY_STYLE_BARE: pass

class AuxMethodContext(object):
    """Generic object that holds information specific to auxiliary methods"""
    def __init__(self, p_ctx, error):
        self.p_ctx = p_ctx
        """Primary context that this method was bound to."""

        self.error = error
        """Error from primary context (if any)."""


class TransportContext(object):
    """Generic object that holds transport-specific context information"""
    def __init__(self, transport, type=None):
        self.itself = transport
        """The transport itself; i.e. a ServerBase instance."""

        self.type = type
        """The protocol the transport uses."""


class ProtocolContext(object):
    """Generic object that holds transport-specific context information"""
    def __init__(self, transport, type=None):
        self.itself = transport
        """The transport itself; i.e. a ServerBase instance."""

        self.type = type
        """The protocol the transport uses."""


class EventContext(object):
    """Generic object that holds event-specific context information"""
    def __init__(self, event_id=None):
        self.event_id=event_id


class MethodContext(object):
    """The base class for all RPC Contexts. Holds all information about the
    current state of execution of a remote procedure call.
    """

    frozen = False

    @property
    def method_name(self):
        """The public name of the method the ``method_request_string`` was
        matched to.
        """

        if self.descriptor is None:
            return None
        else:
            return self.descriptor.name

    def __init__(self, transport):
        # metadata
        self.call_start = time()
        """The time the rpc operation was initiated in seconds-since-epoch
        format.

        Useful for benchmarking purposes."""

        self.call_end = None
        """The time the rpc operation was completed in seconds-since-epoch
        format.

        Useful for benchmarking purposes."""

        self.app = transport.app
        """The parent application."""

        self.udc = None
        """The user defined context. Use it to your liking."""

        self.transport = TransportContext(transport)
        """The transport-specific context. Transport implementors can use this
        to their liking."""

        self.protocol = ProtocolContext(transport)
        """The protocol-specific context. Protocol implementors can use this
        to their liking."""

        self.event = EventContext()
        """Event-specific context. Use this as you want, preferably only in
        events, as you'd probably want to separate the event data from the
        method data."""

        self.aux = None
        """Auxiliary-method specific context. You can use this to share data
        between auxiliary sessions. This is not set in primary contexts.
        """

        self.method_request_string = None
        """This is used to decide which native method to call. It is set by
        the protocol classes."""

        self.__descriptor = None

        # This is set based on the value of the descriptor.
        self.service_class = None
        """The service definition class the method belongs to."""

        #
        # Input
        #

        # stream
        self.in_string = None
        """Incoming bytestream as a sequence of ``str`` or ``bytes`` instances."""

        # parsed
        self.in_document = None
        """Incoming document, what you get when you parse the incoming stream."""
        self.in_header_doc = None
        """Incoming header document of the request."""
        self.in_body_doc = None
        """Incoming body document of the request."""

        # native
        self.in_error = None
        """Native python error object. If this is set, either there was a
        parsing error or the incoming document was representing an exception.
        """
        self.in_header = None
        """Deserialized incoming header -- a native object."""
        self.in_object = None
        """In the request (i.e. server) case, this contains the function
        argument sequence for the function in the service definition class.
        In the response (i.e. client) case, this contains the object returned
        by the remote procedure call.

        It's always a sequence of objects:
            * ``[None]`` when the function has no output (client)/input (server)
              types.
            * A single-element list that wraps the return value when the
              function has one return type defined,
            * A tuple of return values in case of the function having more than
              one return value.

        The order of the argument sequence is in line with
        ``self.descriptor.in_message._type_info.keys()``.
        """

        #
        # Output
        #

        # native
        self.out_object = None
        """In the response (i.e. server) case, this contains the native python
        object(s) returned by the function in the service definition class.
        In the request (i.e. client) case, this contains the function arguments
        passed to the function call wrapper.

        It's always a sequence of objects:
            * ``[None]`` when the function has no output (server)/input (client)
              types.
            * A single-element list that wraps the return value when the
              function has one return type defined,
            * A tuple of return values in case of the function having more than
              one return value.

        The order of the argument sequence is in line with
        ``self.descriptor.out_message._type_info.keys()``.
        """
        self.out_header = None
        """Native python object set by the function in the service definition
        class."""
        self.out_error = None
        """Native exception thrown by the function in the service definition
        class."""

        # parsed
        self.out_body_doc = None
        """Serialized body object."""
        self.out_header_doc = None
        """Serialized header object."""
        self.out_document = None
        """out_body_doc and out_header_doc wrapped in the outgoing envelope"""

        # stream
        self.out_string = None
        """Outgoing bytestream (i.e. a sequence of strings)"""

        self.function = None
        """The callable of the user code."""

        self.locale = None
        """The locale the request will use when needed for things like date
        formatting, html rendering and such."""

        self.frozen = True
        """When this is set, no new attribute can be added to this class
        instance. This is mostly for internal use.
        """

        self.app.event_manager.fire_event("method_context_constructed", self)

    def get_descriptor(self):
        return self.__descriptor

    def set_descriptor(self, descriptor):
        self.__descriptor = descriptor
        self.function = descriptor.function

    descriptor = property(get_descriptor, set_descriptor)
    """The :class:``MethodDescriptor`` object representing the current method.
    It is only set when the incoming request was successfully mapped to a method
    in the public interface. The contents of this property should not be changed
    by the user code.
    """

    def __setattr__(self, k, v):
        if self.frozen == False or k in self.__dict__ or k == 'descriptor':
            object.__setattr__(self, k, v)
        else:
            raise ValueError("use the udc member for storing arbitrary data "
                             "in the method context")

    def __repr__(self):
        retval = deque()
        for k, v in self.__dict__.items():
            if isinstance(v, dict):
                ret = deque(['{'])
                items = sorted(v.items())
                for k2, v2 in items:
                    ret.append('\t\t%r: %r,' % (k2, v2))
                ret.append('\t}')
                ret = '\n'.join(ret)
                retval.append("\n\t%s=%s" % (k, ret))
            else:
                retval.append("\n\t%s=%r" % (k, v))

        retval.append('\n)')

        return ''.join((self.__class__.__name__, '(', ', '.join(retval), ')'))

    def __del__(self):
        self.call_end = time()
        self.app.event_manager.fire_event("method_context_destroyed", self)


class MethodDescriptor(object):
    '''This class represents the method signature of an exposed service. It is
    produced by the :func:`spyne.decorator.srpc` decorator.
    '''

    def __init__(self, function, in_message, out_message, doc,
                 is_callback=False, is_async=False, mtom=False, in_header=None,
                 out_header=None, faults=None,
                 port_type=None, no_ctx=False, udp=None, class_key=None,
                 aux=None, patterns=None, body_style=None):

        self.__real_function = function
        """The original callable for the user code."""

        self.reset_function()

        self.in_message = in_message
        """A :class:`spyne.model.complex.ComplexModel` subclass that defines the
        input signature of the user function and that was automatically
        generated by the ``@srpc`` decorator."""

        self.out_message = out_message
        """A :class:`spyne.model.complex.ComplexModel` subclass that defines the
        output signature of the user function and that was automatically
        generated by the ``@srpc`` decorator."""

        self.doc = doc
        """The function docstring."""

        # these are not working, so they are not documented.
        self.is_callback = is_callback
        self.is_async = is_async
        self.mtom = mtom
        #"""Flag to indicate whether to use MTOM transport with SOAP."""
        self.port_type = port_type
        #"""The portType this function belongs to."""

        self.in_header = in_header
        """An iterable of :class:`spyne.model.complex.ComplexModel`
        subclasses to denote the types of header objects that this method can
        accept."""

        self.out_header = out_header
        """An iterable of :class:`spyne.model.complex.ComplexModel`
        subclasses to denote the types of header objects that this method can
        emit along with its return value."""

        self.faults = faults
        """An iterable of :class:`spyne.model.fault.Fault` subclasses to denote
        the types of exceptions that this method can throw."""

        self.no_ctx = no_ctx
        """no_ctx: Boolean flag to denote whether the user code gets an
        implicit :class:`spyne.MethodContext` instance as first argument."""

        self.udp = udp
        """Short for "User Defined Properties", this is just an arbitrary python
        object set by the user to pass arbitrary metadata via the ``@srpc``
        decorator."""

        self.class_key = class_key
        """ The identifier of this method in its parent
        :class:`spyne.service.ServiceBase` subclass."""

        self.aux = aux
        """Value to indicate what kind of auxiliary method this is. (None means
        primary)

        Primary methods block the request as long as they're running. Their
        return values are returned to the client. Auxiliary ones execute
        asyncronously after the primary method returns, and their return values
        are ignored by the rpc layer.
        """

        self.patterns = patterns
        """This list stores patterns which will match this callable using
        various elements of the request protocol.

        Currently, the only object supported here is the
        :class:`spyne.protocol.http.HttpPattern` object.
        """

        self.body_style = body_style
        """One of (BODY_STYLE_EMPTY, BODY_STYLE_BARE, BODY_STYLE_WRAPPED)."""

    @property
    def name(self):
        """The public name of the function. Equals to the type_name of the
        in_message."""
        return self.in_message.get_type_name()

    @property
    def key(self):
        """The function identifier in '{namespace}name' form."""

        assert not (self.in_message.get_namespace() is DEFAULT_NS)

        return '{%s}%s' % (
            self.in_message.get_namespace(), self.in_message.get_type_name())

    def reset_function(self, val=None):
        if val != None:
            self.__real_function = val
        self.function = self.__real_function


class EventManager(object):
    """Spyne supports a simple event system that can be used to have repetitive
    boiler plate code that has to run for every method call nicely tucked away
    in one or more event handlers. The popular use-cases include things like
    database transaction management, logging and measuring performance.

    Various Spyne components support firing events at various stages during the
    processing of the request, which are documented in the relevant classes.

    The classes that support events are:
        * :class:`spyne.application.Application`
        * :class:`spyne.service.ServiceBase`
        * :class:`spyne.protocol._base.ProtocolBase`
        * :class:`spyne.server.wsgi.WsgiApplication`

    The events are stored in an ordered set. This means that the events are ran
    in the order they were added and adding a handler twice does not cause it to
    run twice.
    """

    def __init__(self, parent, handlers={}):
        self.parent = parent
        self.handlers = dict(handlers)

    def add_listener(self, event_name, handler):
        """Register a handler for the given event name.

        :param event_name: The event identifier, indicated by the documentation.
                           Usually, this is a string.
        :param handler: A static python function that receives a single
                        MethodContext argument.
        """

        handlers = self.handlers.get(event_name, oset())
        handlers.add(handler)
        self.handlers[event_name] = handlers

    def fire_event(self, event_name, ctx):
        """Run all the handlers for a given event name.

        :param event_name: The event identifier, indicated by the documentation.
                           Usually, this is a string.
        :param handler: The method context. Event-related data is conventionally
                        stored in ctx.event attribute.
        """

        handlers = self.handlers.get(event_name, oset())
        for handler in handlers:
            handler(ctx)
