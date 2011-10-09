
**********
Rpclib FAQ
**********

Frequently asked questions about rpclib and related libraries.

Does rpclib support the SOAP 1.2 standard?
==========================================

Sort answer: No. Long answer: Nope.

Patches are welcome.

How do I implement a predefined WSDL?
=====================================

This is not a strength of rpclib, which is more oriented toward implementing
services from scratch. It does not have any functionality to parse an existing
WSDL document to produce the necessary Python classes and method stubs.

Patches are welcome. You can start by adapting the WSDL parser from
`RSL <http://rsl.sf.net>`.

Is it possible to use other decorators with @rpc/@srpc?
=======================================================

**Short answer:** Yes, but just use events. See the :ref:`manual-user-manager`
tutorial and the `events example <http://github.com/arskom/rpclib/blob/master/examples/user_manager/server_basic.py>`_
to learn how to do so. They work almost the same, except for the syntax.

**Long Answer:** Here's the magic from the :mod:`rpclib.decorator`: ::

    argcount = f.func_code.co_argcount
    param_names = f.func_code.co_varnames[arg_start:argcount]

So if ``f`` is your decorator, its signature should be the same as the user method,
otherwise the parameter names and numbers in the interface are going to be wrong,
which will cause weird errors.

Please note that if you just intend to have a convenient way to set additional
method metadata, you can use the ``_udp`` argument to the :func:`rpclib.decorator.srpc`
to your liking.

So if you're hell bent on using decorators, you should use the `decorator package <http://pypi.python.org/pypi/decorator/>`_.
Here's an example: ::

    from decorator import decorator

    def _do_something(func, *args, **kw):
        print "before call"
        result = func(*args, **kw)
        print "after call"
        return result

    def my_decor(f):
        return decorator(_do_something, f)

    class tests(ServiceBase):
        @my_decor
        @srpc(ComplexTypes.Integer, _returns=ComplexTypes.Integer)
        def testf(first):
            return first

Note that the place of the decorator matters. Putting it before ``@srpc`` will
make it run once, on service initialization. Putting it after will make it run
every time the method is called, but not on initialization.

Original thread: http://mail.python.org/pipermail/soap/2011-September/000565.html

PS: The next faq entry is also probably relevant to you.

How do I alter the behaviour of a user method without using decorators?
=======================================================================

``ctx.descriptor.function`` contains the handle to the original function. You
can set that attribute to arbitrary callables to prevent the original user
method from running.

