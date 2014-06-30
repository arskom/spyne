
.. _migration:

***************
Migration Guide
***************

.. _migration-210-211:

2.10 => 2.11
============

While Spyne tries very hard not to break backwards compatibility across minor
releases, fixes to some blatant bugs that we just can't stand having around
anymore that ship with 2.11 do have the possibility of breaking existing code.

The good news about this is that, in most of the cases, they find
inconsistencies in your code and force you to fix them before they hurt you one
way or the other.

So here's a list of things that you should look for in case your daemon refuses
to boot after switching to Spyne 2.11:

1) **Schema non-determinism due to inheritance**: Spyne now adds all child
   classes of a given parent class to the Xml Schema document, regardless of
   whether it's used in service definitions or not. This
   is a first step towards implementing polymorphic responses. So when a
   subclass contains
   a field that is also present in the parent class, you will see a "content
   model not determinist" [sic] error and the daemon will refuse to boot.
   This error could
   be hidden in cases where the subclass was not explicitly used as a type
   marker in @rpc either directly or indirectly.

   **Fix**: Make sure that the offending field is present in only one of the
   parent or child classes. Please note that common fields in sibling classes
   are not supposed to cause any issues.

2) **Unequal number of parameters in @rpc and function definition**: Spyne 2.10
   did not care when @rpc had more arguments than the actual function
   definition. Spyne 2.11 won't tolerate this and the daemon will refuse to boot.

   **Fix**: Make sure the number of arguments to @rpc and the function it
   decorates are consistent.

3) **Declared field order can change**: The field order inside the
   ``<sequence>`` tags in Xml Schema (and naturally Wsdl) documents should
   *in theory* stay the same, but we never know as CPython offers no guarantees
   about the element order consistency in its hashmap implementation.

   **Fix**: Explicitly declare ``_type_info`` as a sequence of
   ``(field_name, field_type)`` pairs.

   This is not much of a problem in Python 3, as it's possible to customize the
   class dict passed to the metaclass thanks to ``__prepare__``. We now pass an
   ordered dict by default in Python 3 so that the field order is the same as
   the field declaration order in class definition.

   However, some folks wanted the same functionality in Python 2 so bad that
   they dared to submit this horrendous hack:
   https://github.com/arskom/spyne/pull/343
   You can use it to make sure field
   order stays consistent across Spyne releases and CPython implementations.

   As it seemed to work OK with CPython 2.6 and 2.7 and PyPy, we decided to ship
   it with 2.11 after making sure that it's strictly opt-in. Please test it with
   your environment and report back as it's relying, as far as we can tell,
   on some implementation details of CPython.

4) **Change in class declaration order**: Spyne 2.11 uses a proper topological
   sorting algorithm for determining the order of the object definitions in the
   Xml Schema document. So the order of these will certainly be different from
   what 2.10 generates. This is not supposed to cause any issues though. Fingers
   crossed!

   **Fix:** There is no fix short of reverting the toposort commits.

5) **Possible change in automatically generated type names:** Partly as a result
   of the above point, but also as a result of more robust type enumeration
   logic, auto-generated type names could be different from what 2.10 generates,
   which may break break SOAP clients that use statically compiled copies of the
   WSDL document.

   **Fix:** Explicitly set type names of the markers you customize using the
   ``type_name`` argument.

6) **String or Unicode types may fail to (de)serialize:** As we removed
   hard-coded utf8 defaults from everywhere, code that silently worked before
   now can fail with ``"You need to define a source encoding for decoding
   incoming unicode values``.

   **Fix:** Just add ``'encoding='utf8'`` to the relevant types.

Please don't hesitate to contact us via people@spyne.io if you think
you have stumbled upon a backwards compatibility issue that wasn't elaborated
above.
