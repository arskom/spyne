
.. _reference-base:

Fundamental Data Structures
===========================

MethodContext
-------------

.. autoclass:: rpclib.MethodContext
    :members:
    :inherited-members:

MethodDescriptor
----------------

.. autoclass:: rpclib.MethodDescriptor
    :members:
    :inherited-members:

.. _reference-eventmanager:


EventManager
------------

Rpclib supports a simple event system that can be used to have repetitive boiler
plate code that has to run for every method call nicely tucked away in one or
more event handlers. The popular use-cases include things like database
transaction management, logging and measuring performance.

Various Rpclib components support firing events at various stages during the
processing of the request, which are documented in the relevant classes.

The classes that support events are:
    * :class:`rpclib.application.Application`
    * :class:`rpclib.service.ServiceBase`
    * :class:`rpclib.protocol._base.ProtocolBase`
    * :class:`rpclib.server.wsgi.WsgiApplication`

.. autoclass:: rpclib.EventManager
    :members:
    :inherited-members:
