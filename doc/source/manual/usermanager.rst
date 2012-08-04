
.. _manual-user-manager:

User Manager
============

This tutorial builds on the :ref:`manual-helloworld` tutorial. If you haven't
done so, we recommended you to read it first.

In this tutorial, we will talk about:

* Defining complex types.
* Customizing types.
* Defining events.

The following is an simple example using complex, nested data. It's available
here: http://github.com/arskom/spyne/blob/master/examples/user_manager/server_basic.py
::

    import logging
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('spyne.protocol.xml').setLevel(logging.DEBUG)

    from spyne.application import Application
    from spyne.decorator import rpc
    from spyne.interface.wsdl import Wsdl11
    from spyne.protocol.soap import Soap11
    from spyne.model.primitive import Unicode
    from spyne.model.primitive import Integer
    from spyne.model.complex import Array
    from spyne.model.complex import Iterable
    from spyne.model.complex import ComplexModel
    from spyne.server.wsgi import WsgiApplication
    from spyne.service import ServiceBase

    _user_database = {}
    _user_id_seq = 1

    class Permission(ComplexModel):
        __namespace__ = 'spyne.examples.user_manager'

        application = Unicode
        operation = Unicode

    class User(ComplexModel):
        __namespace__ = 'spyne.examples.user_manager'

        user_id = Integer
        user_name = Unicode
        first_name = Unicode
        last_name = Unicode
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

    application = Application([UserManagerService], 'spyne.examples.user_manager',
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

Juping into what's new: Spyne uses ``ComplexModel`` as a general type that,
when subclassed, will produce complex serializable types that can be used in a
public service. The ``Permission`` class is a fairly simple class with just
two members: ::

    class Permission(ComplexModel):
        application = Unicode
        feature = Unicode

Let's also look at the ``User`` class: ::

    class User(ComplexModel):
        user_id = Integer
        username = Unicode
        firstname = Unicode
        lastname = Unicode

Nothing new so far.

Below, you can see that the ``email`` member which has a regular expression
restriction defined. The ``Unicode`` type accepts other restrictions, please refer to
the :class:`spyne.model.primitive.Unicode` documentation for more information: ::

        email = Unicode(pattern=r'\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[A-Z]{2,4}\b')

The ``permissions`` attribute is an array, whose native type is a ``list`` of ``Permission``
objects. ::

        permissions = Array(Permission)

The following is deserialized as a generator, but looks the same from the
points of view of protocol and interface documents: ::

        permissions = Iterable(Permission)

The following is deserialized as a list of ``Permission`` objects, just like with
the ``Array`` example, but is shown and serialized differently in Wsdl and Soap
representations. ::

        permissions = Permission.customize(max_occurs='unbounded')

With the ``Array`` and ``Iterable`` types, a container class wraps multiple
occurences of the inner data type.

Here, we need to use the :func:`spyne.model._base.ModelBase.customize` call
because calling a ``ComplexModel`` subclass instantiates that class, whereas
calling a ``SimpleModel`` child implicitly calls the ``.customize`` method of
that class.

The ``customize`` function just sets given arguments as class attributes to
``cls.Attributes`` class. You can refer to the documentation of each class to
see which member of the ``Attributes`` class is used for the given object.

Here, we define a function to be called for every method call. It instantiates
the ``UserDefinedContext`` class and sets it to the context object's ``udc``
attribute, which is in fact short for 'User Defined Context'. ::

    def _on_method_call(ctx):
        ctx.udc = UserDefinedContext()

We register it to the application's 'method_call' handler. ::

    application.event_manager.add_listener('method_call', _on_method_call)

Note that registering it to the service definition's event manager would have
the same effect, but it'd have to be set for every service definition: ::

    UserManagerService.event_manager.add_listener('method_call', _on_method_call)

You can also prefer to define your own ``ServiceBase`` class and use it as a
base class throughout your projects: ::

    class MyServiceBase(ServiceBase):
        pass

    MyServiceBase.event_manager.add_listener('method_call', _on_method_call)

Next, we define the UserDefinedContext object. It's just a regular python class
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
logging or to performance measurements. You can have a look at the
`events.py example <http://github.com/arskom/spyne/blob/master/examples/user_manager/server_basic.py>`_
in the examples directory in the source distribution for an example on using
events to measure method performance)

What's next?
------------

This tutorial walks you through what you need to know to expose more complex
services. You can read the :ref:`manual-sqlalchemy` document where the
:class:`spyne.model.table.TableModel` class and its helpers are introduced.
You can also have look at the :ref:`manual-metadata` section where service
metadata management apis are introduced.

Otherwise, please refer to the rest of the documentation or the mailing list
if you have further questions.
