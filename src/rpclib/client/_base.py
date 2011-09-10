
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

import rpclib.protocol.soap.soap11

from rpclib._base import MethodContext
from rpclib.model.primitive import string_encoding

class Factory(object):
    def __init__(self, app):
        self.__app = app

    def create(self, object_name):
        return self.__app.interface.get_class_instance(object_name)

class Service(object):
    def __init__(self, rpc_class, url, app):
        self.__app = app
        self.__url = url
        self.out_header = None
        self.rpc_class = rpc_class

    def __getattr__(self, key):
        return self.rpc_class(self.__url, self.__app, key, self.out_header)

class RemoteProcedureBase(object):
    """Abstract base class that handles all (de)serialization.

    Child classes must implement the client transport in the __call__ method
    using the following method signature:

        def __call__(self, *args, **kwargs):

    :param url:  The url for the server endpoint.
    :param app:  The application instance the client belongs to.
    :param name: The string identifier for the remote method.
    :param out_header: The header that's going to be sent with the remote call.
    """

    def __init__(self, url, app, name, out_header):
        self.url = url
        self.app = app

        self.ctx = MethodContext(app)
        self.ctx.method_request_string = name
        self.ctx.out_header = out_header

        self.app.out_protocol.set_method_descriptor(self.ctx)

    def __call__(self, *args, **kwargs):
        """Serializes its arguments, sends them, receives and deserializes the
        response."""

        raise NotImplementedError()

    def get_out_object(self, args, kwargs):
        """Serializes the method arguments to output document<.

        :param args: Sequential arguments.
        :param kwargs: Name-based arguments.
        """

        assert self.ctx.out_object is None

        request_raw_class = self.ctx.descriptor.in_message
        request_type_info = request_raw_class._type_info
        self.ctx.out_object = request_raw = request_raw_class()

        for i in range(len(request_type_info)):
            if i < len(args):
                setattr(request_raw, request_type_info.keys()[i], args[i])
            else:
                setattr(request_raw, request_type_info.keys()[i], None)

        for k in request_type_info:
            if k in kwargs:
                setattr(request_raw, k, kwargs[k])

    def get_out_string(self):
        """Serializes the output document to a bytestream."""

        assert self.ctx.out_document is None
        assert self.ctx.out_string is None

        self.app.out_protocol.serialize(self.ctx)
        self.app.out_protocol.create_out_string(self.ctx, string_encoding)

    def get_in_object(self):
        """Deserializes the response bytestream to input document and native
        python object.
        """

        assert self.ctx.in_string is not None
        assert self.ctx.in_document is None

        self.app.in_protocol.create_in_document(self.ctx)

        # sets the ctx.in_body_doc and ctx.in_header_doc properties
        self.app.in_protocol.decompose_incoming_envelope(self.ctx)

        # this sets ctx.in_object
        self.app.in_protocol.deserialize(self.ctx)

        type_info = self.ctx.descriptor.out_message._type_info

        if (self.app.in_protocol.in_wrapper != self.app.in_protocol.NO_WRAPPER
                  and len(self.ctx.descriptor.out_message._type_info) == 1):
            wrapper_attribute = type_info.keys()[0]
            self.ctx.in_object = getattr(self.ctx.in_object,
                                                        wrapper_attribute, None)

class ClientBase(object):
    def __init__(self, url, app):
        """The self.service property should be initialized in the constructor of
        the child class."""

        self.factory = Factory(app)

        # FIXME: this four-line block should be explained...
        if isinstance(app.in_protocol,rpclib.protocol.soap.soap11._Soap11):
            app.in_protocol.in_wrapper = rpclib.protocol.soap.soap11._Soap11.OUT_WRAPPER
        if isinstance(app.out_protocol,rpclib.protocol.soap.soap11._Soap11):
            app.out_protocol.out_wrapper= rpclib.protocol.soap.soap11._Soap11.NO_WRAPPER

    def set_options(self, **kwargs):
        """Sets call options.

        :param out_header:  Sets the header object that's going to be sent with
                            the remote procedure call.
        :param soapheaders: A suds-compatible alias for out_header.
        """

        self.service.out_header = kwargs.get('soapheaders', None)
        if self.service.out_header is None:
            self.service.out_header = kwargs.get('out_header', None)
