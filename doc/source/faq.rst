
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

**Short answer:** No, use events. See the :ref:`manual-user-manager` tutorial and
the `events example <http://github.com/arskom/rpclib/blob/master/examples/user_manager/server_basic.py>`_
to learn how to do so.

**Long Answer:** Here's the magic from the :mod:`rpclib.decorator`: ::

    argcount = f.func_code.co_argcount
    param_names = f.func_code.co_varnames[arg_start:argcount]

So if ``f`` is your decorator, the parameter names and numbers are going to be
wrong, which will cause weird errors. So just use events.

If you're hell bent on using decorators, you can wrap @srpc. However that's not
a supported way to work with rpclib, so you'll most probably be on your own.

Please note that if you just intend to have a convenient way to set additional
method metadata, you can use the ``_udp`` argument to the :func:`rpclib.decorator.srpc`
to your liking.
