
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

"""A server that doesn't support any transport at all -- it's here for testing
purposes.
"""

from rpclib.client._base import Factory
from rpclib._base import MethodContext
from rpclib.server import ServerBase

class NullServer(ServerBase):
    transport = 'noconn://null.rpclib'

    def __init__(self, app):
        ServerBase.__init__(self, app)

        self.service = _FunctionProxy(self, self.app)
        self.factory = Factory(self.app)

    def get_wsdl(self):
        return self.app.get_interface_document(self.url)

    def set_options(self, **kwargs):
        self.service.in_header = kwargs.get('soapheaders', None)

class _FunctionProxy(object):
    def __init__(self, parent, app):
        self.__app = app
        self.in_header = None

    def __getattr__(self, key):
        return _FunctionCall(self.__app, key, self.in_header)

class _FunctionCall(object):
    def __init__(self, app, key, in_header):
        self.__key = key
        self.__app = app
        self.__in_header = in_header

    def __call__(self, *args, **kwargs):
        ctx = MethodContext(self.__app)
        ctx.method_name = self.__key
        ctx.in_header = self.__in_header

        ctx.service_class = self.__app.get_service_class(ctx.method_name)
        ctx.descriptor = ctx.service_class.get_method(ctx.method_name)

        self.__app.process_request(ctx, args)

        if ctx.out_error:
            raise ctx.out_error
        else:
            return ctx.out_object
