
#
# soaplib - Copyright (C) Soaplib contributors.
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

"""A soap server that uses ZeroMQ (zmq.REP) as transport"""

import zmq

from soaplib import MethodContext
from soaplib.server import Base

context = zmq.Context()

class Server(Base):
    transport = 'http://rfc.zeromq.org/'

    def __init__(self, app, app_url, wsdl_url=None):
        Base.__init__(self, app)
        self.app_url = app_url
        self.wsdl_url = wsdl_url

        self.soap_socket = context.socket(zmq.REP)
        self.soap_socket.bind(app_url)

    def __handle_wsdl_request(self):
        return self.app.get_wsdl(self.url)

    def serve_forever(self):
        while True:
            in_string = self.soap_socket.recv()
            ctx = MethodContext()

            in_object = self.get_in_object(ctx, in_string)

            if ctx.in_error:
                out_object = ctx.in_error
            else:
                out_object = self.get_out_object(ctx, in_object)
                if ctx.out_error:
                    out_object = ctx.out_error

            out_string = self.get_out_string(ctx, out_object)

            self.soap_socket.send(out_string)
