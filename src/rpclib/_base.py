
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
    def __init__(self, app):
        self.app = app

        self.service_class = None

        self.in_error = None
        self.in_header = None
        self.in_header_doc = None
        self.in_body_doc = None

        self.out_error = None
        self.out_header = None
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

class MethodDescriptor(object):
    '''This class represents the method signature of a soap method,
    and is returned by the rpc decorator.
    '''

    def __init__(self, name, public_name, in_message, out_message, doc,
                 is_callback=False, is_async=False, mtom=False, in_header=None,
                 out_header=None, faults=(),
                 port_type=None, no_ctx=False
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
