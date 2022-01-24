
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
logger_client = logging.getLogger('.'.join([__name__, 'client']))
logger_server = logging.getLogger('.'.join([__name__, 'server']))

from pprint import pformat

from spyne import BODY_STYLE_EMPTY, BODY_STYLE_BARE, BODY_STYLE_WRAPPED, \
    EventManager
from spyne.error import Fault, Redirect, RespawnError, InvalidRequestError
from spyne.interface import Interface, InterfaceDocuments
from spyne.util import six
from spyne.util.appreg import register_application


class MethodAlreadyExistsError(Exception):
    def __init__(self, what):
        super(MethodAlreadyExistsError, self) \
                                 .__init__("Method key %r already exists", what)


def get_fault_string_from_exception(e):
    # haha.
    return "Internal Error"


def return_traceback_in_unhandled_exceptions():
    """Call this function first thing in your main function to return original
    python errors to your clients in case of unhandled exceptions.
    """

    global get_fault_string_from_exception

    import traceback
    def _get_fault_string_from_exception(e):
        return traceback.format_exc()
    get_fault_string_from_exception = _get_fault_string_from_exception


class Application(object):
    """The Application class is the glue between one or more service
    definitions, input and output protocols.

    :param services:     An iterable of Service subclasses that defines
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
    :param config:       An arbitrary python object to store random global data.
    :param classes:      An iterable of Spyne classes that don't appear in any
                         of the service definitions but need to appear in the
                         interface documents nevertheless.
    :param documents_container:
                         A class that implements the InterfaceDocuments
                         interface

    Supported events:
        * ``method_call``:
            Called right before the service method is executed

        * ``method_return_object``:
            Called right after the service method is executed

        * ``method_exception_object``:
            Called when an exception occurred in a service method, before the
            exception is serialized.

        * ``method_context_created``:
            Called from the constructor of the MethodContext instance.

        * ``method_context_closed``:
            Called from the ``close()`` function of the MethodContext instance,
            which in turn is called by the transport when the response is fully
            sent to the client (or in the client case, the response is fully
            received from server).
    """

    transport = None

    def __init__(self, services, tns, name=None,
                 in_protocol=None, out_protocol=None,
                 config=None, classes=(),
                 documents_container=InterfaceDocuments):
        self.services = tuple(services)
        self.tns = tns
        self.name = name
        self.config = config
        self.classes = classes

        if self.name is None:
            self.name = self.__class__.__name__.split('.')[-1]

        logger.info("Initializing application {%s}%s...", self.tns, self.name)

        self.event_manager = EventManager(self)
        self.error_handler = None

        self.in_protocol = in_protocol
        self.out_protocol = out_protocol

        if self.in_protocol is None:
            from spyne.protocol import ProtocolBase
            self.in_protocol = ProtocolBase()

        if self.out_protocol is None:
            from spyne.protocol import ProtocolBase
            self.out_protocol = ProtocolBase()

        self.check_unique_method_keys()  # is this really necessary nowadays?

        # this needs to be after protocol assignments to give _static_when
        # functions as much info as possible about the application
        self.interface = Interface(self, documents_container=documents_container)

        # set_app needs to be after interface init because the protocols use it.
        self.in_protocol.set_app(self)
        # FIXME: this normally is another parameter to set_app but it's kept
        # separate for backwards compatibility reasons.
        self.in_protocol.message = self.in_protocol.REQUEST

        self.out_protocol.set_app(self)
        # FIXME: this normally is another parameter to set_app but it's kept
        # separate for backwards compatibility reasons.
        self.out_protocol.message = self.out_protocol.RESPONSE

        register_application(self)

    def process_request(self, ctx):
        """Takes a MethodContext instance. Returns the response to the request
        as a native python object. If the function throws an exception, it
        returns None and sets the exception object to ctx.out_error.

        Overriding this method would break event management. So this is not
        meant to be overridden unless you know what you're doing.
        """

        try:
            ctx.fire_event('method_call')

            # in object is always a sequence of incoming values. We need to fix
            # that for bare mode.
            if ctx.descriptor.body_style is BODY_STYLE_BARE:
                ctx.in_object = [ctx.in_object]
            elif ctx.descriptor.body_style is BODY_STYLE_EMPTY:
                ctx.in_object = []

            # call user method
            ctx.out_object = self.call_wrapper(ctx)

            # out object is always a sequence of return values. see
            # MethodContext docstrings for more info
            if ctx.descriptor.body_style is not BODY_STYLE_WRAPPED or \
                                len(ctx.descriptor.out_message._type_info) <= 1:
                # if it's not a wrapped method, OR there's just one return type
                # we wrap it ourselves
                ctx.out_object = [ctx.out_object]

            # Now that the processing is switched to the outgoing message,
            # point ctx.protocol to ctx.out_protocol
            ctx.protocol = ctx.outprot_ctx

            ctx.fire_event('method_return_object')

        except Redirect as e:
            try:
                e.do_redirect()

                ctx.out_object = [None]

                # Now that the processing is switched to the outgoing message,
                # point ctx.protocol to ctx.out_protocol
                ctx.protocol = ctx.outprot_ctx

                ctx.fire_event('method_redirect')

            except Exception as e:
                logger_server.exception(e)
                ctx.out_error = Fault('Server',
                                             get_fault_string_from_exception(e))

                ctx.fire_event('method_redirect_exception')

        except Fault as e:
            if e.faultcode == 'Client' or e.faultcode.startswith('Client.'):
                logger_client.exception(e)
            else:
                logger.exception(e)

            ctx.out_error = e

            ctx.fire_event('method_exception_object')

        # we don't catch BaseException because we actually don't want to catch
        # "system-exiting" exceptions. See:
        # https://docs.python.org/2/library/exceptions.html#exceptions.Exception
        except Exception as e:
            logger_server.critical(e, **{'exc_info': 1})

            ctx.out_error = Fault('Server', get_fault_string_from_exception(e))

            ctx.fire_event('method_exception_object')

    def call_wrapper(self, ctx):
        """This method calls the call_wrapper method in the service definition.
        This can be overridden to make an application-wide custom exception
        management.
        """

        # no function
        if ctx.function is None:
            logger.debug("Skipping user code call as ctx.function is None.")
            return None

        # @rpc inside service class
        if ctx.descriptor.no_self:
            assert ctx.descriptor.service_class is not None
            return ctx.descriptor.service_class.call_wrapper(ctx)

        # from here on it's @mrpc in a (parent) class
        cls = ctx.descriptor.parent_class
        if cls.__orig__ is not None:
            cls = cls.__orig__

        filters = {}
        inst = cls.__respawn__(ctx, filters)
        if inst is None:
            raise RespawnError('{%s}%s with params %r' %
                            (cls.get_namespace(), cls.get_type_name(), filters))

        in_cls = ctx.descriptor.in_message

        args = tuple(ctx.in_object)
        if args is None:
            args = ()

        elif ctx.descriptor.body_style is BODY_STYLE_WRAPPED and \
                                len(in_cls.get_flat_type_info(in_cls)) <= 1:
            args = ()

        else:
            args = args[1:]

        # check whether this is a valid request according to the prerequisite
        # function (the callable that was passed in the _when argument to @mrpc)
        if ctx.descriptor.when is not None:
            if not ctx.descriptor.when(inst, ctx):
                raise InvalidRequestError("Invalid object state for request")

        if ctx.descriptor.no_ctx:
            args = (inst,) + args
        else:
            args = (inst, ctx,) + args

        if ctx.descriptor.service_class is None:
            retval = ctx.function(*args)

        else:
            retval = ctx.descriptor.service_class.call_wrapper(ctx, args=args)

        return retval

    def _has_callbacks(self):
        return self.interface._has_callbacks()

    def reinitialize(self, server):
        """This is normally called on transport instantiation by ServerBase"""

        seen = set()

        from spyne import MethodDescriptor
        for d in self.interface.method_id_map.values():
            assert isinstance(d, MethodDescriptor)

            if d.aux is not None and not id(d.aux) in seen:
                d.aux.initialize(server)
                seen.add(id(d.aux))

            if d.service_class is not None and not id(d.service_class) in seen:
                d.service_class.initialize(server)
                seen.add(id(d.service_class))

    def __hash__(self):
        return hash(tuple((id(s) for s in self.services)))

    def check_unique_method_keys(self):
        keys = {}
        for s in self.services:
            for mdesc in s.public_methods.values():
                other_mdesc = keys.get(mdesc.internal_key, None)
                if other_mdesc is not None:
                    logger.error(
                        'Methods keys for "%s.%s" and "%s.%s" conflict',
                                   mdesc.function.__module__,
                                   six.get_function_name(mdesc.function),
                                   other_mdesc.function.__module__,
                                   six.get_function_name(other_mdesc.function))
                    raise MethodAlreadyExistsError(mdesc.internal_key)

                keys[mdesc.internal_key] = mdesc
