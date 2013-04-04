
.. _reference-model:

Models
======

The `spyne.model` package contains the Spyne type markers to denote primitive
and complex types in object and method definitions.

Spyne has built-in support most common data types and provides an API to
those who'd like to implement their own.

Base Classes
------------

.. automodule:: spyne.model._base
   :members:
   :show-inheritance:

Model Groups
------------

There are five types of models in Spyne:

.. toctree::
    :maxdepth: 2

    primitive
    binary
    enum
    complex
    fault
    sql