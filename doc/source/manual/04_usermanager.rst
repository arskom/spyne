
.. _manual-user-manager:

User Manager
============

This tutorial builds on the :ref:`manual-helloworld` and :ref:`manual-types` tutorial.
If you haven't done so, we recommended you to read them first.

In this tutorial, we will talk about:

* Defining complex types.
* Customizing types.
* Defining events.

The simple example that we are going to be studying here using complex, nested
data is available here:
http://github.com/arskom/spyne/blob/master/examples/user_manager/server_basic.py

Here are the definitions for the two complex types that we will use: throughout
this section: ::

    class Permission(ComplexModel):
        application = Unicode
        feature = Unicode


    class User(ComplexModel):
        user_id = Integer
        username = Unicode
        firstname = Unicode
        lastname = Unicode
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

You can read the :ref:`manual-sqlalchemy` document where the
:class:`spyne.model.complex.TTableModel` class and its helpers are introduced.
You can also have look at the :ref:`manual-validation` section where Spyne's
imperative and declarative input validation features are introduced.
