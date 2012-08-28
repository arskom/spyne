
Models
======

In Spyne, models are used to mark how a certain message fragment will be
converted to and from which native python format. They are also used to hold
both declarative and imperative restrictions.

Spyne has built-in support most common data types and provides an API to
those who'd like to implement their own.

Base Classes
------------

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

.. function:: spyne.model.enum.Enum

Fault
-----

.. autoclass:: spyne.model.fault.Fault
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
