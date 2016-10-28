
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

import gc, logging
logger = logging.getLogger('spyne')

from time import time
from copy import copy
from collections import deque, namedtuple, defaultdict

from spyne.const import MIN_GC_INTERVAL
from spyne.const.xml_ns import DEFAULT_NS

from spyne.util.oset import oset

class BODY_STYLE_WRAPPED: pass
class BODY_STYLE_EMPTY: pass
class BODY_STYLE_BARE: pass
class BODY_STYLE_OUT_BARE: pass


_LAST_GC_RUN = 0.0


# When spyne.server.twisted gets imported, this type gets a static method named
# `from_twisted_address`. Dark magic.
Address = namedtuple("Address", ["type", "host", "port"])


class _add_address_types():
    Address.TCP4 = 'TCP4'
    Address.TCP6 = 'TCP6'
    Address.UDP4 = 'UDP4'
    Address.UDP6 = 'UDP6'
    def address_str(self):
        return ":".join((self.type, self.host, str(self.port)))
    Address.__str__ = address_str


class AuxMethodContext(object):
    """Generic object that holds information specific to auxiliary methods"""
    def __init__(self, parent, error):
        self.parent = parent
        """Primary context that this method was bound to."""

        self.error = error
        """Error from primary context (if any)."""


class TransportContext(object):
    """Generic object that holds transport-specific context information"""
    def __init__(self, parent, transport, type=None):
        self.parent = parent
        """The MethodContext this object belongs to"""

        self.itself = transport
        """The transport itself; i.e. a ServerBase instance."""

        self.type = type
        """The protocol the transport uses."""

        self.app = transport.app

        self.request_encoding = None
        """General purpose variable to hold the string identifier of a request
        encoding. It's nowadays usually 'utf-8', especially with http data"""

        self.remote_addr = None
        """The address of the other end of the connection."""

        self.sessid = ''
        """The session id."""


class ProtocolContext(object):
    """Generic object that holds protocol-specific context information"""
    def __init__(self, parent, transport, type=None):
        self.parent = parent
        """The MethodContext this object belongs to"""

        self.itself = transport
        """The protocol itself as passed to the `Application` init. This is a
        `ProtocolBase` instance."""

        self.type = type
        """The protocol the transport uses."""

        self._subctx = defaultdict(
                               lambda: self.__class__(parent, transport, type))

    def __getitem__(self, item):
        return self._subctx[item]


class EventContext(object):
    """Generic object that holds event-specific context information"""
    def __init__(self, parent, event_id=None):
        self.parent = parent
        self.event_id = event_id


class MethodContext(object):
    """The base class for all RPC Contexts. Holds all information about the
    current state of execution of a remote procedure call.
    """

    SERVER = type("SERVER", (object,), {})
    CLIENT = type("CLIENT", (object,), {})

    frozen = False

    def copy(self):
        retval = copy(self)

        if retval.transport is not None:
            retval.transport.parent = retval
        if retval.inprot_ctx is not None:
            retval.inprot_ctx.parent = retval
        if retval.outprot_ctx is not None:
            retval.outprot_ctx.parent = retval
        if retval.event is not None:
            retval.event.parent = retval
        if retval.aux is not None:
            retval.aux.parent = retval

        return retval

    @property
    def method_name(self):
        """The public name of the method the ``method_request_string`` was
        matched to.
        """

        if self.descriptor is None:
            return None
        else:
            return self.descriptor.name

    def __init__(self, transport, way):
        # metadata
        self.call_start = time()
        """The time the rpc operation was initiated in seconds-since-epoch
        format.

        Useful for benchmarking purposes."""

        self.call_end = None
        """The time the rpc operation was completed in seconds-since-epoch
        format.

        Useful for benchmarking purposes."""

        self.is_closed = False

        self.app = transport.app
        """The parent application."""

        self.udc = None
        """The user defined context. Use it to your liking."""

        self.transport = TransportContext(self, transport)
        """The transport-specific context. Transport implementors can use this
        to their liking."""

        self.outprot_ctx = None
        """The output-protocol-specific context. Protocol implementors can use
        this to their liking."""

        if self.app.out_protocol is not None:
            self.outprot_ctx = self.app.out_protocol.get_context(self, transport)

        self.inprot_ctx = None
        """The input-protocol-specific context. Protocol implementors can use
        this to their liking."""

        if self.app.in_protocol is not None:
            self.inprot_ctx = self.app.in_protocol.get_context(self, transport)

        self.protocol = None
        """The protocol-specific context. This points to the in_protocol when an
        incoming message is being processed and out_protocol when an outgoing
        message is being processed."""

        if way is MethodContext.SERVER:
            self.protocol = self.inprot_ctx
        elif way is MethodContext.CLIENT:
            self.protocol = self.outprot_ctx
        else:
            raise ValueError(way)

        self.event = EventContext(self)
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

        self.files = []
        """List of stuff to be closed when closing this context. Anything that
        has a close() callable can go in."""

        self.__descriptor = None

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
        """The pull interface to the outgoing bytestream. It's a sequence of
        strings (which could also be a generator)."""

        self.out_stream = None
        """The push interface to the outgoing bytestream. It's a file-like
        object."""

        #self.out_stream = None
        #"""The push interface to the outgoing bytestream. It's a file-like
        #object."""

        self.function = None
        """The callable of the user code."""

        self.locale = None
        """The locale the request will use when needed for things like date
        formatting, html rendering and such."""

        self.in_protocol = transport.app.in_protocol
        """The protocol that will be used to (de)serialize incoming input"""

        self.out_protocol = transport.app.out_protocol
        """The protocol that will be used to (de)serialize outgoing input"""

        self.frozen = True
        """When this is set, no new attribute can be added to this class
        instance. This is mostly for internal use.
        """

        self.app.event_manager.fire_event("method_context_created", self)

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

    # Deprecated. Use self.descriptor.service_class.
    @property
    def service_class(self):
        if self.descriptor is not None:
            return self.descriptor.service_class

    def __setattr__(self, k, v):
        if not self.frozen or k in self.__dict__ or k in \
                                                 ('descriptor', 'out_protocol'):
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

    def close(self):
        global _LAST_GC_RUN

        self.call_end = time()
        self.app.event_manager.fire_event("method_context_closed", self)
        for f in self.files:
            f.close()

        self.is_closed = True

        # this is important to have file descriptors returned in a timely manner
        t = time()
        if (t - _LAST_GC_RUN) > MIN_GC_INTERVAL:
            gc.collect()

            dt = (time() - t)
            _LAST_GC_RUN = t

            logger.debug("gc.collect() took around %dms.", round(dt, 2) * 1000)

    def set_out_protocol(self, what):
        self._out_protocol = what

    def get_out_protocol(self):
        return self._out_protocol

    out_protocol = property(get_out_protocol, set_out_protocol)


class MethodDescriptor(object):
    """This class represents the method signature of an exposed service. It is
    produced by the :func:`spyne.decorator.srpc` decorator.
    """

    def __init__(self, function, in_message, out_message, doc,
                 is_callback=False, is_async=False, mtom=False, in_header=None,
                 out_header=None, faults=None,
                 port_type=None, no_ctx=False, udp=None, class_key=None,
                 aux=None, patterns=None, body_style=None, args=None,
                 operation_name=None, no_self=None, translations=None, when=None,
                 in_message_name_override=True, out_message_name_override=True,
                 service_class=None, href=None):

        self.__real_function = function
        """The original callable for the user code."""

        self.reset_function()

        self.operation_name = operation_name
        """The base name of an operation without the request suffix, as
        generated by the ``@srpc`` decorator."""

        self.in_message = in_message
        """A :class:`spyne.model.complex.ComplexModel` subclass that defines the
        input signature of the user function and that was automatically
        generated by the ``@srpc`` decorator."""

        self.name = None
        """The public name of the function. Equals to the type_name of the
        in_message."""

        if body_style is BODY_STYLE_BARE:
            self.name = in_message.Attributes.sub_name

        if self.name is None:
            self.name = self.in_message.get_type_name()

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

        self.args = args
        """A sequence of the names of the exposed arguments, or None."""

        # FIXME: docstring yo.
        self.no_self = no_self
        """FIXME: docstring yo."""

        self.service_class = service_class
        """The ServiceBase subclass the method belongs to, if there's any."""

        self.parent_class = None
        """The ComplexModel subclass the method belongs to. Only set for @mrpc
        methods."""

        # HATEOAS Stuff
        self.translations = translations
        """None or a dict of locale-translation pairs."""

        self.href = href
        """None or a dict of locale-translation pairs."""

        self.when = when
        """None or a callable that takes the object instance and returns a
        boolean value. If true, the object can process that action.
        """

        # Method Customizations
        self.in_message_name_override = in_message_name_override
        """When False, no mangling of in message name will be performed by later
        stages of the interface generation. Naturally, it will be up to you to
        resolve name clashes."""

        self.out_message_name_override = out_message_name_override
        """When False, no mangling of out message name will be performed by
        later stages of the interface generation. Naturally, it will be up to
        you to resolve name clashes."""

    def translate(self, locale, default):
        """
        :param locale: locale string
        :param default: default string if no translation found
        :returns: translated string
        """

        if locale is None:
            locale = 'en_US'
        if self.translations is not None:
            return self.translations.get(locale, default)
        return default

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
    boilerplate code that has to run for every method call nicely tucked away
    in one or more event handlers. The popular use-cases include things like
    database transaction management, logging and measuring performance.

    Various Spyne components support firing events at various stages during the
    processing of a request, which are documented in the relevant classes.

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

    def fire_event(self, event_name, ctx, *args, **kwargs):
        """Run all the handlers for a given event name.

        :param event_name: The event identifier, indicated by the documentation.
                           Usually, this is a string.
        :param ctx: The method context. Event-related data is conventionally
                        stored in ctx.event attribute.
        """

        handlers = self.handlers.get(event_name, oset())
        for handler in handlers:
            handler(ctx, *args, **kwargs)


class FakeContext(object):
    def __init__(self, app=None, descriptor=None,
            in_object=None, in_error=None, in_document=None, in_string=None,
            out_object=None, out_error=None, out_document=None, out_string=None,
            in_protocol=None, out_protocol=None):
        self.app = app
        self.descriptor = descriptor
        self.in_object = in_object
        self.in_error = in_error
        self.in_document = in_document
        self.in_string = in_string
        self.out_error = out_error
        self.out_object = out_object
        self.out_document = out_document
        self.out_string = out_string
        self.in_protocol = in_protocol
        self.out_protocol = out_protocol

        if self.in_protocol is not None:
            self.inprot_ctx = self.in_protocol.get_context(self, None)
        else:
            self.inprot_ctx = type("ProtocolContext", (object,), {})()

        from spyne.protocol.html._base import HtmlClothProtocolContext

        if self.out_protocol is not None:
            self.outprot_ctx = self.out_protocol.get_context(self, None)
        else:
            # The outprot_ctx here must contain properties from ALL tested
            # protocols' context objects. That's why we use
            # HtmlClothProtocolContext here, it's just the one with most
            # attributes.
            self.outprot_ctx = HtmlClothProtocolContext(self, None)

        self.protocol = self.outprot_ctx
        self.transport = type("ProtocolContext", (object,), {})()
