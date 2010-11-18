
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

"""A soap client that uses ZeroMQ (zmq.REQ) as transport"""

import zmq

from rpclib.client import Service
from rpclib.client import RemoteProcedureBase
from rpclib.client import Base

context = zmq.Context()

class _RemoteProcedure(RemoteProcedureBase):
    def __call__(self, *args, **kwargs):
        out_object = self.get_out_object(args, kwargs)
        out_string = self.get_out_string(out_object)

        socket = context.socket(zmq.REQ)
        socket.connect(self.url)
        socket.send(out_string)
    
        in_str = socket.recv()

        return self.get_in_object(in_str)

class Client(Base):
    def __init__(self, url, app):
        Base.__init__(self, url, app)

        self.service = Service(_RemoteProcedure, url, app)
