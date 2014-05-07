.. image:: https://travis-ci.org/arskom/spyne.png?branch=master
        :target: http://travis-ci.org/arskom/spyne

**WARNING:** This is from spyne's development branch. This version is not released
yet! Latest stable release can be found in the ``2_10`` branch.

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

Spyne currently supports the WSDL 1.1 interface description standard, along with
SOAP 1.1 and the so-called HttpRpc, XmlDocument, JsonDocument, YamlDocument,
MessagePackDocument and MessagePackRpc protocols which can be transported via
Http or ZeroMQ. The transports can be used in both a client or server setting.

The following are the primary sources of information about spyne:

* Spyne's home page is: http://spyne.io/
* The latest documentation for all releases of Spyne can be found at: http://spyne.io/docs
* The official source code repository is at: https://github.com/arskom/spyne
* The official spyne discussion forum is at: people@spyne.io. Subscribe either
  via http://lists.spyne.io/listinfo/people or by sending an empty message to:
  people-subscribe at spyne dot io.
* You can download Spyne releases from
  `github <http://github.com/arskom/spyne/downloads>`_ or
  `pypi <http://pypi.python.org/pypi/spyne>`_.

Spyne is a generalized version of a Soap library known as soaplib. The following
legacy versions of soaplib are also available in the source repository at github
as branches:

* Soaplib-0.8 branch: http://github.com/arskom/spyne/tree/soaplib-0_8
* Soaplib-1.0 branch: http://github.com/arskom/spyne/tree/soaplib-1_0
* Soaplib-2.0 was never released as a stable package, but the branch is still
  available: http://github.com/arskom/spyne/tree/soaplib-2_0

Requirements
============

Spyne is known to work on Python versions 2.6 and 2.7. We're also looking for
volunteers to test Python 3.x.

The only hard requirement is `pytz <http://pytz.sourceforge.net/>`_ which is
available via pypi.

Additionally the following software packages are needed for various subsystems
of Spyne:

* A Wsgi server of your choice is needed to wrap
  ``spyne.server.wsgi.WsgiApplication``
* `lxml>=3.2.5 <http://lxml.de>`_ is needed for any xml-related protocol.
* `lxml>=3.3.0 <http://lxml.de>`_ is needed for any html-related protocol.
* `SQLAlchemy <http://sqlalchemy.org>`_ is needed for
  ``spyne.model.complex.TTableModel``.
* `pyzmq <https://github.com/zeromq/pyzmq>`_ is needed for
  ``spyne.client.zeromq.ZeroMQClient`` and
  ``spyne.server.zeromq.ZeroMQServer``.
* `Werkzeug <http://werkzeug.pocoo.org/>`_ is needed for using
  ``spyne.protocol.http.HttpRpc`` under a wsgi transport.
* `PyParsing<2.0 <http://pypi.python.org/pypi/pyparsing>`_ is needed for
  using ``HttpPattern``'s with ``spyne.protocol.http.HttpRpc``\. (PyParsing>=2.x
  is Python 3 only).
* `Twisted <http://twistedmatrix.com/>`_ is needed for
  ``spyne.server.twisted.TwistedWebResource`` and
  ``spyne.client.twisted.TwistedHttpClient``.
* `Django <http://djangoproject.com/>`_ (tested with 1.2 and up) is needed for
  :class:`spyne.server.django.DjangoApplication` and :class:`spyne.server.django.DjangoServer`.
* `Pyramid <http://pylonsproject.org/>`_ is needed for
  ``spyne.server.pyramid.PyramidApplication``.
* `msgpack-python <http://github.com/msgpack/msgpack-python/>`_ is needed for
  ``spyne.protocol.msgpack``.
* `PyYaml <https://bitbucket.org/xi/pyyaml>`_ is needed for
  ``spyne.protocol.yaml``.
* `simplejson <http://github.com/simplejson/simplejson>`_ is used when found
  for ``spyne.protocol.json``.

You are advised to add these as requirements to your own projects, as these are
only optional dependencies of Spyne, thus not handled in its setup script.

Installing
==========

You can get spyne via pypi: ::

    easy_install spyne

or you can clone the latest master tree from github: ::

    git clone git://github.com/arskom/spyne.git

To install from source distribution, you should run the setup script as usual: ::

    python setup.py install [--user]

If you want to make any changes to the Spyne code, just use ::

    python setup.py develop [--user]

so that you can painlessly test your patches.

Finally, to run the tests use: ::

    pyhon setup.py test

The test script should first install every single library that Spyne integrates
with to the current directory. You should have a python development envrionment
already set up so that packages like lxml can compile.


Getting Support
===============

The official mailing list for both users and developers alike can be found at
http://lists.spyne.io/listinfo/people.

You can also use the 'spyne' tag to ask questions on
`Stack Overflow <http://stackoverflow.com>`_.


Contributing
============

Please see the CONTRIBUTING.rst file in the Spyne source distribution for
information about how you can help Spyne get more awesome.

Acknowledgments
===============

.. image:: http://www.jetbrains.com/img/logos/pycharm_logo142x29.gif
        :target: http://www.jetbrains.com/pycharm/

Spyne committers get a free license for PyCharm Professional Edition, courtesy
of JetBrains.

.. image:: http://www.cloudbees.com/sites/default/files/Button-Built-on-CB-1.png
        :target: https://spyne.ci.cloudbees.com/

CloudBees generously hosts our Jenkins installation and gives us a ton of
compute time for free.


Thanks a lot guys!..
