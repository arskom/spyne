
.. _tutorial-user-manager:

User Manager
------------

Let's try a more complicated example than just strings and integers!
The following is an simple example using complex, nested data. It's available
here: http://github.com/arskom/rpclib/blob/master/examples/user_manager/server_basic.py
::

    import logging
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('rpclib.protocol.soap.soap11').setLevel(logging.DEBUG)

    from rpclib.application import Application
    from rpclib.decorator import rpc
    from rpclib.interface.wsdl import Wsdl11
    from rpclib.protocol.soap import Soap11
    from rpclib.model.primitive import String
    from rpclib.model.primitive import Integer
    from rpclib.model.complex import Array
    from rpclib.model.complex import Iterable
    from rpclib.model.complex import ComplexModel
    from rpclib.server.wsgi import WsgiApplication
    from rpclib.service import ServiceBase

    _user_database = {}
    _user_id_seq = 1

    class Permission(ComplexModel):
        __namespace__ = 'rpclib.examples.user_manager'

        application = String
        operation = String

    class User(ComplexModel):
        __namespace__ = 'rpclib.examples.user_manager'

        user_id = Integer
        user_name = String
        first_name = String
        last_name = String
        permissions = Array(Permission)

    class UserManagerService(ServiceBase):
        @rpc(User, _returns=Integer)
        def add_user(ctx, user):
            user.user_id = ctx.udc.get_next_user_id()
            ctx.udc.users[user.user_id] = user

            return user.user_id

        @rpc(Integer, _returns=User)
        def get_user(ctx, user_id):
            return ctx.udc.users[user_id]

        @rpc(User)
        def set_user(ctx, user):
            ctx.udc.users[user.user_id] = user

        @rpc(Integer)
        def del_user(ctx, user_id):
            del ctx.udc.users[user_id]

        @rpc(_returns=Iterable(User))
        def get_all_users(ctx):
            return ctx.udc.users.itervalues()

    application = Application([UserManagerService], 'rpclib.examples.user_manager',
                interface=Wsdl11(), in_protocol=Soap11(), out_protocol=Soap11())

    def _on_method_call(ctx):
        ctx.udc = UserDefinedContext()

    application.event_manager.add_listener('method_call', _on_method_call)

    class UserDefinedContext(object):
        def __init__(self):
            self.users = _user_database

        @staticmethod
        def get_next_user_id():
            global _user_id_seq

            _user_id_seq += 1

            return _user_id_seq

    if __name__=='__main__':
        try:
            from wsgiref.simple_server import make_server
        except ImportError:
            print "Error: example server code requires Python >= 2.5"

        server = make_server('127.0.0.1', 7789, WsgiApplication(application))

        print "listening to http://127.0.0.1:7789"
        print "wsdl is at: http://localhost:7789/?wsdl"

        server.serve_forever()

Jumping into what's new. ::

    class Permission(ComplexModel):
        application = String
        feature = String

    class User(ComplexModel):
        user_id = Integer
        username = String
        firstname = String
        lastname = String
        permissions = Array(Permission)

The `Permission` and `User` structures in the example are standard python
objects that extend `ComplexModel`.  Rpclib uses `ComplexModel` as a general
type that when extended will produce complex serializable types that can be used
in a public service.

Here, we define a function to be called for every method call. It instantiates
an object called UserDefinedContext and sets it to the context object's udc
attribute, which is in fact short for 'user defined context'. ::

    def _on_method_call(ctx):
        ctx.udc = UserDefinedContext()

We register it to the application's 'method_call' handler. ::

    application.event_manager.add_listener('method_call', _on_method_call)

Note that registering it to the service definition's event manager would have
the same effect: ::

    UserManagerService.event_manager.add_listener('method_call', _on_method_call)

Here, we define the UserDefinedContext object. It's just a regular python class
with no specific api it should adhere to, other than your own. ::

    class UserDefinedContext(object):
        def __init__(self):
            self.users = _user_database

        @staticmethod
        def get_next_user_id():
            global _user_id_seq

            _user_id_seq += 1

            return _user_id_seq

Such custom objects could be used to manage everything from transactions to
logging or to performance measurements. (see the events.py example in the
examples directory in the source distribution for an example on using events to
measure method performance.

What's next?
^^^^^^^^^^^^

This tutorial walks you through most of what you need to know to expose your
services. You can read the :ref:`tutorial-sqlalchemy` tutorial if you plan
to expose your database application using rpclib. Otherwise, you should refer to
the rest of the documentation or the mailing list if you have further questions.
