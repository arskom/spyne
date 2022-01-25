
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
from collections import deque, defaultdict

from spyne import const


_LAST_GC_RUN = 0.0


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

    def get_peer(self):
        """Returns None when not applicable, otherwise returns
        :class:`spyne.Address`"""

        return None


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
    TransportContext = TransportContext

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

    def fire_event(self, event, *args, **kwargs):
        self.app.event_manager.fire_event(event, self, *args, **kwargs)

        desc = self.descriptor
        if desc is not None:
            for evmgr in desc.event_managers:
                evmgr.fire_event(event, self, *args, **kwargs)

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
        """`True` means response is fully sent and request finalized."""

        self.app = transport.app
        """The parent application."""

        self.udc = None
        """The user defined context. Use it to your liking."""

        self.transport = None
        """The transport-specific context. Transport implementors can use this
        to their liking."""

        if self.TransportContext is not None:
            self.transport = self.TransportContext(self, transport)

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

        self.active = False
        """Transports may choose to delay incoming requests. When a context
        is queued but waiting, this is False."""

        self.__descriptor = None

        #
        # Input
        #

        # stream
        self.in_string = None
        """Incoming bytestream as a sequence of ``str`` or ``bytes``
        instances."""

        # parsed
        self.in_document = None
        """Incoming document, what you get when you parse the incoming
        stream."""
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

        self.function = None
        """The callable of the user code."""

        self.locale = None
        """The locale the request will use when needed for things like date
        formatting, html rendering and such."""

        self._in_protocol = transport.app.in_protocol
        """The protocol that will be used to (de)serialize incoming input"""

        self._out_protocol = transport.app.out_protocol
        """The protocol that will be used to (de)serialize outgoing input"""

        self.pusher_stack = []
        """Last one is the current PushBase instance writing to the stream."""

        self.frozen = True
        """When this is set, no new attribute can be added to this class
        instance. This is mostly for internal use.
        """

        self.fire_event("method_context_created")

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

    # FIXME: Deprecated. Use self.descriptor.service_class.
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

                for k2, v2 in sorted(v.items()):
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
        if (t - _LAST_GC_RUN) > const.MIN_GC_INTERVAL:
            gc.collect()

            dt = (time() - t)
            _LAST_GC_RUN = t

            logger.debug("gc.collect() took around %dms.", round(dt, 2) * 1000)

    def set_out_protocol(self, what):
        self._out_protocol = what
        if self._out_protocol.app is None:
            self._out_protocol.set_app(self.app)

    def get_out_protocol(self):
        return self._out_protocol

    out_protocol = property(get_out_protocol, set_out_protocol)

    def set_in_protocol(self, what):
        self._in_protocol = what
        self._in_protocol.app = self.app

    def get_in_protocol(self):
        return self._in_protocol

    in_protocol = property(get_in_protocol, set_in_protocol)


class FakeContext(object):
    def __init__(self, app=None, descriptor=None, in_header=None,
            in_object=None, in_error=None, in_document=None, in_string=None,
            out_object=None, out_error=None, out_document=None, out_string=None,
            in_protocol=None, out_protocol=None):
        self.app = app
        self.descriptor = descriptor
        self.in_header = in_header
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
