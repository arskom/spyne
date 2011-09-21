.. _manual-t-and-p:

Implementing Transports and Protocols
=====================================

Some preliminary information would be handy before delving into details:

How Exactly is User Code Wrapped?
------------------------------

Here's what happens when a request arrives to an Rpclib server:

The server transport decides whether this is a request for the interface
document or a remote proceduce call request. Every transport has its own way of
dealing with this.

If the incoming request was for the interface document, it's easy: The interface
document needs to be generated and returned as a nice chunk of string to the client.
The server transport first calls ``self.app.interface.build_interface_document()``
which builds and caches the document and later calls the
:func:`rpclib.interface.InterfaceBase.get_interface_document` that returns the cached
document.

If it was an RPC request, here's what happens:

#. The server must set the ``ctx.in_string`` attribute to an iterable of strings.
   This will contain the incoming byte stream.
#. The server calls the :class:`rpclib.server.ServerBase.get_in_object` call
   from its parent class.
#. The server then calls the ``create_in_document``, ``decompose_incoming_envelope``
   and ``deserialize`` functions from the protocol class. The first parses the
   incoming stream to the protocol serializer's internal representation, which
   is then split to header and body parts, which is later deserialized to the
   native python representations.
#. Once the protocol performs its voodoo, the server calls ``get_out_object`` 
   which in turn calls the :func:`rpclib.application.Application.process_request`
   function.
#. The ``process_request`` function fires relevant events and calls the
   :func:`rpclib.application.Application.call_wrapper` function.
   This function is overridable by user, but the overriding function must call
   the one in :class:`rpclib.application.Application`. This in
   turn calls the :func:`rpclib.service.ServiceBase.call_wrapper` function,
   which has has same requirements.
#. The :func:`rpclib.service.ServiceBase.call_wrapper` finally calls the user
   function, and the value is returned to ``process_request`` call, which sets
   the return value to ``ctx.out_object``.
#. The server object now calls the ``get_out_string`` function to put the
   response as an iterable of strings in ``ctx.out_string``. The
   ``get_out_string`` function calls the ``serialize`` and ``create_out_string``
   functions of the protocol class.
#. The server pushes the stream from ctx.out_string back to the client.

You can apply the same logic in reverse to the client transport.

So if you want to implement a new transport or protocol, all you need to do is
to subclass the relevant base class and implement the missing methods.

A transport example: Persistent, DB-Backed, Fan-Out Queue
----------------------------------------------------

Here's the server: https://github.com/arskom/rpclib/blob/master/examples/authenticate/server_soap.py
Here's the client: https://github.com/arskom/rpclib/blob/master/examples/authenticate/client_suds.py

We skip the imports and dive straight into code. Here's the SQLAlchemy boilerplate for creating the database and other related machinery. ::

    db = create_engine('sqlite:///:memory:')
    metadata = MetaData(bind=db)
    DeclarativeBase = declarative_base(metadata=metadata)

This the table where queued messages are stored. ::

    class TaskQueue(TableModel, DeclarativeBase):
        __tablename__ = 'task_queue'

        id = Column(sqlalchemy.Integer, primary_key=True)
        data = Column(sqlalchemy.LargeBinary, nullable=False)

This is the table where the task id of the last processed task for each worker is stored. Workers are identified by an integer. ::

    class WorkerStatus(TableModel, DeclarativeBase):
        __tablename__ = 'worker_status'

        worker_id = Column(sqlalchemy.Integer, nullable=False, primary_key=True, autoincrement=False)
        task_id = Column(sqlalchemy.Integer, ForeignKey(TaskQueue.id), nullable=False)

The consumer is a :class:``rpclib.server.ServerBase`` child that receives requests by polling the database. 

The transport is for displaying it in the Wsdl. While it's irrelevant here, it's nice to put it in. ::

    class Consumer(ServerBase):
        transport = 'http://sqlalchemy.persistent.queue/'

We set the incoming values, create a database connection and set it to `self.session`. ::

        def __init__(self, app, db, consumer_id):
            ServerBase.__init__(self, app)

            self.session = sessionmaker(bind=db)()
            self.id = consumer_id

We also query the worker status table and get the id for the first task. If there is no record for own worker id, the server starts from task_id=0. ::

            try:
                self.session.query(WorkerStatus) \
                          .filter_by(worker_id=self.id).one()
            except NoResultFound:
                self.session.add(WorkerStatus(worker_id=self.id, task_id=0))
                self.session.commit()

This is the main loop for our server. ::

        def serve_forever(self):
            while True:

We first get the id of the last processed task: ::

                last = self.session.query(WorkerStatus).with_lockmode("update") \
                              .filter_by(worker_id=self.id).one()

Which is used to get the next tasks to process: ::

                task_queue = self.session.query(TaskQueue) \
                        .filter(TaskQueue.id > last.task_id) \
                        .order_by(TaskQueue.id)

Each task is a procedure call, so we create a :class:`rpclib.MethodContext` instance for each task and set transport-specific data to the ``ctx.transport`` object. ::

                for task in task_queue:
                    ctx = MethodContext(self.app)
                    ctx.in_string = [task.data]
                    ctx.transport.consumer_id = self.id
                    ctx.transport.task_id = task.id

This call parses the incoming request. ::

                    self.get_in_object(ctx)

In case of an error when parsing the request, the server logs the error and continues to process the next task in queue. The ``get_out_string`` call is smart enough to notice and serialize the error. ::

                    if ctx.in_error:
                        self.get_out_string(ctx)
                        logging.error(''.join(ctx.out_string))
                        continue

As the request was parsed correctly, the user method can be called to process the task. ::

                    self.get_out_object(ctx)

If there was an expected or non-expected error the result from the server's perspective is the same. So it logs the error and continues to process the next task in queue. ::

                    if ctx.out_error:
                        self.get_out_string(ctx)
                        logging.error(''.join(ctx.out_string))
                        continue

If task processing went fine, the server serializes the out object and logs that instead. ::

                    self.get_out_string(ctx)
                    logging.debug(''.join(ctx.out_string))

Finally, the task marked as processed.

                    last.task_id = task.id
                    self.session.commit()

Once all tasks in queue are comsumed, the server waits a pre-defined amount of time before polling the database for new tasks. ::

            time.sleep(10)

This concludes the worker implementation. But how do we put tasks in the task queue? That's the job of the ``Producer`` class that is implemented as an rpclib client.

Implementing clients is a two-stage operation. The main transport logic is in the :class:`rpclib.client.RemoteProcedureBase` child that is a native Python callable whose function is to serialize the arguments, send it to the server, receive the reply, deserialize it and pass the return value to the python caller.

We start with the constructor, where we initialize the SQLAlchemy database connection factory.

    class RemoteProcedure(RemoteProcedureBase):
        def __init__(self, url, app, name, out_header, db):
            RemoteProcedureBase.__init__(self, url, app, name, out_header)

            self.Session = sessionmaker(bind=db)

The implementation of the client is much simpler because we trust that the Rpclib code will do The Right Thing. Here, we serialize the arguments: ::

        def __call__(self, *args, **kwargs):
            session = self.Session()

            self.get_out_object(args, kwargs)
            self.get_out_string()

            out_string = ''.join(self.ctx.out_string)

And put it to the database: ::

            session.add(TaskQueue(data=out_string))
            session.commit()
            session.close()

The function does not return anything because this is an asyncronous client.

Here's the ``Producer`` class whose sole purpose is to initialize the right callable factory. ::

    class Producer(ClientBase):
        def __init__(self, url, app, db):
            ClientBase.__init__(self, url, app, db)

            self.service = Service(RemoteProcedure, url, app, db)

This is the worker service that will process the tasks. ::

    class AsyncService(ServiceBase):
        @rpc(Integer)
        def sleep(ctx, integer):
            print "Sleeping for %d seconds..." % (integer)
            time.sleep(integer)

And this event is here to do some logging. ::

    def _on_method_call(ctx):
        print "This is worker id %d, processing task id %d." % (
                                ctx.transport.consumer_id, ctx.transport.task_id)

    AsyncService.event_manager.add_listener('method_call', _on_method_call)

It's now time to deploy our service. We start by configuring the logger and creating the necessary sql tables: ::

    if __name__ == '__main__':
        logging.basicConfig(level=logging.DEBUG)
        logging.getLogger('sqlalchemy.engine.base.Engine').setLevel(logging.DEBUG)
        metadata.create_all()

We then initialize our application: ::

        application = Application([AsyncService], 'rpclib.async',
                interface=Wsdl11(), in_protocol=Soap11(), out_protocol=Soap11())

And queue some tasks: ::

        producer = Producer(db, application)
        for i in range(10):
            producer.service.sleep(i)

And finally start the one worker to consume the queued tasks: ::

        consumer = Consumer(application, db, 1)
        consumer.serve_forever()

That's about it! You can switch to another database engine that accepts multiple connections and insert tasks from another connection to see the consumer in action.

What's Next?
^^^^^^^^^^^^

Start hacking! Good luck, and be sure to pop out to the mailing list if you have
questions.

