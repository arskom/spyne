
.. _manual-metadata:

Working with RPC Metadata
=========================

This section builds on :ref:`manual-user-manager` section. If you haven’t done
so, we recommended you to read it first.

In most of the real-world scenarios, an RPC request comes with additional
baggage like authentication headers, routing history, and similar information.
Spyne comes with rich mechanisms that lets you deal with both protocol and
transport metadata.

At the protocol level, the input and the output of the rpc function itself
are kept in ``ctx.in_object`` and ``ctx.out_object`` attributes of the
:class:`spyne.MethodContext` whereas the protocol metadata reside in
``ctx.in_header`` and ``ctx.out_header`` attributes.

You can set values to the header attributes in the function bodies or events.
You just need to consider the order the events are fired, so that you don't
overwrite data.

If you want to use headers in a function, you must denote it either in the
decorator or the :class:`spyne.service.Service` child that you use to
expose your functions.

A full example using most of the available metadata functionality is available
here: https://github.com/plq/spyne/blob/master/examples/authenticate/server_soap.py

Protocol Headers
----------------

As said before, the protocol headers are available in ``ctx.in_header`` and
``ctx.out_header`` objects. You should set the ``ctx.out_header`` to the
native value of the declared type.

Header objects are defined just like any other object: ::

    class RequestHeader(ComplexModel):
        user_name = Mandatory.Unicode
        session_id = Mandatory.Unicode

They can be integrated to the rpc definition either by denoting it in the
service definition: ::

    class UserService(Service):
        __tns__ = 'spyne.examples.authentication'
        __in_header__ = RequestHeader

        @rpc(_returns=Preferences)
        def some_call(ctx):
            # (...)

Or in the decorator: ::

        @rpc(_in_header=RequestHeader, _returns=Preferences)

It's generally a better idea to set the header types in the ``Service``
child as it's likely that all methods will use it. This will avoid cluttering
the service definition with header declarations. The header declaration in the
decorator will overwrite the one in the service definition.

Transport Headers
-----------------

There is currently no general transport header api -- transport-specific apis
should be used for setting headers. The only transport that supports
headers right now is Http, and you can use ``ctx.transport.resp_headers``
which is a dict where keys are field names and values are field values. Both
must be ``str`` instances.

Exceptions
----------

Here's a sample custom public exception: ::

    class PublicKeyError(Fault):
        __type_name__ = 'KeyError'
        __namespace__ = 'spyne.examples.authentication'

        def __init__(self, value):
            super(PublicKeyError, self).__init__(
                    faultcode='Client.KeyError',
                    faultstring='Value %r not found' % value
                )

Let's modify the python dict to throw our own exception class: ::

    class SpyneDict(dict):
        def __getitem__(self, key):
            try:
                return dict.__getitem__(self, key)
            except KeyError:
                raise PublicKeyError(key)

We can now modify the decorator to expose the exception this service can throw: ::

    preferences_db = SpyneDict()

    class UserService(Service):
        __tns__ = 'spyne.examples.authentication'
        __in_header__ = RequestHeader

        @rpc(_throws=PublicKeyError, _returns=Preferences)
        def get_preferences(ctx):
            retval = preferences_db[ctx.in_header.user_name]

            return retval

While this is not really necessary in the world of the dynamic languages, it'd
still be nice to specify the exceptions your service can throw in the interface
document. Plus, intefacing with your services will just feel more natural with
languages like Java where exceptions are kept on a short leash.

What's next?
^^^^^^^^^^^^

With this document, you know most of what Spyne has to offer for application
developers. You can refer to the :ref:`manual-t-and-p` section if you want to
implement your own transports and protocols.

Otherwise, please refer to the rest of the documentation or the mailing list
if you have further questions.
