
.. _manual-types:

Spyne Models and Native Python Types
====================================

There are five types of models in Spyne:

* **Primitive:** These are basic models that can contain a single value at a
  time. Primitive types are more-or-less present in any programming language
  and all of them map to a well-defined Python type. Types like ``Integer``,
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

As an example, let's customize the vanilla ``Unicode`` type to accept only
valid email strings: ::

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

As restricting the length of a string is very common (not all types have such
shortcuts), the length limit can be passed as a positional argument as well:

::

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

    class SomeSampleServices(Service):
        @srpc(Decimal, Decimal, _returns=Decimal)
        def exp(x, y):
            """Exponentiate arbitrary rationals. A very DoS friendly service!"""
            return x ** y

        utcnow = srpc(_returns=DateTime)(datetime.utcnow)

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
number. The native type is :class:`decimal.Decimal`.

It has two direct subclasses: The arbitrary-size
:class:`spyne.model.primitive.Integer` type and the machine-dependent
:class:`spyne.model.primitive.Double` (:class:`spyne.model.primitive.Float`
is a synonym for ``Double`` as Python does not distinguish between
floats and doubles) types.

Unless you are *sure* that you need to deal with arbitrary-size numbers you
should not use the arbitrary-size types in their vanilla form.

You must also refrain from using :class:`spyne.model.primitive.Float` and
:class:`spyne.model.primitive.Double` types unless you need your math to
roll faster as their representation is machine-specific, thus not really
reliable nor portable.

.. NOTE::
    ``float`` and ``decimal.Decimal`` are known to not be getting along too
    well. That's the case in Spyne as well.

    The ``Float``/``Double`` and ``Decimal`` markers are NOT compatible. Using
    ``float`` values in ``Decimal``-denoted fields and vice-versa will cause
    weird issues because Python's ``float`` values are serialized using
    ``repr()`` whereas ``Decimal`` is serialized using ``str()``. You have been
    warned.

For integers, we recommend you to use bounded types like
:class:`spyne.model.primitive.UnsignedInteger32` which can only contain a
32-bit unsigned integer. (Which is very popular as e.g. a primary key type
in a relational database.)

For floating-point numbers, use the ``Decimal`` type with a pre-defined scale
and precision. E.g. ``Decimal(16, 4)`` can represent a 16-digit number in total
which can have up to 4 decimal digits, which could be used e.g. as a nice
monetary type. [#]_

Note that it is your responsibility to make sure that the scale and precision
constraints are consistent with the values in the context of the decimal
package. See the :func:`decimal.getcontext` documentation for more
information.

It's also possible to set range constraints (``Decimal(gt=4, lt=10)``) or
discrete values (``UnsignedInteger8(values=[2,4,6,8]``). Please see the
:mod:`spyne.model.primitive` documentation for more details regarding number
handling in Spyne.

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
once Spyne gets ported to Python 3. It might even be deprecated and removed in
the future, so make sure you are using either ``Unicode`` or ``ByteArray`` in
your interface definitions.

``File``, ``ByteArray``, ``Unicode`` and ``String`` are all arbitrary-size in
their vanilla versions. Don't forget to customize them with additional
restrictions when implementing public services.

Just like numbers, it's also possible to place value-based constraints on
Strings (e.g. ``String(values=['red', 'green', 'blue'])`` ) but not lexical
constraints.

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
`Shapely <http://toblerity.github.com/shapely/>`_.

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

There are types defined for convenience in the Xml Schema standard which are
just convenience types on top of the text types. They are implemented as they
are needed by Spyne users. The following are some of the more notable ones.

* :class:`spyne.model.primitive.Boolean`: Life is simple here: Either ``True``
  or ``False``.

* :class:`spyne.model.primitive.AnyUri`: An RFC-2396 & 2732 compliant URI type.
  See: http://www.w3.org/TR/xmlschema-2/#anyURI

  **NOT YET VALIDATED BY SOFT VALIDATION!!!** Patches are welcome :)

* :class:`spyne.model.primitive.Uuid`: A fancy way of packing a 128-bit
  integer.

Please consult the :mod:`spyne.model.primitive` documentation for a more
complete list.

Dynamic Types
^^^^^^^^^^^^^

While Spyne is all about putting firm restrictions on your input schema,
it's also about flexibility.

That's why, while generally discouraged, the user can choose to accept or
return unstructured data using the :class:`spyne.model.primitive.AnyDict`, whose
native type is a regular ``dict`` and :class:`spyne.model.primitive.AnyXml`
whose native type is a
regular :class:`lxml.etree.Element`.

``AnyDict`` and ``AnyXml`` are roughly equivalent when the underlying
protocol is an XML based one -- ``AnyDict`` just totally ignores attributes.

Mandatory Variants
^^^^^^^^^^^^^^^^^^

TBD

Enum
----

The :class:`spyne.model.enum.Enum` type mimics the ``enum`` in C/C++ with some
additional type safety. It's part of the Spyne's SOAP heritage so it's  mostly
for compatibility reasons. If you want to use it, go right ahead, it will work.
But you can get the same functionality by defining a  custom ``Unicode`` type,
like so: ::

    SomeUnicode = Unicode(values=['x', 'y', 'z'])

The equivalent Enum-based declaration would be as follows: ::

    SomeEnum = Enum('x', 'y', 'z', type_name="SomeEnum")

These to would be serialized the same, yet their API is different. Lets look at
the following class definition: ::

    class SomeClass(ComplexModel):
        a = SomeEnum
        b = SomeUnicode

Assuming the following message comes in: ::

    <SomeClass>
      <a>x</a>
      <b>x</b>
    </SomeClass>

We will have: ::

    >>> some_class.a == 'x'
    True
    >>> some_class.b == 'x'
    False
    >>> some_class.a == SomeEnum.x
    False
    >>> some_class.b == SomeEnum.x
    True
    >>> some_class.b is SomeEnum.x
    True

So ``Enum`` is just a fancier value-restricted ``Unicode`` that has a
marginally faster (as it doesn't do string comparison) comparison option. You
probably don't need it.

Binary
------

Dealing with binary data has traditionally been a weak spot of most of the
serialization formats in use today. The best XML or MIME (email) does is
either base64 encoding or something similar, Json has no clue about binary
data (and many other things actually, but let's just not go there now) and
SOAP, in all its bloatiness, has quite a few binary encoding options
available, yet none of the "optimized" ones are implemented in Spyne [#]_.

Spyne supports binary data on all of the protocols it implements, falling back
to base64 encoding where necessary. In terms of message size, the efficient
protocols are `MessagePack <http://msgpack.org>`_ and good old Http. But, as
MessagePack does not offer an incremental parsing/generation API in its Python
wrapper, (in other words, it's not possible to parse the message without
having it all in memory) it's best to use the
:class:`spyne.protocol.http.HttpRpc` protocol when dealing with arbitrary-size
binary data.

A few points to consider:

1. ``HttpRpc`` only works with an Http transport.
2. ``HttpRpc`` supports only one file per request.
3. Not every http transport supports incremental parsing of incoming data.
   (e.g. Twisted). Make sure to test your stack end-to-end to see how it
   handles huge messages [#]_.

Now that all that is said, let's look at the API that Spyne provides for
dealing with binary data.

Spyne offers two types:

1. :class:`spyne.model.binary.ByteArray` is a simple type that contains
   arbitrary data. It's similar to Python's own ``str`` in terms of
   functionality, but it's a sequence of ``str`` instances instead of just a
   big ``str`` to be able to handle data in chunks using generators when
   needed [#]_.
2. :class:`spyne.model.binary.File` is a quirkier type that is mainly used to
   deal with Http way of dealing with file uploads. Its native value is the
   ``File.Value`` instance in :class:`spyne.model.binary.File`. See its
   documentation for more information.

Dealing with binary data with Spyne is not that hard -- you just need to make
sure your data is parsed incrementally when you're preparing to deal with
arbitrary-size binary data, which means you need to do careful testing as
different WSGI implementations behave differently.

Complex
-------

Types that can contain other types are termed "complex objects". They must be
subclasses of :class:`spyne.model.complex.ComplexModel` class.

Here's a sample complex object definition: ::

    class Permission(ComplexModel):
        application = Unicode
        feature = Unicode

The ``ComplexModel`` metaclass, namely the
:class:`spyne.model.complex.ComplexModelMeta` scans the class definition and
ignores attributes that:

1. Begin with an underscore (``_``)
2. Are not subclasses of the ``ModelBase``.

If you want to set some defaults (e.g. namespace) with your objects, you can
define your own ``ComplexModel`` base class as follows: ::

    class MyAppComplexModel(ComplexModelBase):
        __namespace__ = "http://example.com/myapp"
        __metaclass__ = ComplexModelMeta


If you want to use Python keywords as field names, or need leading underscores
in field names, or you just want your Spyne definition and other code to be
separate, you can do away with the metaclass magic and do this: ::

    class Permission(ComplexModel):
        _type_info = {
            'application': Unicode,
            'feature': Unicode,
        }

However, you still won't get predictable field order, as you're just assigning
a ``dict`` to the ``_type_info`` attribute. If you also need that, (which
becomes handy when e.g. you serialize your return value directly to HTML, or
you need to add fields to your XML messages in a backwards-compatible way [#]_\)
you need to pass a sequence of ``(field_name, field_type)`` tuples, like so: ::

    class Permission(ComplexModel):
        _type_info = [
            ('application', Unicode),
            ('feature', Unicode),
        ]

This comes with the added bonus of a predictable field order [#]_.  A second
way of getting a predictable field order is to set the 
:attr:`spyne.model.complex.ComplexModel.Attributes.declare_order` attribute.
The default value of that attribute is going to change in future version
of Spyne to ``"name"``.  Since the preivous example had the fields sorted by
name this will produce the same outcome: ::

    class PredictableComplexModel(ComplexModelBase):
        class Attributes(ComplexModelBase.Attributes)
            declare_order = "name"

    class Permission(PredictableComplexModel):
        application = Unicode
        feature = Unicode

Arrays
^^^^^^

If you need to deal with more than one instance of something, the
:class:`spyne.model.complex.Array` is what you need.

Imagine the following inside the definition of a ``User`` object: ::

        permissions = Array(Permission)

The User can have an infinite number of permissions. If you need to put a
limit to that, you can do this: ::

        permissions = Array(Permission.customize(max_occurs=15))

It is important to emphasize once more that Spyne restrictions are only
enforced for an incoming request when validation is enabled. If you want this
enforcement for *every* assignment, you do this the usual way by writing a
property setter.

The ``Array`` type has two alternatives. The first one is the
:class:`spyne.model.complex.Iterable` type. ::

        permissions = Iterable(Permission)

It is equivalent to the ``Array`` type from an interface perspective --
the client will not notice any difference between an ``Iterable`` and an
``Array`` as return type.

It's just meant to signal the internediate machinery that the return value
*could* be a generator and **must not** be consumed unless returning data to
the client. This comes in handy for, e.g. custom loggers because they should
not try to log the return value (as that would mean consuming the generator).

You could use the ``Iterable`` marker in other places instead of ``Array``
without any problems, but it's really meant to be used as return types in
function definitions.

The second alternative to the ``Array`` notation is the following: ::

        permissions = Permission.customize(max_occurs='unbounded')

The native value that you should return for both remain the same: a sequence
of the designated type. However, the exposed interface is slightly different
for Xml and friends (other protocols that ship with Spyne always assume the
second notation).

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

The same value/type combination would result in the following json document: ::

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

As for Json, we'd still get the same document. This trick sometimes needed by
XML people for interoperability. Otherwise, you can use whichever version
pleases your eye the most.

You can play with the ``examples/arrays_simple_vs_complex.py`` in the source
repository to see the above mechanism at work.

Complex Models as Return Values
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When working with functions, you don't need to return instances of the
CompexModel subclasses themselves. Anything that walks and quacks like the
designated return type will work just fine. Specifically, the returned object
should return appropriate values on ``getattr()``\s for field names in the
return type. Any exceptions thrown by the object's ``__getattr__`` method will
be logged and ignored.

However, it is important to return *instances* and not classes themselves. Due
to the way Spyne serialization works, the classes themselves will also work as
return values until you start seeing funky responses under load in production.
Don't do this! [#]_

Fault
-----

:class:`spyne.model.fault.Fault` a special kind of ``ComplexModel`` that is
also the subclass of Python's own :class:`Exception`.

When implementing public Spyne services, the recommendation is to raise
instances of ``Fault`` subclasses for client errors, and let other exceptions
bubble up until they get logged and re-raised as server-side errors by the
protocol handlers.

Not all protocols and transports care about distinguishing client and server
exceptions. Http has 4xx codes for client-side (invalid request case) errors
and 5xx codes for server-side (legitimate request case) errors. SOAP uses
"Client." and "Server." prefixes in error codes to make this distinction.

To integrate common transport and protocol behavior easily to Spyne, some
common exceptions are defined in the :mod:`spyne.error` module. These are
then hardwired to some common Http response codes so that e.g. raising a
``ResourceNotFoundError`` ends up setting the response code to 404.

You can look at the source code of the
:func:`spyne.protocol.ProtocolBase.fault_to_http_response_code` to see which
exceptions correspond to which return codes. This can be extended easily by
subclassing your transport and overriding the ``fault_to_http_response_code``
function with your own version.

Note that, while using an Exception sink to re-raise non-Fault based
exceptions as ``InternalError``\s is recommended, it's not Spyne's default
behavior -- you need to subclass the :class:`spyne.application.Application`
and override the :func:`spyne.application.Application.call_wrapper` function
like this:

::

    class MyApplication(Application):
        def call_wrapper(self, ctx):
            try:
                return ctx.service_class.call_wrapper(ctx)

            except error.Fault, e:
                sc = ctx.service_class
                logger.error("Client Error: %r | Request: %r",
                                                (e, ctx.in_object))
                raise

            except Exception, e:
                sc = ctx.service_class
                logger.exception(e)
                raise InternalError(e)


What's next?
------------

See the :ref:`manual-user-manager` tutorial that will walk you through
defining complex objects and using events.


.. [#] By the way, Spyne does not include types like
       `ISO-4217 <http://www.currency-iso.org/>`_-compliant
       'currency' and 'monetary' types. (See
       http://www.w3.org/TR/2001/WD-xforms-20010608/slice4.html for more
       information.)  They are actually really easy to
       implement. If you're looking for a simple way to contribute, this would
       be a nice place to start! Patches are welcome!

.. [#] Spyne used to have mtom (http://www.w3.org/Submission/soap11mtom10/)
       support. But as it was not maintained in a long time, it's not
       currently functional. Patches are welcome!

.. [#] Not every browser or http daemon supports huge file uploads due to
       issues around 32-bit integers. E.g. Firefox < 18.0 can't handle big
       files: https://bugzilla.mozilla.org/show_bug.cgi?id=215450

.. [#] Technically, a simple ``str`` instance is also a sequence of ``str``
       instances. However, using a ``str`` as the value to ``ctx.out_string``
       would cause sending data in one-byte chunks, which is very inefficient.
       See e.g. how HTTP's chunked encoding works.

.. [#] The "field order" is the order Spyne sends the fields in a
       ``ComplexModel`` to the client, and the order they are declared
       in the SOAP WSDL.  Currently Spyne's default field order is whatever
       is returned by a ``dict`` iterator.  This can change when the run time
       environment changes.  Things like adding a field, Spyne releasing a
       new version, or using a different version of the Python interpreter
       can cause the field order to change.  Such a changes are especially
       painful for SOAP clients because they typically fetch the WSDL once and
       assume it won't change - often requiring a recompile if it does.
       Spyne is moving away from it's current unpredicable field order to one
       controlled by
       :attr:`spyne.model.complex.ComplexModel.Attributes.declare_order`.
       It currently defaults to ``"random"`` but this will change in the
       future.  If an unpredictable field order might cause you problems set
       ``declare_order`` to ``"name"`` or ``"declared"``.

.. [#] When you add a new key to a python dict, the entry order can get
       shuffled. This will make the tag order in your schema change. If for
       some reason, clients don't see the new schema, they will send documents
       in old field order. This will make the 'lxml' validator upset as it also
       validates field older.

.. [#] http://stackoverflow.com/a/15383191
