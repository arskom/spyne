
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
    """Abstract base class for the callable that gets the request from the
    python caller and forwards it to the remote side.

    Child classes that implement transports should override the __call__
    function like so:

    def __call__(self, *args, **kwargs)

    where the args and kwargs are serialized using the protocol and sent to the
    remote side using the transport the child implements.
    """

    def __init__(self, url, app, name, out_header):
        self.url = url
        self.app = app

        self.ctx = MethodContext(app)
        self.ctx.method_request_string = name
        self.ctx.out_header = out_header

        self.ctx.service_class = self.app.get_service_class(self.ctx)
        self.ctx.descriptor = self.ctx.service_class.get_method(self.ctx)

    def get_out_object(self, args, kwargs):
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
        assert self.ctx.out_document is None
        assert self.ctx.out_string is None

        self.app.out_protocol.serialize(self.ctx)
        self.app.out_protocol.create_out_string(self.ctx, string_encoding)

    def get_in_object(self):
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
        """Must be overridden to initialize the service properly"""
        self.factory = Factory(app)

    def set_options(self, **kwargs):
        self.service.out_header = kwargs.get('soapheaders', None)
