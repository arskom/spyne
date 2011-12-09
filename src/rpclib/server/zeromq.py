
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

"""This module contains a server implementation that uses ZeroMQ (zmq.REP) as
transport.
"""

import zmq

from rpclib._base import MethodContext
from rpclib.server import ServerBase

context = zmq.Context()
"""The ZeroMQ context."""

class ZmqMethodContext(MethodContext):
    def __init__(self, app):
        MethodContext.__init__(self, app)
        self.transport.type = 'zmq'

class ZeroMQServer(ServerBase):
    """The ZeroMQ server transport."""
    transport = 'http://rfc.zeromq.org/'

    def __init__(self, app, app_url, wsdl_url=None):
        ServerBase.__init__(self, app)

        self.app_url = app_url
        self.wsdl_url = wsdl_url

        self.soap_socket = context.socket(zmq.REP)
        self.soap_socket.bind(app_url)

    def __handle_wsdl_request(self):
        return self.app.get_interface_document(self.url)

    def serve_forever(self):
        """Runs the ZeroMQ server."""

        while True:
            initial_ctx = ZmqMethodContext(self.app)
            initial_ctx.in_string = [self.soap_socket.recv()]

            ctx, = self.generate_contexts(initial_ctx)
            if ctx.in_error:
                ctx.out_object = ctx.in_error
            
            else:
                self.get_in_object(ctx)

                if ctx.in_error:
                    ctx.out_object = ctx.in_error
                else:
                    self.get_out_object(ctx)
                    if ctx.out_error:
                        ctx.out_object = ctx.out_error

            self.get_out_string(ctx)
            self.soap_socket.send(''.join(ctx.out_string))
