
.. _manual-user-manager:

User Manager
============

This tutorial builds on the :ref:`manual-helloworld` and relevant parts of the
:ref:`manual-types` tutorial. If you haven't yet done so, we recommended you
to read them first.

In this tutorial, we will introduce the context object and the events to show
how to implement a real-world service.

A less bloated variant of this example is avaiable here:
http://github.com/arskom/spyne/blob/master/examples/user_manager/server_basic.py

Here are the definitions for the two complex types that we will use throughout
this section: ::

    class Permission(ComplexModel):
        id = UnsignedInteger32
        application = Unicode(values=('usermgr', 'accountmgr'))
        feature = Unicode(values=('read', 'modify', 'delete'))

    class User(ComplexModel):
        id = UnsignedInteger32
        user_name = Unicode(32, min_len=4, pattern='[a-z0-9.]+')
        full_name = Unicode(64, pattern='\w+ (\w+)+')
        email = Unicode(pattern=r'\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[A-Z]{2,4}\b')
        permissions = Array(Permission)

Nothing new so far.

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
with no specific api it should adhere to: ::

    class UserDefinedContext(object):
        def __init__(self):
            self.users = _user_database

        @staticmethod
        def get_next_user_id():
            global _user_id_seq

            _user_id_seq += 1

            return _user_id_seq

Such custom objects could be used to manage any repetitive task ranging from
transactions to logging or to performance measurements. You can have a look at
the `events.py example <http://github.com/arskom/spyne/blob/master/examples/user_manager/server_basic.py>`_
in the examples directory in the source distribution for an example on using
events to measure method performance)

Method Metadata
---------------

TBD

Decorators and ``@rpc``
^^^^^^^^^^^^^^^^^^^^^^^

TBD

What's next?
------------

You can read the :ref:`manual-sqlalchemy` document where the
:class:`spyne.model.complex.TTableModel` class and its helpers are introduced.
You can also have look at the :ref:`manual-validation` section where Spyne's
imperative and declarative input validation features are introduced.
