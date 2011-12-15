
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

"""The ZeroMQ (zmq.REQ) client transport."""

import zmq

from rpclib.client import Service
from rpclib.client import RemoteProcedureBase
from rpclib.client import ClientBase

context = zmq.Context()

class _RemoteProcedure(RemoteProcedureBase):
    def __call__(self, *args, **kwargs):
        self.ctx = self.contexts[0]

        self.get_out_object(self.ctx, args, kwargs)
        self.get_out_string(self.ctx)
        out_string = ''.join(self.ctx.out_string)

        socket = context.socket(zmq.REQ)
        socket.connect(self.url)
        socket.send(out_string)

        self.ctx.in_string = [socket.recv()]
        self.get_in_object(self.ctx)

        if not (self.ctx.in_error is None):
            raise self.ctx.in_error
        else:
            return self.ctx.in_object

class ZeroMQClient(ClientBase):
    def __init__(self, url, app):
        ClientBase.__init__(self, url, app)

        self.service = Service(_RemoteProcedure, url, app)
