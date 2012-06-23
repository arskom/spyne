
Models
======

In spyne, models are used to mark how a certain message fragment will be
converted to and from its native python format. It also holds validation
information, and holds actually THE information interface document standards
like WSDL are designed to exposed.

Spyne's has built-in support most common data types and provides an API to
those who'd like to implement their own.

Base Classes
------------

.. automodule:: spyne.model
   :members:
   :show-inheritance:


.. automodule:: spyne.model._base
   :members:
   :show-inheritance:

Binary
------

.. automodule:: spyne.model.binary
   :members:
   :show-inheritance:

Complex
-------

.. automodule:: spyne.model.complex
   :members:
   :show-inheritance:

Enum
----

.. automodule:: spyne.model.enum
   :members:
   :show-inheritance:

Fault
-----

.. automodule:: spyne.model.fault
   :members:
   :show-inheritance:

Primitives
----------

.. automodule:: spyne.model.primitive
   :members:
   :show-inheritance:
   :inherited-members:

SQL Table
---------

.. automodule:: spyne.model.table
   :members:
   :show-inheritance:
