**WARNING:** This is from spyne's development branch. This version is not
released yet! Latest stable release can be found in the ``2_13`` branch.

If you like and use Spyne, star it on `Github <https://github.com/arskom/spyne>`_!

About
=====

Spyne aims to save the protocol implementers the hassle of implementing their
own remote procedure call api and the application programmers the hassle of
jumping through hoops just to expose their services using multiple protocols and
transports.

In other words, Spyne is a framework for building distributed
solutions that strictly follow the MVC pattern, where Model = `spyne.model`,
View = `spyne.protocol` and Controller = `user code`.

Spyne comes with the implementations of popular transport, protocol and
interface document standards along with a well-defined API that lets you
build on existing functionality.

The following are the primary sources of information about spyne:

* Spyne's home page is: http://spyne.io/
* The latest documentation for all releases of Spyne can be found at: http://spyne.io/docs
* The official source code repository is at: https://github.com/arskom/spyne
* The official spyne discussion forum is at: people at spyne dot io. Subscribe
  either via http://lists.spyne.io/listinfo/people or by sending an empty
  message to: people-subscribe at spyne dot io.
* You can download Spyne releases from
  `Github <https://github.com/arskom/spyne/downloads>`_ or
  `PyPi <http://pypi.python.org/pypi/spyne>`_.
* Continuous Integration: https://jenkins.arskom.com.tr/job/spyne/

Requirements
============

Spyne source distribution is a collection of highly decoupled components, which
makes it a bit difficult to put a simple list of requirements, as literally
everything except ``pytz`` is optional.

Python version
--------------

Spyne 2.13 supports Python 2.7, 3.6, 3.7, 3.8, 3.9 and 3.10.

Libraries
---------

Additionally the following software packages are needed for various subsystems
of Spyne:

* A Wsgi server of your choice is needed to wrap
  ``spyne.server.wsgi.WsgiApplication``
* `lxml>=3.2.5 <http://lxml.de>`_ is needed for any xml-related protocol.
* `lxml>=3.4.1 <http://lxml.de>`_ is needed for any html-related protocol.
* `SQLAlchemy <http://sqlalchemy.org>`_ is needed for
  ``spyne.model.complex.TTableModel``.
* `pyzmq <https://github.com/zeromq/pyzmq>`_ is needed for
  ``spyne.client.zeromq.ZeroMQClient`` and
  ``spyne.server.zeromq.ZeroMQServer``.
* `Werkzeug <http://werkzeug.pocoo.org/>`_ is needed for using
  ``spyne.protocol.http.HttpRpc`` under a wsgi transport.
* `PyParsing <http://pypi.python.org/pypi/pyparsing>`_ is needed for
  using ``HttpPattern``'s with ``spyne.protocol.http.HttpRpc``\.
* `Twisted <http://twistedmatrix.com/>`_ is needed for anything in
  ``spyne.server.twisted`` and ``spyne.client.twisted``.
* `Django <http://djangoproject.com/>`_ (tested with 1.8 and up) is needed for
  anything in ``spyne.server.django``.
* `Pyramid <http://pylonsproject.org/>`_ is needed for
  ``spyne.server.pyramid.PyramidApplication``.
* `msgpack>=1.0.0 <http://github.com/msgpack/msgpack-python/>`_ is needed for
  ``spyne.protocol.msgpack``.
* `PyYaml <https://bitbucket.org/xi/pyyaml>`_ is needed for
  ``spyne.protocol.yaml``.
* `simplejson <http://github.com/simplejson/simplejson>`_ is used when found
  for ``spyne.protocol.json``.

You are advised to add these as requirements to your own projects, as these are
only optional dependencies of Spyne, thus not handled in its setup script.

Installing
==========

You first need to have package manager (pip, easy_install) installed. Spyne
ships with a setuptools bootstrapper, so if setup.py refuses to run because it
can't find setuptools, do:

    bin/distribute_setup.py

You can add append --user to get it installed with $HOME/.local as prefix.

You can get spyne via pypi: ::

    easy_install [--user] spyne

or you can clone the latest master tree from Github: ::

    git clone git://github.com/arskom/spyne.git

To install from source distribution, you can run the setup script as usual: ::

    python setup.py install [--user]

If you want to make any changes to the Spyne code, just use ::

    python setup.py develop [--user]

so that you can painlessly test your patches.

Finally, to run the tests, you need to first install every single library that
Spyne integrates with, along with additional packages like ``pytest`` or ``tox``
that are only needed when running Spyne testsuite. An up-to-date list is
maintained in the ``requirements/`` directory, in separate files for both
Python 2.7 and >=3.6. To install everything, run: ::

    pip install [--user] -r requirements/test_requirements.txt

If you are still stuck on Python 2.x however, you should use: ::

    pip install [--user] -r requirements/test_requirements_py27.txt

Assuming all dependencies are installed without any issues, the following
command will run the whole test suite: ::

    python setup.py test

Spyne's test harness has evolved a lot in the 10+ years the project has been
active. It has 3 main stages: Traditional unit tests, tests that perform
end-to-end testing by starting actual daemons that listen on real TCP sockets
on hard-coded ports, and finally Django tests that are managed by tox. Naively
running pytest etc in the root directory will fail as their auto-discovery
mechanism was not implemented with Spyne's requirements in mind.

Getting Support
===============

Official support channels are as follows:

- The official mailing list for both users and developers alike can be found at:
  http://lists.spyne.io/listinfo/people.

- You can use the 'spyne' tag to ask questions on
  `Stack Overflow <https://stackoverflow.com/questions/tagged/spyne>`_.

- You can also use the `forum <https://github.com/arskom/spyne/discussions>`_ on
  the project's github page.

Please don't use the issue tracker for asking questions. It's a database that
holds the most important information for the project, so we must avoid
cluttering it as much as possible.

Contributing
============

If you feel like helping out, see the CONTRIBUTING.rst file in the Spyne source
distribution for starting points and general guidelines.
