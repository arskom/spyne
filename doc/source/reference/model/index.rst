
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

.. automodule:: spyne.model._base
   :members:
   :show-inheritance:

Modifiers
---------

.. autofunction:: spyne.model.Mandatory

