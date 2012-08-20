
.. _reference-base:

Fundamental Data Structures
===========================

MethodContext
-------------

.. autoclass:: spyne.MethodContext
    :members:
    :show-inheritance:

MethodDescriptor
----------------

.. autoclass:: spyne.MethodDescriptor
    :members:
    :show-inheritance:

.. _reference-eventmanager:


EventManager
------------

Spyne supports a simple event system that can be used to have repetitive
boilerplate code that has to run for every method call nicely tucked away in one
or more event handlers. The popular use-cases include tasks like database
transaction management, logging and measuring performance.

Various Spyne components support firing events at various stages during the
processing of the request, which are documented in the relevant classes.

The classes that support events are:
    * :class:`spyne.application.Application`
    * :class:`spyne.service.ServiceBase`
    * :class:`spyne.protocol._base.ProtocolBase`
    * :class:`spyne.server.wsgi.WsgiApplication`

.. autoclass:: spyne.EventManager
    :members:
    :show-inheritance:
