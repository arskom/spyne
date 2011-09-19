
.. _manual-metadata:

Working with RPC Metadata
=========================

In most of the real-world scenarios, rpc data comes with additional baggage like
authentication headers, routing history, and similar information. Rpclib comes
with rich mechanisms that lets you deal with both protocol and transport
metadata.

At the protocol level, the input and the output of the rpc function itself
are kept in ``ctx.in_object`` and ``ctx.out_object`` attributes of the
:class:`rpclib.MethodContext` whereas the protocol metadata reside in
``ctx.in_header`` and ``ctx.out_header`` attributes.

You can set values to the header attributes in the function bodies or events.
You just need to heed the order the events are fired, so that you don't
overwrite data.

If you want to use headers in a function, you must denote it either in the
decorator or the :class:`rpclib.service.ServiceBase` child that you use to
expose your functions.

A full example using most of the available metadata functionality is available
here: https://github.com/plq/rpclib/blob/master/examples/authenticate/server_soap.py

Protocol Headers
----------------

The protocol headers are available in ``ctx.in_header`` and ``ctx.out_header``
objects. You should set the ``ctx.out_header`` to the native value of the
declared type.

Header objects are defined just like any other object: ::

    class RequestHeader(ComplexModel):
        user_name = Mandatory.String
        session_id = Mandatory.String

They can be integrated to the rpc definition either by denoting it in the
service definition: ::

    class UserService(ServiceBase):
        __tns__ = 'rpclib.examples.authentication'
        __in_header__ = RequestHeader

        @rpc(_throws=PublicValueError, _returns=Preferences)
        def get_preferences(ctx):
            retval = preferences_db[ctx.in_header.user_name]

            return retval

Or in the decorator: ::

        @srpc(Mandatory.String, _throws=PublicValueError,
                                _in_header=RequestHeader, _returns=Preferences)

It's generally a better idea to set the header types in the ServiceBase child
as it's likely that a lot of methods will use it. This will avoid cluttering the
service definition with header declarations. The header declaration in the
decorator will overwrite the one in the service definition.

Among the protocols that support headers, only Soap is supported.

Transport Headers
-----------------

There is currently no general transport header api -- transport-specific apis
should be used for setting headers.

:class:`rpclib.server.wsgi.WsgiApplication`:
    The ``ctx.transport.resp_headers`` attribute is a dict made of header/value
    pairs, both strings.
