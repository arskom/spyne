
Models
======

In rpclib, models are used to mark how a certain message fragment will be
converted to and from its native python format. It also holds validation
information, and holds actually THE information interface document standards
like WSDL are designed to exposed.

Rpclib's has built-in support most common data types and provides an API to
those who'd like to implement their own.

Base Classes
------------

.. automodule:: rpclib.model
   :members:
   :show-inheritance:


.. automodule:: rpclib.model._base
   :members:
   :show-inheritance:

Binary
------

.. automodule:: rpclib.model.binary
   :members:
   :show-inheritance:

Complex
-------

.. automodule:: rpclib.model.complex
   :members:
   :show-inheritance:

Enum
----

.. automodule:: rpclib.model.enum
   :members:
   :show-inheritance:

Fault
-----

.. automodule:: rpclib.model.fault
   :members:
   :show-inheritance:

Primitives
----------

.. automodule:: rpclib.model.primitive
   :members:
   :show-inheritance:
   :inherited-members:

SQL Table
---------

.. automodule:: rpclib.model.table
   :members:
   :show-inheritance:
