
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

"""A soap client that uses http (urllib2) as transport"""

import urllib2

from rpclib.client import Service
from rpclib.client import ClientBase
from rpclib.client import RemoteProcedureBase

import rpclib.protocol.soap

class _RemoteProcedure(RemoteProcedureBase):
    def __call__(self, *args, **kwargs):
        self.get_out_object(args, kwargs) # sets self.ctx.out_object
        self.get_out_string()

        out_string = ''.join(self.ctx.out_string)
        request = urllib2.Request(self.url, out_string)
        code = 200
        try:
            response = urllib2.urlopen(request)
            self.ctx.in_string = response.read()

        except urllib2.HTTPError,e:
            code=e.code
            self.ctx.in_string = e.read()

        self.get_in_object()

        if not (self.ctx.in_error is None):
            raise self.ctx.in_error
        elif code >= 500:
            raise self.ctx.in_object
        else:
            return self.ctx.in_object

class Client(ClientBase):
    def __init__(self, url, app):
        super(Client, self).__init__(url, app)

        # FIXME: this four-line block should be explained...
        if isinstance(app.in_protocol,rpclib.protocol.soap.Soap11):
            app.in_protocol.in_wrapper = rpclib.protocol.soap.Soap11.OUT_WRAPPER
        if isinstance(app.out_protocol,rpclib.protocol.soap.Soap11):
            app.out_protocol.out_wrapper= rpclib.protocol.soap.Soap11.NO_WRAPPER

        self.service = Service(_RemoteProcedure, url, app)
