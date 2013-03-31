
.. _manual-helloworld:

Spyne Models and Native Python Types
====================================

Spyne comes with many building blocks for you to define your own composite objects when necessary.

There are five types of models in Spyne:

* **Primitive:** These are basic models that can contain a single value at a time.
  Primitive types are more-or-less present in any programming language and all
  of them map to a well-defined Python type. Types like ``Integer``,
  ``Decimal``, ``Float``, ``String``, ``Date`` are all primitives. See the
  documentation for :mod:`spyne.model.primitive` for more info.

* **Enum:** Custom types that can take only a pre-determined number of values.
  It's also possible to get enum-like behavior with primitives as well. Enums
  are defined using the :class:`spyne.model.enum.Enum` class.

* **Binary:** Binary types are used to represent arbitrarily-long byte streams.
  There are two types of binary types in Spyne: The 
  :class:`spyne.model.binary.ByteArray` and the
  :class:`spyne.model.binary.File` class. While any type of ``str`` sequence
  can be used as ``ByteArray``, the ``File`` only works with a ``File.Value``
  instance. Please see the relevant example below for a more thorough
  explanation.

* **Complex:** Complex objects are subclasses of the
  :class:`spyne.model.complex.ComplexModel` class. They are hierarchical
  container classes that can contain any type of object.

* **Fault:** When an exception is thrown from the user code, it's serialized
  and returned to the client as a :class:`spyne.model.fault.Fault`. If this
  exception is not a subclass of ``Fault``, the client will probably see this
  as an internal error. Some of the most common exceptions that a web service
  might need to throw can be found in the :mod:`spyne.error` module.

Customization
-------------

yes... ``.customize()``


Primitives
----------

Using primitives in functions are very simple. Here are some examples: ::

        @srpc(Decimal, Decimal, _returns=Decimal)
        def prod(x, y):
            return x * y

        @srpc(_returns=DateTime)
        def now(s):
            return datetime.now()

        @srpc(Unicode, _returns=Unicode)
        def upper(s):
            return s.upper()

        # etc.

Let's now look at them case by case:

Numbers
^^^^^^^

Numbers are organized in a hierarchy. The
:class:`spyne.model.primitive.Decimal` type is the arbitrary-precision, arbitrary-size 
generic number type will accept any rational number. The
:class:`spyne.model.primitive.Integer` type is the arbitrary-size integer
type. You should not use these types unless you explicitly know you need to
deal with arbitrary-size numbers.

There are also limited types like the 
:class:`spyne.model.primitive.UnsignedInteger32` which can only contain an
32-bit unsigned integer.

You should also refrain from using :class:`spyne.model.primitive.Float` and
:class:`spyne.model.primitive.Double` types, as their representation is
machine-specific and use the ``Decimal`` type with a pre-defined scale and
precision. E.g. ``Decimal(9, 4)`` can represent a 9-digit number in total
which can have up to 4 decimal digits.

Please see the :mod:`spyne.model.primitive` documentation for more info.

Strings
^^^^^^^

There are two string types in Spyne: :class:`spyne.model.primitive.Unicode` and
:class:`spyne.model.primitive.String` whose native types are ```str`` and
``unicode`` respectively.

Unlike the Python ``str``, the Spyne ``String`` is
not for arbitrary byte streams but just non-encoded text data. You should always
use ``Unicode`` unless you really know you need to deal with a ``str`` type.

If you need to deal with arbitrary byte streams, remember that you shoul use
the ``ByteArray`` type. The ``String`` type will be just an alias for ``Unicode``
once Spyne gets ported to Python 3. It might even be deprecated and removed in the
future, so make sure you are using either ``Unicode`` or ``ByteArray`` in your
interface definitions.

Date/Time Types
^^^^^^^^^^^^^^^

:class:`spyne.model.primitive.Date`, :class:`spyne.model.primitive.Time` and
:class:`spyne.model.primitive.DateTime` correspond to the native types 
``datetime.date``, ``datetime.time`` and ``datetime.datetime`` respectively.
Spyne supports working with both offset-naive and offset-aware datetimes.

Spatial Types
^^^^^^^^^^^^^

:class:`spyne.model.primitive.Point`

:class:`spyne.model.primitive.Polygon`

:class:`spyne.model.primitive.MultiPolygon`

Miscellanous Types
^^^^^^^^^^^^^^^^^^

:class:`spyne.model.primitive.Boolean`

:class:`spyne.model.primitive.Uuid`

:class:`spyne.model.primitive.AnyDict`

:class:`spyne.model.primitive.AnyUri`

:class:`spyne.model.primitive.AnyXml`

Enum
----

Binary
------

Complex
-------

Fault
-----




What's next?
^^^^^^^^^^^^

See the :ref:`manual-user-manager` tutorial that will walk you through
defining complex objects and using events.
