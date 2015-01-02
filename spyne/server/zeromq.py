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

"""The ``spyne.server.zeromq`` module contains a server implementation that
uses ZeroMQ (zmq.REP) as transport.
"""
import threading

import zmq

from spyne.auxproc import process_contexts
from spyne._base import MethodContext
from spyne.server import ServerBase


class ZmqMethodContext(MethodContext):
    def __init__(self, app):
        super(ZmqMethodContext, self).__init__(app, MethodContext.SERVER)
        self.transport.type = 'zmq'

class ZeroMQServer(ServerBase):
    """The ZeroMQ server transport."""
    transport = 'http://rfc.zeromq.org/'

    def __init__(self, app, app_url, wsdl_url=None, ctx=None, socket=None):
        if ctx and socket and ctx is not socket.context:
            raise ValueError("ctx should be the same as socket.context")
        super(ZeroMQServer, self).__init__(app)

        self.app_url = app_url
        self.wsdl_url = wsdl_url

        if ctx:
            self.ctx = ctx
        elif socket:
            self.ctx = socket.context
        else:
            self.ctx = zmq.Context()

        if socket:
            self.zmq_socket = socket
        else:
            self.zmq_socket = self.ctx.socket(zmq.REP)
            self.zmq_socket.bind(app_url)

    def __handle_wsdl_request(self):
        return self.app.get_interface_document(self.url)

    def serve_forever(self):
        """Runs the ZeroMQ server."""

        while True:
            error = None

            initial_ctx = ZmqMethodContext(self)
            initial_ctx.in_string = [self.zmq_socket.recv()]

            contexts = self.generate_contexts(initial_ctx)
            p_ctx, others = contexts[0], contexts[1:]
            if p_ctx.in_error:
                p_ctx.out_object = p_ctx.in_error
                error = p_ctx.in_error

            else:
                self.get_in_object(p_ctx)

                if p_ctx.in_error:
                    p_ctx.out_object = p_ctx.in_error
                    error = p_ctx.in_error
                else:
                    self.get_out_object(p_ctx)
                    if p_ctx.out_error:
                        p_ctx.out_object = p_ctx.out_error
                        error = p_ctx.out_error

            self.get_out_string(p_ctx)

            process_contexts(self, others, error)

            self.zmq_socket.send(b''.join(p_ctx.out_string))

            p_ctx.close()


class ZeroMQThreadPoolServer(object):
    """Create a ZeroMQ server transport with several background workers,
    allowing asynchronous calls.

    More details on the pattern http://zguide.zeromq.org/page:all#Shared-Queue-DEALER-and-ROUTER-sockets"""

    def __init__(self, app, app_url, pool_size, wsdl_url=None, ctx=None, socket=None):
        if ctx and socket and ctx is not socket.context:
            raise ValueError("ctx should be the same as socket.context")

        self.app = app

        if ctx:
            self.ctx = ctx
        elif socket:
            self.ctx = socket.context
        else:
            self.ctx = zmq.Context()

        if socket:
            self.frontend = socket
        else:
            self.frontend = self.ctx.socket(zmq.ROUTER)
            self.frontend.bind(app_url)

        be_url = 'inproc://{tns}.{name}'.format(tns=self.app.tns, name=self.app.name)
        self.pool = []
        self.background_jobs = []
        for i in range(pool_size):
            worker, job = self.create_worker(i, be_url)
            self.pool.append(worker)
            self.background_jobs.append(job)

        self.backend = self.ctx.socket(zmq.DEALER)
        self.backend.bind(be_url)

    def create_worker(self, i, be_url):
        socket = self.ctx.socket(zmq.REP)
        socket.connect(be_url)
        worker = ZeroMQServer(self.app, be_url, socket=socket)
        job = threading.Thread(target=worker.serve_forever)
        job.daemon = True
        return worker, job

    def serve_forever(self):
        """Runs the ZeroMQ server."""

        for job in self.background_jobs:
            job.start()

        zmq.device(zmq.QUEUE, self.frontend, self.backend)

        # We never get here...
        self.frontend.close()
        self.backend.close()
