
.. _manual-validation:

Input Validation
================

The input validation features of Spyne are also mostly inherited from the Soap
world and follows the behavior of Xml validation operations as closely as
possible.

Input validation is an essential component of any distributed system exposed
to a non-trusted environment. Examples of validation constraints that Spyne
can apply are as follows:

- A number that must be within a certain range,
- A string that must match with a given regular expression.
- A string that can only take certain values.

Currently, data validation can be handled by two subsystems:

Xml schema validation:
    Such rules are enforced by lxml's schema validation feature. This is of
    course only useful for Xml-based protocols.

"Soft" validation:
    Spyne itself implements enforcing a subset of the XmlSchema-type
    constraints in a protocol-independent way. When using this mode, it's also
    possible to use Spyne's imperative validation hooks.

When validating Xml data, the differences between using "lxml" and "soft"
validation are as follows:

- Soft validation ignores unknown fields, while *lxml* validation rejects
    them.
- Soft validation doesn't care about namespaces, while *lxml* validation
    rejects unexpected namespaces.

============================== ======== =========
Criteria                       lxml     soft
============================== ======== =========
Unknown fields                 reject   ignore
Unknown namespaces             reject   ignore
Supported transport protocols  SOAP/XML any
============================== ======== =========

.. NOTE::
    The two validation subsystems operate independently, you can use either
    one, but not both at the same time. The validator is indicated when
    instantiating the protocol, by passing either ``validator='soft'`` or
    ``validator='lxml'`` to the constructor. ::

        #using 'soft' validation with HttpRpc
        application = Application([NameOfMonthService],
                tns='spyne.examples.multiprot',
                in_protocol=HttpRpc(validator='soft'),
                out_protocol=HttpRpc()
            )

        #using lxml validation with Soap
        application = Application([UserService],
                tns='spyne.examples.authentication',
                interface=Wsdl11(),
                in_protocol=Soap11(validator='lxml'),
                out_protocol=Soap11()
            )

Simple validation at the Xml schema level
-----------------------------------------

This applies to all the primitive data types, and is suitable for simple
logical conditions.

.. NOTE::
    Constraints applied at this level are reflected in the XML schema itself,
    thus a client that retrieves the WSDL of the service will be able to see
    what the constraints are.

Any primitive type
^^^^^^^^^^^^^^^^^^

Certain generic restrictions can be applied to any type. They are listed
below, along with their default values

- ``default = None`` - default value if the input is ``None``.
- ``nillable = True`` - if ``True``, the item can be null when provided. Note
    that this constraint only applies when the variable is actually provided
    in the input document and is ignored if it's not. You should set
    ``min_occurs=1`` if you want to force this variable to be present in
    incoming documents.
- ``min_occurs = 0`` - set this to 1 to make the type mandatory. Can be set to
    any positive integer. Note that if ``nillable=False``, the validator will
    still accept ``null`` values.
- ``max_occurs = 1`` - can be set to any strictly positive integer. Values
    greater than 1 will imply an iterable of objects as native Python type. It
    can be set to ``unbounded`` or ``decimal.Decimal('inf')`` to denote an array
    with infinitely many elements.

.. NOTE::
    You should not use float('inf') as its behavior has inconsistencies
    between platforms and Python versions. See:
    https://github.com/arskom/spyne/pull/155

These rules can be combined, the example below illustrates how to create a
mandatory string:

    Unicode(min_occurs=1, min_len=1, nillable=False)

Numbers
^^^^^^^

Integers and other countable numerical data types (i.e. except Float or
Double) can be compared with specific values, using the following keywords:
``ge``, ``gt``, ``le``, ``lt`` (they correspond to >=, >, <=, <) ::

    Integer(ge=1, le=12) #an integer between 1 and 12, i.e. 1 <= x <= 12

Strings
^^^^^^^

Strings can be validated against a regular expression: ::

    Unicode(pattern="[0-9]+") #must contain one or more digits

Length checks can be enforced as well: ::

    Unicode(min_len=5, max_len=10)

If you want to keep an incoming bytestream as a ``str`` with a known encoding,
that's also possible with the String type. You can specify:

- Which encoding the strings must be in
- How to handle the situations in which a string cannot be decoded properly (to
  understand how this works, consult `Python's documentation
  <http://docs.python.org/howto/unicode.html>`_) ::

        String(encoding = 'win-1251')
        String(unicode_errors = 'strict') #could be 'replace' or 'ignore'

These restrictions can be combined: ::

    String(encoding='win-1251', max_len=20)
    String(min_len=5, max_len=20, pattern='[a-z]')

Possible values
^^^^^^^^^^^^^^^

Sometimes you may want to allow only a finite set of values, or values which
can be difficult to describe in terms of an interval. If this is the case, you
can explicitly indicate the set: ::

    Integer(values=[1984, 13, 45, 42])
    Unicode(values=[u"alpha", u"bravo", u"charlie"]) # note the 'u' prefix

Advanced validation
^^^^^^^^^^^^^^^^^^^

Spyne offers several primitives for this purpose. Please see the
:class:`spyne.model.ModelBase` reference for more information.

These primitives are:

**validate_string** 
    invoked when the variable is extracted from the input XML data.
**validate_native**
    invoked after the string is converted to a specific Python value.

Since all data comes in as a byte stream, when you read it you get a ``str``
instance. So the ``validate_string`` hook is your first line of defense
against invalid data.

After the string validation passes, the data is converted to its native type.
You can then do some additional checks. Validation in this stage is handled by
the ``validate_native`` hook.

A string validation
^^^^^^^^^^^^^^^^^^^

A custom string type that can not contain the colon symbol (``':'``).

We'll have to declare our own class as a subclass of ``Unicode``\: ::

    class SpecialString(Unicode):
        """Custom string type that prohibits the use of colons"""

        @staticmethod
        def validate_string(cls, value):
            retval = True
            if value is not None and ":" in value:
                retval = False
            return (
                    Unicode.validate_string(value) and retval
                )

A native validation example
^^^^^^^^^^^^^^^^^^^^^^^^^^^

A custom numerical type that verifies whether the number is prime.

This time both flavours of validation are combined: *validate_string* to see
if it is a number, and then ``validate_native`` to see if it is prime. ::

    from math import sqrt, floor

    class Prime(UnsignedInteger):
        """Custom integer type that only accepts primes."""

        @staticmethod
        def validate_native(cls, value):
            return (
                UnsignedInteger.validate_native(value) and \
                all(a % i for i in xrange(2, floor(sqrt(a))))
            )

.. NOTE::
    Constraints applied at this level do **not** modify the XML schema itself.
    So a client that retrieves the WSDL of the service will not be aware of
    these restrictions. Keep this in mind and make sure that validation rules
    that are not visible in the XML schema are documented elsewhere.

.. NOTE::
    When overriding ``validate_string`` or ``validate_native`` in a custom
    type class, the validation functions from the parent class are
    **not invoked**.

    If you wish to apply those validation functions as well, you must call
    them explicitly.

Summary
^^^^^^^

- Simple checks can be applied at the XML schema level, you can control:
  - The length of a string,
  - The pattern with which a string must comply,
  - A numeric interval, etc.

- *Spyne* can apply arbitrary rules for the validation of input data:
  - *validate_string* is the first applied filter.
  - *validate_native* is the applied at the second phase.
  - Override these functions in your derived class to add new validation rules.
  - The validation functions must return a *boolean* value.
  - These rules are **not** shown in the XML schema.

What's next?
^^^^^^^^^^^^

Now that you've also learned how to tame incoming data, you can have a look at
the :ref:`manual-sqlalchemy` document where we explain how to easily integrate
with SQLAlchemy by showing how to map Spyne objects to table definitions and
rows returned by database queries.

You could also have a look at the :ref:`manual-metadata` section where service
metadata management apis are introduced.

Otherwise, please refer to the rest of the documentation or the mailing list
if you have further questions.
