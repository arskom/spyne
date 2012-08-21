
.. _manual-metadata:

Working with RPC Metadata
=========================

This section builds on :ref:`manual-user-manager` section. If you haven’t done
so, we recommended you to read it first.

In most of the real-world scenarios, an rpc request comes with additional
baggage like authentication headers, routing history, and similar information.
Spyne comes with rich mechanisms that lets you deal with both protocol and
transport metadata.

At the protocol level, the input and the output of the rpc function itself
are kept in ``ctx.in_object`` and ``ctx.out_object`` attributes of the
:class:`spyne.MethodContext` whereas the protocol metadata reside in
``ctx.in_header`` and ``ctx.out_header`` attributes.

You can set values to the header attributes in the function bodies or events.
You just need to heed the order the events are fired, so that you don't
overwrite data.

If you want to use headers in a function, you must denote it either in the
decorator or the :class:`spyne.service.ServiceBase` child that you use to
expose your functions.

A full example using most of the available metadata functionality is available
here: https://github.com/plq/spyne/blob/master/examples/authenticate/server_soap.py

Protocol Headers
----------------

As said before, the protocol headers are available in ``ctx.in_header`` and
``ctx.out_header`` objects. You should set the ``ctx.out_header`` to the native
value of the declared type.

Header objects are defined just like any other object: ::

    class RequestHeader(ComplexModel):
        user_name = Mandatory.String
        session_id = Mandatory.String

They can be integrated to the rpc definition either by denoting it in the
service definition: ::

    preferences_db = {}

    class UserService(ServiceBase):
        __tns__ = 'spyne.examples.authentication'
        __in_header__ = RequestHeader

        @rpc(_returns=Preferences)
        def get_preferences(ctx):
            retval = preferences_db[ctx.in_header.user_name]

            return retval

Or in the decorator: ::

        @rpc(_in_header=RequestHeader, _returns=Preferences)

It's generally a better idea to set the header types in the ServiceBase child
as it's likely that all methods will use it. This will avoid cluttering the
service definition with header declarations. The header declaration in the
decorator will overwrite the one in the service definition.

Among the protocols that support headers, only Soap is supported.

Transport Headers
-----------------

There is currently no general transport header api -- transport-specific apis
should be used for setting headers.

:class:`spyne.server.wsgi.WsgiApplication`:
    The ``ctx.transport.resp_headers`` attribute is a dict made of header/value
    pairs, both strings.

Exceptions
----------

The base class for public exceptions in Spyne is
:class:`spyne.model.fault.Fault`. See its docstring for more info about how it
works.

Here's how you define your own public exceptions: ::

    class PublicKeyError(Fault):
        __type_name__ = 'KeyError'
        __namespace__ = 'spyne.examples.authentication'

        def __init__(self, value):
            Fault.__init__(self,
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

    class UserService(ServiceBase):
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

.. NOTE::
    Spyne has common exceptions already defined and integrated to protocols.
    So if one raises :class:`spyne.error.ResourceNotFound` from user code,
    the HttpRpc protocol is smart enough to set the Http response code to 404.

What's next?
^^^^^^^^^^^^

With this document, you know most of what Spyne has to offer for application
developers. You can refer to the :ref:`manual-t-and-p` section if you want to
implement your own transports and protocols.

Otherwise, please refer to the rest of the documentation or the mailing list
if you have further questions.
