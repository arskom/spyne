
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

"""This module contains the ClientBase class and its helper objects."""

from rpclib._base import MethodContext
from rpclib.model.primitive import string_encoding

class Factory(object):
    def __init__(self, app):
        self.__app = app

    def create(self, object_name):
        return self.__app.interface.get_class_instance(object_name)

class Service(object):
    def __init__(self, rpc_class, url, app, *args, **kwargs):
        self.__app = app
        self.__url = url
        self.out_header = None
        self.rpc_class = rpc_class
        self.args = args
        self.kwargs = kwargs

    def __getattr__(self, key):
        return self.rpc_class(self.__url, self.__app, key, self.out_header,
                                                    *self.args, **self.kwargs)

class RemoteProcedureBase(object):
    """Abstract base class that handles all (de)serialization.

    Child classes must implement the client transport in the __call__ method
    using the following method signature: ::

        def __call__(self, *args, **kwargs):

    :param url:  The url for the server endpoint.
    :param app:  The application instance the client belongs to.
    :param name: The string identifier for the remote method.
    :param out_header: The header that's going to be sent with the remote call.
    """

    def __init__(self, url, app, name, out_header=None):
        self.url = url
        self.app = app

        initial_ctx = MethodContext(app)
        initial_ctx.method_request_string = name
        initial_ctx.out_header = out_header

        self.contexts = self.app.out_protocol.generate_method_contexts(initial_ctx)

    def __call__(self, *args, **kwargs):
        """Serializes its arguments, sends them, receives and deserializes the
        response."""

        raise NotImplementedError()

    def get_out_object(self, ctx, args, kwargs):
        """Serializes the method arguments to output document.

        :param args: Sequential arguments.
        :param kwargs: Name-based arguments.
        """

        assert ctx.out_object is None

        request_raw_class = ctx.descriptor.in_message
        request_type_info = request_raw_class._type_info
        request_raw = request_raw_class()

        for i in range(len(request_type_info)):
            if i < len(args):
                setattr(request_raw, request_type_info.keys()[i], args[i])
            else:
                setattr(request_raw, request_type_info.keys()[i], None)

        for k in request_type_info:
            if k in kwargs:
                setattr(request_raw, k, kwargs[k])

        ctx.out_object = list(request_raw)

    def get_out_string(self, ctx):
        """Serializes the output document to a bytestream."""

        assert ctx.out_document is None
        assert ctx.out_string is None

        self.app.out_protocol.serialize(ctx, self.app.out_protocol.REQUEST)

        if ctx.service_class != None:
            if ctx.out_error is None:
                ctx.service_class.event_manager.fire_event(
                                        'method_return_document', ctx)
            else:
                ctx.service_class.event_manager.fire_event(
                                        'method_exception_document', ctx)

        self.app.out_protocol.create_out_string(ctx, string_encoding)

        if ctx.service_class != None:
            if ctx.out_error is None:
                ctx.service_class.event_manager.fire_event(
                                            'method_return_string', ctx)
            else:
                ctx.service_class.event_manager.fire_event(
                                            'method_exception_string', ctx)

        if ctx.out_string is None:
            ctx.out_string = [""]

    def get_in_object(self, ctx):
        """Deserializes the response bytestream first as a document and then
        as a native python object.
        """

        assert ctx.in_string is not None
        assert ctx.in_document is None

        self.app.in_protocol.create_in_document(ctx)
        if ctx.service_class != None:
            ctx.service_class.event_manager.fire_event(
                                            'method_accept_document', ctx)

        # sets the ctx.in_body_doc and ctx.in_header_doc properties
        self.app.in_protocol.decompose_incoming_envelope(ctx,
                                        message=self.app.in_protocol.RESPONSE)

        # this sets ctx.in_object
        self.app.in_protocol.deserialize(ctx,
                                        message=self.app.in_protocol.RESPONSE)

        type_info = ctx.descriptor.out_message._type_info

        if len(ctx.descriptor.out_message._type_info) == 1: # TODO: Non-Wrapped Object Support
            wrapper_attribute = type_info.keys()[0]
            ctx.in_object = getattr(ctx.in_object, wrapper_attribute, None)


class ClientBase(object):
    """The base class for all client applications. ``self.service``
    attribute should be initialized in the constructor of the child class.
    """

    def __init__(self, url, app):
        self.factory = Factory(app)

    def set_options(self, **kwargs):
        """Sets call options.

        :param out_header:  Sets the header object that's going to be sent with
                            the remote procedure call.
        :param soapheaders: A suds-compatible alias for out_header.
        """

        if ('soapheaders' in kwargs) and ('out_header' in kwargs):
            raise ValueError('you should specify only one of "soapheaders" or '
                             '"out_header" keyword arguments.')

        self.service.out_header = kwargs.get('soapheaders', None)
        if self.service.out_header is None:
            self.service.out_header = kwargs.get('out_header', None)
