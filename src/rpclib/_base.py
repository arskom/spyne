
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

from collections import deque

class MethodContext(object):
    frozen = False

    def __init__(self, app):
        self.app = app

        self.udc = None # the user defined context. use it to your liking.

        self.method_name = None
        # these are set based on the value of the method_name.
        self.service_class = None # the class the method belongs to
        self.descriptor = None    # its descriptor

        self.in_string = None     # incoming bytestream (can be any kind of
                                  #     iterable that contains strings)
        self.in_document = None   # parsed document
        self.in_error = None      # native python error object (probably a
                                  #     child of Exception)
        self.in_header_doc = None # incoming header document of the request.
        self.in_body_doc = None   # incoming body document of the request.
        self.in_header = None     # native incoming header

        # in the request (i.e. server) case, this contains the function
        # arguments for the function in the service definition class.
        # in the response (i.e. client) case, this contains the object returned
        # by the remote procedure call.
        self.in_object = None

        # in the response (i.e. server) case, this is the native python object
        # returned by the function in the service definition class.
        # in the response (i.e. client) case, this contains the function
        # arguments passed to the function call wrapper.
        self.out_object = None

        self.out_header = None     # native python object set by the function in
                                   # the service definition class
        self.out_error = None      # native exception thrown by the function in
                                   # the service definition class
        self.out_body_doc = None   # serialized body object
        self.out_header_doc = None # serialized header object
        self.out_document = None   # body and header wrapped in the outgoing
                                   # envelope
        self.out_string = None     # outgoing bytestream (can be any kind of
                                   # iterable that contains strings)

        self.frozen = True # when this is set, no new attribute can be added to
                           # the class instance.

    def __setattr__(self, k, v):
        if self.frozen == False or k in self.__dict__:
            object.__setattr__(self, k,v)
        else:
            raise ValueError("use the udc member for storing arbitrary data in "
                             "the method context")

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

class MethodDescriptor(object):
    '''This class represents the method signature of a soap method,
    and is returned by the rpc decorator.
    '''

    def __init__(self, name, public_name, in_message, out_message, doc,
                 is_callback=False, is_async=False, mtom=False, in_header=None,
                 out_header=None, faults=(),
                 port_type=None, no_ctx=False,
                ):

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
        self.faults = faults
        self.port_type = port_type
        self.no_ctx = no_ctx

class EventManager(object):
    def __init__(self, supported_events):
        self.__supported_events = set(supported_events)
        self.__event_handlers = {}

    def add_listener(self, event_name, handler):
        assert event_name in self.__supported_events

        handlers = self.__event_handlers.get(event_name, [])
        handlers.add(handler)
        self.__event_handlers[event_name] = handlers

    def fire_event(self, event_name, ctx):
        assert event_name in self.__supported_events

        handlers = self.__event_handlers.get(event_name, [])
        for handler in handlers:
            handler(ctx)
