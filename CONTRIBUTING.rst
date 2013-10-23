Spyne development guidelines
============================

Code format
-----------

The code should comply with PEP8.


Branching
---------

For fixing an issue or adding a feature create a new branch from ``master`` branch.


Pull request
------------

When submitting a pull request:

* add and run tests.
* describe the changes in ``CHANGELOG.rst``.
* create a pull request from your topic branch to ``master`` in upstream Spyne repo.
* review the diff of the pull request on github.


Development principles
----------------------

* when overriding a method in a class use ``super`` to call the parent implementation instead of
  directly specifying the parent class. This is needed to correctly call all implementations
  according to MRO when having "diamond inheritance".
