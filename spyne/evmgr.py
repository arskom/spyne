
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


from spyne.util.oset import oset


class EventManager(object):
    """Spyne supports a simple event system that can be used to have repetitive
    boilerplate code that has to run for every method call nicely tucked away
    in one or more event handlers. The popular use-cases include things like
    database transaction management, logging and performance measurements.

    Various Spyne components support firing events at various stages during the
    request handling process, which are documented in the relevant classes.

    The events are stored in an ordered set. This means that the events are ran
    in the order they were added and adding a handler twice does not cause it to
    run twice.
    """

    def __init__(self, parent, handlers={}):
        """Initializer for the ``EventManager`` instance.

        :param parent: The owner of this event manager. As of Spyne 2.13, event
        managers can be owned by multiple objects, in which case this property
        will be none.

        :param handlers: A dict of event name (string)/callable pairs. The dict
        shallow-copied to the ``EventManager`` instance.
        """

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

    def del_listener(self, event_name, handler=None):
        if handler is None:
            del self.handlers[event_name]
        else:
            self.handlers[event_name].remove(handler)


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
