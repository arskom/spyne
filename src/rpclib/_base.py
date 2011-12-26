
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

from time import time

from collections import deque

from rpclib.const.xml_ns import DEFAULT_NS
from rpclib.util.oset import oset

class TransportContext(object):
    """Generic object that holds transport-specific context information"""
    def __init__(self, type=None):
        self.type=type

class EventContext(object):
    """Generic object that holds event-specific context information"""
    def __init__(self, event_id=None):
        self.event_id=event_id

class MethodContext(object):
    """The base class for all RPC Contexts. Holds crucial information about the
    lifetime of a document.
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

    def __init__(self, app):
        # metadata
        self.call_start = time()
        """The time the rpc operation was initiated in seconds-since-epoch
        format.

        Useful for benchmarking purposes."""

        self.call_end = None
        """The time the rpc operation was completed in seconds-since-epoch
        format.

        Useful for benchmarking purposes."""

        self.app = app
        """The parent application."""

        self.udc = None
        """The user defined context. Use it to your liking."""

        self.transport = TransportContext()
        """The transport-specific context. Transport implementors can use this
        to their liking."""

        self.event = EventContext()
        """Event-specific context. Use this as you want, preferably only in
        events, as you'd probably want to separate the event data from the
        method data."""

        self.method_request_string = None
        """This is used as a basis on deciding which native method to call."""

        self.descriptor = None
        """The MethodDescriptor object representing the current method."""

        #
        # The following are set based on the value of the descriptor.
        #
        self.service_class = None
        """The service definition class the method belongs to."""

        #
        # Input
        #

        # stream
        self.in_string = None
        """Incoming bytestream (i.e. an iterable of strings)"""

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
        """Deserialzed incoming header -- a native object."""
        self.in_object = None
        """In the request (i.e. server) case, this contains the function
        arguments for the function in the service definition class.
        In the response (i.e. client) case, this contains the object returned
        by the remote procedure call.

        It's always an iterable of objects:
            * [None] when the function has no output (client)/input (server)
              types.
            * A single-element list that wraps the return value when the
              function has one return type defined,
            * Left untouched even when the function has more than one return
              values.

        The objects never contain the instances but lists of values. The order
        is in line with ``self.descriptor.in_class._type_info.keys()``.
        """

        #
        # Output
        #

        # native
        self.out_object = None
        """In the request (i.e. server) case, this is the native python object
        returned by the function in the service definition class.
        In the response (i.e. client) case, this contains the function arguments
        passed to the function call wrapper.

        It's always an iterable of objects:
            * [None] when the function has no output (server)/input (client)
              types.
            * A single-element list that wraps the return value when the
              function has one return type defined,
            * Left untouched even when the function has more than one return
              values.

        The objects never contain the instances but lists of values. The order
        is in line with ``self.descriptor.out_class._type_info.keys()``.
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
        """Outgoing bytestream (i.e. an iterable of strings)"""

        self.frozen = True
        """When this is set, no new attribute can be added to this class
        instance. This is mostly for internal use.
        """

        self.app.event_manager.fire_event("method_context_constructed", self)

    def __setattr__(self, k, v):
        if self.frozen == False or k in self.__dict__:
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
    '''This class represents the method signature of a soap method,
    and is returned by the rpc decorator.
    '''

    def __init__(self, function, in_message, out_message, doc,
                 is_callback=False, is_async=False, mtom=False, in_header=None,
                 out_header=None, faults=None,
                 port_type=None, no_ctx=False, udp=None, class_key=None):

        self.__real_function = function
        self.reset_function()

        """The original function object to be called when the method is remotely
        invoked."""

        self.in_message = in_message
        """Automatically generated complex object based on incoming arguments to
        the function."""

        self.out_message = out_message
        """Automatically generated complex object based on the return type of
        the function."""

        self.doc = doc
        """The function docstring."""

        self.is_callback = is_callback
        self.is_async = is_async

        self.mtom = mtom
        """Flag to indicate whether to use MTOM transport with SOAP."""

        self.in_header = in_header
        """The incoming header object this function could accept."""

        self.out_header = out_header
        """The outgoing header object this function could send."""

        self.faults = faults
        """The exceptions that this function can throw."""

        self.port_type = port_type
        """The portType this function belongs to."""

        self.no_ctx = no_ctx
        """Whether the function receives the method context as the first
        argument implicitly."""

        self.udp = udp
        """Short for "User-Defined Properties", it's your own playground. You
        can use it to store custom metadata about the method."""

        self.class_key = class_key
        """The name the function is accessible from in the class."""

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
    """The event manager for all rpclib events. The events are stored in an
    ordered set -- so the events are ran in the order they were added and
    adding a handler twice does not cause it to run twice.
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
