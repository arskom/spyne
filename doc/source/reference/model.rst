
Models
======

In Spyne, models are used to mark how a certain message fragment will be
converted to and from which native python format. They are also used to hold
both declarative and imperative restrictions.

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

Binary Types
------------

.. automodule:: spyne.model.binary

.. autoclass:: spyne.model.binary.ByteArray
   :members:
   :show-inheritance:

.. autoclass:: spyne.model.binary.File
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

SQL Table
---------

.. automodule:: spyne.model.table
   :members:
   :show-inheritance:
