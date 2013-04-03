
.. _manual-types:

Spyne Models and Native Python Types
====================================

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
  There are two binary types in Spyne: The
  :class:`spyne.model.binary.ByteArray` and the
  :class:`spyne.model.binary.File` class. While any sequence of ``str``
  instances can be used as ``ByteArray``, the ``File`` only works with a
  ``File.Value`` instance. Please see the relevant example below for a more
  thorough explanation.

* **Complex:** Complex objects are subclasses of the
  :class:`spyne.model.complex.ComplexModel` class. They are hierarchical
  container classes that can contain any type of object. Two well known
  examples are the
  :class:`spyne.model.complex.Array` and
  :class:`spyne.model.complex.Iterable` types.
  They are just specialized complex objects.

* **Fault:** When an exception is thrown from the user code, it's serialized
  and returned to the client as a :class:`spyne.model.fault.Fault`. If it is
  not a subclass of ``Fault``, the client will probably see this
  as an internal error. Some of the most common exceptions that a web service
  might need to throw can be found in the :mod:`spyne.error` module.

Before going into detail about each category of models, we will first talk
about an operation that applies to all models: Type Customization.

Customization
-------------

Model customization is how one adds declarative restrictions and other metadata
to a Spyne model. This model metadata is stored in a generic object called
``Attributes``. Every Spyne model has this object as a class attribute.

As an example, let's customize the vanilla ``Unicode`` type to accept only valid
email strings: ::

  class EmailString(Unicode):
      __type_name__ = 'EmailString'

      class Attributes(Unicode.Attributes):
          max_length = 128
          pattern = '[^@]+@[^@]+'

You must consult the reference of the type you want to customize in order to
learn about which values it supports for its ``Attributes`` object.

As this is a quite verbose way of doing it, Spyne offers an in-line
customization mechanism for every type: ::

    EmailString = Unicode.customize(
            max_length=128,
            pattern='[^@]+@[^@]+',
            type_name='EmailString',
        )

Here, ``type_name`` is a special argument name that gets assigned to
``__type_name__`` instead of the ``Attributes`` class.

Calling simple types directly is a shortcut to their customize method: ::

    EmailString = Unicode(
            max_length=128,
            pattern='[^@]+@[^@]+',
            type_name='EmailString',
        )

As restricting the length of a string is very common, the length limit can be
passed as a positional argument as well: ::

    EmailString = Unicode(128,
            pattern='[^@]+@[^@]+',
            type_name='EmailString',
        )

It's actually also not strictly necessary (yet highly recommended) to pass a
type name: ::

    EmailString = Unicode(128, pattern='[^@]+@[^@]+')

When the ``type_name`` is omitted, Spyne auto-generates a type name for the
new custom type basing on the class it's used in.

Type customizations can also be anonymously tucked inside other class
definitions: ::

    class User(ComplexModel):
        user_name = Unicode(64, pattern='[a-z0-9_-]')
        email_address = Unicode(128, pattern='[^@]+@[^@]+')

Do note that calling ``ComplexModel`` subclasses instantitates them. That's why
you should use the ``.customize()`` call, or plain old subclassing to customize
complex types: ::

    class MandatoryUser(User):
        class Attributes(User.Attributes):
            nullable=False
            min_occurs=1

or: ::

    MandatoryUser = User.customize(nullable=False, min_occurs=1)

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
monetary type. By the way, Spyne does not include types like
`ISO-4217 <http://www.currency-iso.org/>`_-compliant
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
`Shapely <`http://toblerity.github.com/shapely/>`_.

These are provided as ``Unicode`` subclasses that just define proper
constraints to force the incoming string to be compliant with the
`Well known text (WKT) <https://en.wikipedia.org/wiki/Well-known_text>`_
format. Well known binary (WKB) format is not (yet?) supported.

The incoming types are not parsed, but you can use ``shapely.wkb.loads()``
function to convert them to native geometric types.

The spatial types that Spyne suppors are as follows:

* :class:`spyne.model.primitive.Point`
* :class:`spyne.model.primitive.Line`
* :class:`spyne.model.primitive.Polygon`

Also the ``Multi*`` variants, which are:

* :class:`spyne.model.primitive.MultiPoint`
* :class:`spyne.model.primitive.MultiLine`
* :class:`spyne.model.primitive.MultiPolygon`

Miscellanous Types
^^^^^^^^^^^^^^^^^^

These exist:

:class:`spyne.model.primitive.AnyUri`

:class:`spyne.model.primitive.Boolean`

:class:`spyne.model.primitive.Uuid`

Dynamic Types
^^^^^^^^^^^^^

These also exist. Somewhat.

:class:`spyne.model.primitive.AnyDict`

:class:`spyne.model.primitive.AnyXml`

Enum
----

TBD

Binary
------

TBD

Complex
-------

Complex objects are, by definition, types that can contain other types. They
must be subclasses of :class:`spyne.model.primitive.ComplexModel` class.

Here's a sample complex object definition: ::

    class Permission(ComplexModel):
        application = Unicode
        feature = Unicode

The ``ComplexModel`` metaclass, namely the
:class:`spyne.model.complex.ComplexModelMeta` scans the class definition and
ignores

1. Those that begin with an underscore (``_``)
2. Those that are not subclasses of the ``ModelBase``.

If you want to use python keywords as field names, or need leading underscores
in field names, or you just want your Spyne definition and other code to be
separate, you can do away with the metaclass magic and do this: ::

    class Permission(ComplexModel):
        _type_info = {
            'application': Unicode,
            'feature': Unicode,
        }

However, you still won't get predictable field order, as you're just setting a
``dict`` to the ``_type_info`` attribute. If you also need to that, you need
to pass a sequence of ``(field_name, field_type)`` tuples, like so: ::

    class Permission(ComplexModel):
        _type_info = [
            ('application', Unicode),
            ('feature', Unicode),
        ]

Arrays
^^^^^^

If you need to deal with more than one instance of something, the
:class:`spyne.model.complex.Array` is what you need.

Imagine the following inside the definition of a ``User`` object: ::

        permissions = Array(Permission)

The User can have an infinite number of permissions. If you need to put a
limit to that, you can do this: ::

        permissions = Array(Permission.customize(max_occurs=15))

It is important to stress once more that Spyne restrictions are only enforced
for an incoming request when validation is enabled. If you want this
enforcement for every *assignment*, you do this the usual way by writing a
property setter.

The ``Array`` type has two alternatives. The first one is the
:class:`spyne.model.complex.Iterable` type. ::

        permissions = Iterable(Permission)

It is equivalent to the ``Array`` type from an interface perspective -- i.e.
the client will not see any difference between an ``Iterable`` and an ``Array``
as return type.

It's just meant to signal the internediate machinery that the return
value *could* be a generator and **must not** be consumed unless returning data
to the client. This comes in handy for, e.g. custom loggers because they should
not try to log the return value.

You could use the ``Iterable`` marker in other places instead of ``Array``
without any problems, but it's really meant to be used as return types in
function definitions.

The second alternative to the ``Array`` notation is the following: ::

        permissions = Permission.customize(max_occurs='unbounded')

The native value that you should return for both remain the same: a sequence
of the designated type. However, the exposed interface is slightly different.

When you use ``Array``, what really happens is that the ``customize()`` function
of the array type creates an in-place class that is equivalent to the
following: ::

        class PermissionArray(ComplexModel):
            Permission = Permission.customize(max_occurs='unbounded')

Whereas when you just set ``max_occurs`` to a value greater than 1, you just get
multiple values without the wrapping object.

As an example, let's look at the following array: ::

    v = [
        Permission(application='app', feature='f1'),
        Permission(application='app', feature='f2')
    ]

Here's how it would be serialized to XML with ``Array(Permission)`` as return
type: ::

    <PermissionArray>
      <Permission>
        <application>app</application>
        <feature>f1</feature>
      </Permission>
      <Permission>
        <application>app</application>
        <feature>f2</feature>
      </Permission>
    </PermissionArray>

The same value-type combination would result in the following json document: ::

    {
        "Permission": [
            {
                "application": "app",
                "feature": "f1"
            },
            {
                "application": "app",
                "feature": "f2"
            }
        ]
    }

However, when we serialize the same object to xml using the
``Permission.customize(max_occurs=float('inf'))`` annotation, we get two
separate Xml documents, like so: ::

    <Permission>
      <application>app</application>
      <feature>f1</feature>
    </Permission>
    <Permission>
      <application>app</application>
      <feature>f2</feature>
    </Permission>

As for Json, we get: ::

    [
        {
            "application": "app", 
            "feature": "f1"
        },
        {
            "application": "app", 
            "feature": "f2"
        }
    ]

At this point, dear reader, you may be going "Arrgh! More choices! Just tell
me what's best!"

Well, for Xml people, the second way of doing things is wrong, (Xml has a
one-root-per-document rule) yet sometimes, it must be done for compatibility
reasons. And doing it the first way will just annoy JSON people.

In order to let everbody keep the beautiful ``Array(Something)`` syntax, 
:class:`spyne.protocol.dictdoc.HierDictDocument`, parent class of Protocols
that eat ``dict`` s including ``JsonDocument``, has a ``skip_depth`` argument
which lets the protocol strip the wrapper objects from response documents.
In its current form, it's a hack. It can be developed into a full-featured
filter that also works with nested ``Array`` setups if there's a demand for
it.

You can play with the ``examples/arrays_simple_vs_complex.py`` in the source
repository to see the above mechanism at work.

Return Values
^^^^^^^^^^^^^

When working with functions, you don't need to return the CompexModel
subclasses themselves. Anything that walks and quacks like the designated
return type will work just fine. Specifically, the returned object should
return appropriate values on ``getattr()`` s for field names in the return
type. Any exceptions thrown by the object's ``__getattr__`` method will be
logged and ignored.

However, it is important to return *instances* and not classes themselves. Due
to the way Spyne serialization works, the classes themselves will also work as
return values until you actually seeing funky responses under load in
production. Don't do this! [#]_

Fault
-----

TBD


What's next?
^^^^^^^^^^^^

See the :ref:`manual-user-manager` tutorial that will walk you through
defining complex objects and using events.



.. [#] See http://www.w3.org/TR/2001/WD-xforms-20010608/slice4.html for more
       information.
.. [#] http://stackoverflow.com/a/15383191
