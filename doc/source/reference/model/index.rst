
.. _reference-model:

Models
======

The `spyne.model` package contains the Spyne type markers to denote primitive
and complex types in object and method definitions.

Spyne has built-in support for most common data types and provides an API for
those who'd like to implement their own.

There are five types of models in Spyne:

.. toctree::
    :maxdepth: 2

    primitive
    binary
    enum
    complex
    fault
    sql

Base Classes
------------

.. autoclass:: spyne.model.ModelBase
   :members:
   :special-members:
   :exclude-members: __dict__,__weakref__

   .. autoattribute:: spyne.model.ModelBase.__orig__

   .. autoattribute:: spyne.model.ModelBase.__extends__

   .. autoattribute:: spyne.model.ModelBase.__namespace__

   .. autoattribute:: spyne.model.ModelBase.__type_name__

.. autoclass:: spyne.model.SimpleModel
   :members:
   :show-inheritance:
   :special-members:
   :exclude-members: __dict__,__weakref__

Modifiers
---------

.. autofunction:: spyne.model.Mandatory
