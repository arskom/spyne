
Models
======

In rpclib, models are used to mark how a certain message fragment will be
converted to and from its native python format. It also holds validation
information, and holds actually THE information interface document standards
like WSDL are designed to exposed.

Rpclib's has built-in support most common data types and provides an API to
those who'd like to implement their own.

Binary
------

.. automodule:: rpclib.model.binary
   :members:

Complex
-------

.. automodule:: rpclib.model.complex
   :members:

Enum
----

.. automodule:: rpclib.model.enum
   :members:

Fault
-----

.. automodule:: rpclib.model.fault
   :members:

Primitives
----------

.. automodule:: rpclib.model.primitive
   :members:

SQL Table
---------

.. automodule:: rpclib.model.table
   :members:
