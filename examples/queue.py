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

"""This is a simple db-backed persistent task queue implementation."""

import time
import logging

import sqlalchemy

from sqlalchemy import MetaData
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import create_engine

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound

from spyne import MethodContext
from spyne.application import Application
from spyne.client import Service
from spyne.client import RemoteProcedureBase
from spyne.client import ClientBase
from spyne.decorator import rpc
from spyne.interface.wsdl import Wsdl11
from spyne.protocol.soap import Soap11
from spyne.model.primitive import Integer
from spyne.server import ServerBase
from spyne.service import ServiceBase

db = create_engine('sqlite:///:memory:')
metadata = MetaData(bind=db)
DeclarativeBase = declarative_base(metadata=metadata)


class TaskQueue(DeclarativeBase):
    __tablename__ = 'task_queue'

    id = Column(sqlalchemy.Integer, primary_key=True)
    data = Column(sqlalchemy.LargeBinary, nullable=False)


class WorkerStatus(DeclarativeBase):
    __tablename__ = 'worker_status'

    worker_id = Column(sqlalchemy.Integer, nullable=False, primary_key=True,
                                                            autoincrement=False)
    task_id = Column(sqlalchemy.Integer, ForeignKey(TaskQueue.id),
                                                            nullable=False)


class Consumer(ServerBase):
    transport = 'http://sqlalchemy.persistent.queue/'

    def __init__(self, db, app, consumer_id):
        ServerBase.__init__(self, app)

        self.session = sessionmaker(bind=db)()
        self.id = consumer_id

        try:
            self.session.query(WorkerStatus) \
                          .filter_by(worker_id=self.id).one()
        except NoResultFound:
            self.session.add(WorkerStatus(worker_id=self.id, task_id=0))
            self.session.commit()

    def serve_forever(self):
        while True:
            last = self.session.query(WorkerStatus).with_lockmode("update") \
                          .filter_by(worker_id=self.id).one()

            task_queue = self.session.query(TaskQueue) \
                    .filter(TaskQueue.id > last.task_id) \
                    .order_by(TaskQueue.id)

            for task in task_queue:
                initial_ctx = MethodContext(self.app)
                initial_ctx.in_string = [task.data]
                initial_ctx.transport.consumer_id = self.id
                initial_ctx.transport.task_id = task.id

                for ctx in self.generate_contexts(initial_ctx, 'utf8'):
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


class RemoteProcedure(RemoteProcedureBase):
    def __init__(self, db, app, name, out_header):
        RemoteProcedureBase.__init__(self, db, app, name, out_header)

        self.Session = sessionmaker(bind=db)

    def __call__(self, *args, **kwargs):
        session = self.Session()

        for ctx in self.contexts:
            self.get_out_object(ctx, args, kwargs)
            self.get_out_string(ctx)

            out_string = ''.join(ctx.out_string)

            session.add(TaskQueue(data=out_string))

        session.commit()
        session.close()


class Producer(ClientBase):
    def __init__(self, db, app):
        ClientBase.__init__(self, db, app)

        self.service = Service(RemoteProcedure, db, app)


class AsyncService(ServiceBase):
    @rpc(Integer)
    def sleep(ctx, integer):
        print("Sleeping for %d seconds..." % (integer))
        time.sleep(integer)


def _on_method_call(ctx):
    print("This is worker id %d, processing task id %d." % (
                                ctx.transport.consumer_id, ctx.transport.task_id))

AsyncService.event_manager.add_listener('method_call', _on_method_call)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('sqlalchemy.engine.base.Engine').setLevel(logging.DEBUG)
    metadata.create_all()

    application = Application([AsyncService], 'spyne.async',
            interface=Wsdl11(), in_protocol=Soap11(), out_protocol=Soap11())

    producer = Producer(db, application)
    for i in range(10):
        producer.service.sleep(i)

    consumer = Consumer(db, application, 1)
    consumer.serve_forever()
