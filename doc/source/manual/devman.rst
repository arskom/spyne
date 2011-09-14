
Developer Manual
================

So, you want to add a new transport, protocol or interface standard implementation to
rpclib? First, some information:

How Exactly is User Code Wrapped?
---------------------------------

Here's what happens when a request arrives to an Rpclib-based server:

The server transport decides whether this is a request for the interface
document or a remote proceduce call request. Every transport has its own way of
dealing with this.

If the incoming request was for the interface document, it's easy: The interface
document needs to be generated and returned as a nice chunk of string to the client.

The server transport first calls ``self.app.interface.build_interface_document()``
which builds and caches the document and later calls the
:func:`rpclib.interface.InterfaceBase.get_interface_document` that returns the cached
document.

If it was an RPC request, here's what happens:

#. The server must set the ``ctx.in_string`` attribute to an iterable of strings.
   This will contain the incoming byte stream.
#. The server calls the :class:`rpclib.server.ServerBase.get_in_object` call
   from its parent class.
#. The server then calls the ``create_in_document``, ``decompose_incoming_envelope``
   and ``deserialize`` functions from the protocol class. The first parses the
   incoming stream to the protocol serializer's internal representation, which
   is then split to header and body parts, which is later deserialized to the
   native python representations.
#. Once the protocol performs its voodoo, the ``ServerBase`` child calls
   ``get_out_object`` from its parent class that in turn calls the
   :func:`rpclib.application.Application.process_request` function.
#. The ``process_request`` function fires relevant events and calls the
   using :func:`rpclib.application.Application.call_wrapper` function.
   This function is overridable by user, but the overriding function must call
   the one in :class:`rpclib.application.Application` by convention. This in turn
   calls the :func:`rpclib.service.ServiceBase.call_wrapper` function, which has
   the same requirements by convention.
#. The :func:`rpclib.service.ServiceBase.call_wrapper` finally calls the user
   function, and the value is returned to ``process_request`` call, which sets
   the return value to ``ctx.out_object``.
#. The server object now calls the ``get_out_string`` function to get the response
   as an iterable of strings in ``ctx.out_string``. The ``get_out_string`` call
   calls the ``serialize`` and ``create_out_string`` functions of the protocol
   class.
#. The server pushes the stream from ctx.out_string back to the client.

You can apply the same logic in reverse to the client transport.

So all you need to do is to subclass the relevant base class and implement the
missing methods.

What's Next?
^^^^^^^^^^^^

Start hacking! Good luck, and be sure to pop out to the mailing list if you have
questions.
