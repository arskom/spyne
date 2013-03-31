
.. _manual-types:

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

This is one of those parts of Spyne where you will feel the Soap heritage as
we just *love* the high amount of professionalism in the Xml Schema standard.

Customization
-------------

Indeed... ``.customize()``


Primitives
----------

Using primitives in functions are very simple. Here are some examples: ::

    class SomeSampleServices(ServiceBase):
        @srpc(Decimal, Decimal, _returns=Decimal)
        def exp(x, y):
            """Exponentiate arbitrary rationals. A very DoS friendly service!"""
            return x ** y

        utcnow = @srpc(_returns=DateTime)(datetime.utcnow)

        @srpc(Unicode, _returns=Unicode)
        def upper(s):
            return s.upper()

        # etc.

Let's now look at them group by group:

Numbers
^^^^^^^

Numbers are organized in a hierarchy, with the
:class:`spyne.model.primitive.Decimal` type  at the top. 
In its vanilla state, the ``Decimal`` class is the arbitrary-precision,
arbitrary-size generic number type that will accept just *any* decimal
number.

It has three direct subclasses: The arbitrary-size
:class:`spyne.model.primitive.Integer` type and the machine-dependent
:class:`spyne.model.primitive.Double` or
:class:`spyne.model.primitive.Float` (which are synonyms as Python does not
distinguish between floats and doubles) types. 

Unless you are absolutely, positively sure that you need to deal with
arbitrary-size numbers, (or you're implementing an existing API) you
should not use the arbitrary-size types in their vanilla form.

You must also refrain from using :class:`spyne.model.primitive.Float` and
:class:`spyne.model.primitive.Double` types unless you need your math to
roll faster as their representation is machine-specific, thus not very
reliable nor portable.

For integers, we recommend you to use types like 
:class:`spyne.model.primitive.UnsignedInteger32` which can only contain a
32-bit unsigned integer. (Which is very popular as e.g. a primary key type
in a relational database.)

For floating-point numbers, use the ``Decimal`` type with a pre-defined scale
and precision. E.g. ``Decimal(16, 4)`` can represent a 16-digit number in total
which can have up to 4 decimal digits, which could be used e.g. as a nice
monetary type. By the way, Spyne does not include types like ISO-4217 compliant
'currency' and 'monetary' types. [#]_ They are actually really easy to
implement. Needless to say, patches are welcome!

Please see the :mod:`spyne.model.primitive` documentation for more details
regarding number handling in Spyne.

Strings
^^^^^^^

There are two string types in Spyne: :class:`spyne.model.primitive.Unicode` and
:class:`spyne.model.primitive.String` whose native types are ``unicode`` and
``str`` respectively.

Unlike the Python ``str``, the Spyne ``String`` is not for arbitrary byte
streams.
You should not use it unless you are absolutely, positively sure that
you need to deal with text data with an unknown encoding.
In all other cases, you should just use the ``Unicode`` type. They actually
look the same from outside, this distinction is made just to properly deal
with the quirks surrounding Python-2's ``unicode`` type.

Remember that you have the ``ByteArray`` and ``File`` types at your disposal
when you need to deal with arbitrary byte streams.

The ``String`` type will be just an alias for ``Unicode``
once Spyne gets ported to Python 3. It might even be deprecated and removed in the
future, so make sure you are using either ``Unicode`` or ``ByteArray`` in your
interface definitions.

``File``, ``ByteArray``, ``Unicode`` and ``String`` are all arbitrary-size in
their vanilla versions. Don't forget to customize them with additional restrictions
when implementing public services.

See also the configuration parameters of your favorite transport for more
information on request size restriction and other precautions against
potential abuse.

Date/Time Types
^^^^^^^^^^^^^^^

:class:`spyne.model.primitive.Date`, :class:`spyne.model.primitive.Time` and
:class:`spyne.model.primitive.DateTime` correspond to the native types 
``datetime.date``, ``datetime.time`` and ``datetime.datetime`` respectively.
Spyne supports working with both offset-naive and offset-aware datetimes.

As long as you return the proper native types, you should be fine.

As a side note, the `dateutil <http://labix.org/python-dateutil>`_ package is
mighty useful for dealing with dates, times and timezones. Highly recommended!

Spatial Types
^^^^^^^^^^^^^

Spyne comes with six basic spatial types that are supported by popular packages
like `PostGIS <http://postgis.refractions.net/>`_ and 
`Shapely <`http://toblerity.github.com/shapely/`>_. These are the 

These are provided as ``Unicode`` wrappers that just define proper constraints
to force the incoming string to be WKT-compliant. WKB is not yet supported.

The incoming types are not parsed, but you can use ``shapely.wkb.loads()``
function to convert them to native geometric types.

:class:`spyne.model.primitive.Point`, :class:`spyne.model.primitive.Line` and
:class:`spyne.model.primitive.Polygon` and also their multi-variants, which are

:class:`spyne.model.primitive.MultiPoint`, :class:`spyne.model.primitive.MultiLine` 
and :class:`spyne.model.primitive.MultiPolygon`.

Miscellanous Types
^^^^^^^^^^^^^^^^^^

:class:`spyne.model.primitive.AnyUri`

:class:`spyne.model.primitive.Boolean`

:class:`spyne.model.primitive.Uuid`

Dynamic Types
^^^^^^^^^^^^^

:class:`spyne.model.primitive.AnyDict`

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



.. [#] See http://www.w3.org/TR/2001/WD-xforms-20010608/slice4.html for more
       information.

