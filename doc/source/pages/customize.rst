
Tuning method arguments
=======================


In Python, arguments of a function may be optional or mandatory.
SOAP allows for repeated arguments as well; this is done using the
:meth:`~soaplib.core.model.base.Base.customize` method of Soap objects.

Arguments of a SOAP method have various cardinality-related attributes:

* ``min_occurs``: The minimal number of occurences of this parameter; set to 0 for an optional field
* ``max_occurs``: The maximal number of occurences of this parameter; if more than 1, the argument will be passed as a list instead.
* ``nillable``: True or False, whether a value of 'Null' (an empty XML element) could be passed for this arguments; this translates to a Python value of ``None``.


Here is an example::

  class MyService(DefinitionBase):

    @soap(
        String.customize(min_occurs=1, max_occurs=1, nillable=False),
        String.customize(min_occurs=0, max_occurs="unbounded", nillable=True),
        String.customize(min_occurs=4, max_occurs=10, nillable=False)
    )
    def my_method(self, mandatory_string, list_of_strings, a_few_strings):
        pass

* The first argument must be present, and cannot be ``None``; it might still be an empty string.
* The second argument will be a list of strings, where some values might be ``None`` (for instance ``['foo', None, 'bar', None, None, 'baz']``
* The third argument is a list of strings, containing between 4 and 10 items. It cannot contain the ``None`` value: ``['foo', 'bar', 'baz', 'foo', '', 'foo']``


Primitives
----------

For the :mod:`~soaplib.core.primitive` types, there is no need to call the :meth:`~soaplib.core.model.base.Base.customize` method::

    # These are equivalent
    String(min_occurs=0, max_occurs=1, nillable=False)
    String.customize(min_occurs=0, max_occurs=1, nillable=False)

The use of :meth:`~soaplib.core.model.base.Base.customize` is mandatory on custom classes (inheriting from :class:`~soaplib.core.model.clazz.ClassModel`).
