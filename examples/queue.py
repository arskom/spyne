#!/usr/bin/env python
# encoding: utf8
#
# Copyright © Burak Arslan <burak at arskom dot com dot tr>,
#             Arskom Ltd. http://www.arskom.com.tr
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    1. Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#    2. Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#    3. Neither the name of the owner nor the names of its contributors may be
#       used to endorse or promote products derived from this software without
#       specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
# OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

"""This is a simple db-backed persistent task queue implementation.

The producer (client) writes requests to a database table. The consumer (server)
polls the database every 10 seconds and processes new requests.
"""

import time
import logging

from sqlalchemy import MetaData
from sqlalchemy import create_engine

from sqlalchemy.orm import sessionmaker

from spyne import MethodContext, Application, rpc, TTableModel, Integer32, \
    UnsignedInteger, ByteArray, Mandatory as M

# client stuff
from spyne import RemoteService, RemoteProcedureBase, ClientBase

# server stuff
from spyne import ServerBase, Service

from spyne.protocol.soap import Soap11


db = create_engine('sqlite:///:memory:')
TableModel = TTableModel(MetaData(bind=db))


#
# The database tables used to store tasks and worker status
#


class TaskQueue(TableModel):
    __tablename__ = 'task_queue'

    id = Integer32(primary_key=True)
    data = ByteArray(nullable=False)


class WorkerStatus(TableModel):
    __tablename__ = 'worker_status'

    worker_id = Integer32(pk=True, autoincrement=False)
    task = TaskQueue.customize(store_as='table')

#
# The consumer (server) implementation
#

class Consumer(ServerBase):
    transport = 'http://sqlalchemy.persistent.queue/'

    def __init__(self, db, app, consumer_id):
        super(Consumer, self).__init__(app)

        self.session = sessionmaker(bind=db)()
        self.id = consumer_id

        if self.session.query(WorkerStatus).get(self.id) is None:
            self.session.add(WorkerStatus(worker_id=self.id))
            self.session.commit()

    def serve_forever(self):
        while True:
            # get the id of the last processed job
            last = self.session.query(WorkerStatus).with_lockmode("update") \
                          .filter_by(worker_id=self.id).one()

            # get new tasks
            task_id = 0
            if last.task is not None:
                task_id = last.task.id

            task_queue = self.session.query(TaskQueue) \
                    .filter(TaskQueue.id > task_id) \
                    .order_by(TaskQueue.id)

            for task in task_queue:
                initial_ctx = MethodContext(self)

                # this is the critical bit, where the request bytestream is put
                # in the context so that the protocol can deserialize it.
                initial_ctx.in_string = [task.data]

                # these two lines are purely for logging
                initial_ctx.transport.consumer_id = self.id
                initial_ctx.transport.task_id = task.id

                # The ``generate_contexts`` call parses the incoming stream and
                # splits the request into header and body parts.
                # There will be only one context here because no auxiliary
                # methods are defined.
                for ctx in self.generate_contexts(initial_ctx, 'utf8'):
                    # This is standard boilerplate for invoking services.
                    self.get_in_object(ctx)
                    if ctx.in_error:
                        self.get_out_string(ctx)
                        logging.error(''.join(ctx.out_string))
                        continue

                    self.get_out_object(ctx)
                    if ctx.out_error:
                        self.get_out_string(ctx)
                        logging.error(''.join(ctx.out_string))
                        continue

                    self.get_out_string(ctx)
                    logging.debug(''.join(ctx.out_string))

                    last.task_id = task.id
                    self.session.commit()

            time.sleep(10)

#
# The producer (client) implementation
#

class RemoteProcedure(RemoteProcedureBase):
    def __init__(self, db, app, name, out_header):
        super(RemoteProcedure, self).__init__(db, app, name, out_header)

        self.Session = sessionmaker(bind=db)

    def __call__(self, *args, **kwargs):
        session = self.Session()

        for ctx in self.contexts:
            self.get_out_object(ctx, args, kwargs)
            self.get_out_string(ctx)

            out_string = ''.join(ctx.out_string)
            print(out_string)

            session.add(TaskQueue(data=out_string))

        session.commit()
        session.close()


class Producer(ClientBase):
    def __init__(self, db, app):
        super(Producer, self).__init__(db, app)

        self.service = RemoteService(RemoteProcedure, db, app)

#
# The service to call.
#

class AsyncService(Service):
    @rpc(M(UnsignedInteger))
    def sleep(ctx, integer):
        print("Sleeping for %d seconds..." % (integer))
        time.sleep(integer)


def _on_method_call(ctx):
    print("This is worker id %d, processing task id %d." % (
                                ctx.transport.consumer_id, ctx.transport.task_id))

AsyncService.event_manager.add_listener('method_call', _on_method_call)

if __name__ == '__main__':
    # set up logging
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('sqlalchemy.engine.base.Engine').setLevel(logging.DEBUG)

    # Setup colorama and termcolor, if they are there
    try:
        from termcolor import colored
        from colorama import init

        init()

    except ImportError, e:
        logging.error("Install 'termcolor' and 'colorama' packages to get "
                      "colored log output")
        def colored(s, *args, **kwargs):
            return s

    logging.info(colored("Creating database tables...", 'yellow', attrs=['bold']))
    TableModel.Attributes.sqla_metadata.create_all()

    logging.info(colored("Creating Application...", 'blue'))
    application = Application([AsyncService], 'spyne.async',
                                in_protocol=Soap11(), out_protocol=Soap11())

    logging.info(colored("Making requests...", 'yellow', attrs=['bold']))
    producer = Producer(db, application)
    for i in range(10):
        producer.service.sleep(i)

    logging.info(colored("Spawning consumer...", 'blue'))
    # process requests. it'd make most sense if this was in another process.
    consumer = Consumer(db, application, consumer_id=1)
    consumer.serve_forever()
