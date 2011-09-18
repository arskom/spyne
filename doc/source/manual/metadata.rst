
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

Let's look at an example: ::

    class RequestHeader(ComplexModel):
        session_id = String

    class AuthenticationService(ServiceBase):
        @srpc(Mandatory.String, Mandatory.String, _returns=ByteArray)
        def authenticate(user_name, password):
            if user_name == 'neo' and password == 'Wh1teR@bb1t':
               return hash

        def get_preferences():

    application = Application([HelloWorldService], 'qx.soap.demo',
        interface=Wsdl11(),
        in_protocol=Soap11(validator='lxml'),
        out_protocol=Soap11()
    )


if __name__=='__main__':
    twisted_apps = [ 
        (WsgiApplication(application), 'app'),
    ]
    sys.exit(run_twisted(twisted_apps, 7789))
