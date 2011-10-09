
.. _changelog:

******************
History and Future
******************

Versioning
==========

Rpclib respects Semantic Versioning rules outlined in http://semver.org.

This means  you can do better than just adding ``'rpclib'`` to your list of
dependencies. Assuming the current version of rpclib is 2.4.8,
you can use the following as dependency string:

* ``rpclib`` if you feel adventurous or are willing to work on rpclib itself.
* ``rpclib<3`` if you only want backwards-compatible bug fixes and new features.
* ``rpclib<2.5`` if you only want backwards-compatible bug fixes.
* ``rpclib=2.4.8`` if you rather like that version.

We have a policy of pushing to pypi as soon as possible, so be sure to at
least use the second option to prevent things from breaking unexpectedly.

Rpclib project uses -alpha -beta and -rc labels to denote unfinished code. We
don't prefer using separate integers for experimental labels. So for example,
instead of having 2.0.0-alpha47, we'll have 2.2.5-alpha.

* **-alpha** means unstable code. You may not recognize the project next time
  you look at it.
* **-beta** means stable(ish) api, unstable behavior, there are bugs everywhere!
  Don't be upset if some quirks that you rely on disappear.
* **-rc** means it's been working in production sans issues for some time on
  beta-testers' sites, but we'd still like it to have tested by a few more
  people.

These labels apply to the project as a whole. Thus, we won't tag the whole
project as beta because some new feature is not yet well-tested, but we will
clearly denote experimental code in its documentation.

.. include:: ../../ROADMAP.rst
.. include:: comparison.rst
.. include:: ../../CHANGELOG.rst
