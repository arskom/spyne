
.. _manual-user-manager:

User Manager
============

This tutorial builds on the :ref:`manual-helloworld` and relevant parts of the
:ref:`manual-types` tutorial. If you haven't yet done so, we recommended you
to read them first.

In this tutorial, we will introduce the context object and the events to show
how to implement a real-world service.

You can see the following code in context in the
`examples/user_manager/server_basic.py <http://github.com/arskom/spyne/blob/master/examples/user_manager/server_basic.py>`_.

The following is an event handler that is called on every method call.
It instantiates the ``UserDefinedContext`` class and sets it to the context
object's ``udc`` attribute, which is in fact short for 'User Defined Context'.

::

    def _on_method_call(ctx):
        ctx.udc = UserDefinedContext()


We register it as the application's ``'method_call'`` handler. ::

    application.event_manager.add_listener(
                            'method_call', _on_method_call)

Note that registering it to the service definition's event manager would have
the same effect, but it'd have to be set for every other ``Service``
subclass that we'd otherwise define: ::

    UserManagerService.event_manager.add_listener(
                            'method_call', _on_method_call)

You can also prefer to define your own ``Service`` class and use it as a
base class throughout your projects: ::

    class MyService(Service):
        pass

    MyService.event_manager.add_listener('method_call', _on_method_call)

Next, we define the UserDefinedContext object. It's just a regular Python
class with no specific api it should adhere to: ::

    class UserDefinedContext(object):
        def __init__(self):
            self.users = _user_database

        @staticmethod
        def get_next_user_id():
            global _user_id_seq

            _user_id_seq += 1

            return _user_id_seq

Such custom objects could be used to manage any repetitive task ranging from
transactions to logging or to performance measurements. An example on using
events to measure method performance can be found in the
`examples/events.py <http://github.com/arskom/spyne/blob/master/examples/events.py>`_.

Method Metadata
---------------

As said before, the smallest exposable unit in Spyne is the Service
subclass which has one or more functions decorated with the ``@rpc`` or
``@srpc`` decorator.

The ``Service`` subclasses are never instantiated, so methods decorated
by ``@rpc`` are implicit ``staticmethod``\s [#]_.

The ``@rpc`` decorator is what you would use most of the time. It passes an
implicit first argument, the context object, conventionally named ``ctx`` to
the user method. The ``@srpc`` decorator is more for functions that you want
to expose but have no direct control over. It's useful only for the simplest
cases, so when in doubt, you should just use ``@rpc``.

The ``@rpc`` decorator takes input types as ``*args`` and other properties as
underscore-prefixed ``**kwargs``\. It uses this information and argument names
extracted from function source to construct a ``ComplexModel`` object on the
fly.

Let's look at the following example: ::

    @rpc(UnsignedByte, DateTime, _returns=Unicode)
    def some_code(ctx, a_byte, a_date):
        return "This is what I got: %r %r" % (a_byte, a_date)

In the default configuration, the ``@rpc`` decorator creates input and output
types behind the scenes as follows: ::

    class some_code(ComplexModel):
        # the tns value to the Application constructor
        __namespace__ = 'application.tns'

        _type_info = [
            ('a_byte', UnsignedByte),
            ('a_date', DateTime),
        ]

    class some_codeResponse(ComplexModel):
        # the tns value to the Application constructor
        __namespace__ = 'application.tns'

        _type_info = [
            ('some_codeResult', Unicode),
        ]

You should consult the
:func:`spyne.decorator.rpc` reference for more information about various
parameters you can pass to tweak how the method is exposed.

The ``'Response'`` and ``'Result'`` suffixes are configurable as well. See
:mod:`spyne.const` reference for more information.


Decorators and ``@rpc``
^^^^^^^^^^^^^^^^^^^^^^^

Using other decorators with ``@rpc``\-decorated functions is possible, yet a
bit tricky.

Here's the magic from the :mod:`spyne.decorator`: ::

    argcount = f.func_code.co_argcount
    param_names = f.func_code.co_varnames[arg_start:argcount]

So if ``f`` here is your decorator, its signature should be the same as the
user method, otherwise the parameter names and numbers in the interface are
going to be wrong, which will cause weird errors [#]_.

This is called "decorator chaining" which is solved by the aptly-named
`decorator package <http://pypi.python.org/pypi/decorator/>`_. Here's an
example: ::

    from decorator import decorator

    def _do_something(func, *args, **kw):
        print "before call"
        result = func(*args, **kw)
        print "after call"
        return result

    def my_decor(f):
        return decorator(_do_something, f)

    class tests(Service):
        @my_decor
        @srpc(Integer, _returns=Integer)
        def testf(first):
            return first

Note that the place of the decorator matters. Putting it before ``@srpc`` will
make it run once, on service initialization. Putting it after will make it run
every time the method is called, but not on initialization.

If this looks like too much of a hassle for you, it's also possible to use
Spyne events instead of decorators.

``ctx.function`` contains the handle to the original function.
You can set that attribute to arbitrary callables to prevent the original user
method from running. This property is initiallized from
``ctx.descriptor.function`` every time a new context is initialized.

If for some reason you need to alter the ``ctx.descriptor.function``,
you can call :func:`ctx.descriptor.reset_function()` to restore it to its
original value.

Also consider thread-safety issues when altering global state.

What's next?
------------

You can read the :ref:`manual-sqlalchemy` document where the
:class:`spyne.model.complex.TTableModel` class and its helpers are introduced.
You can also have look at the :ref:`manual-validation` section where Spyne's
imperative and declarative input validation features are introduced.


.. [#] Here's how that's done: `Magic! <https://github.com/arskom/spyne/blob/295dd1f594b00719235f219b95269c248f102535/spyne/service.py#L49>`_. :)

.. [#] If you just intend to have a convenient way to set additional
       method metadata, you can assign any value to the ``_udp`` argument
       of the ``@rpc`` decorator.
