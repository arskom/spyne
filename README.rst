
Warning! This is from rpclib's unstable development branch.

About
=====

Rpclib aims to save the protocol implementers the hassle of implementing their
own remote procedure call api and the application programmers the hassle of
jumping through hoops just to expose their services using multiple protocols and
transports.

Rpclib comes with the implementations of popular transport, protocol and
interface document standards along with an easy-to-use API that lets you
build on existing functionality.

Rpclib currently supports the WSDL 1.1 interface description standard,
along with SOAP 1.1 and the rest-minus-the-verbs HttpRpc protocols which can be
transported via HTTP or ZeroMQ. The transports can be used in a both client or
server setting.

The following are the primary sources of information about rpclib:

* The latest documentation for Rpclib can be found at: http://arskom.github.com/rpclib
* The official source code repository is at: https://github.com/arskom/rpclib
* The official rpclib discussion forum is at: http://mail.python.org/mailman/listinfo/soap
* You can download Rpclib packages from `github <http://github.com/arskom/rpclib/downloads>`_
  or `pypi <http://pypi.python.org/pypi/rpclib>`_.

Rpclib is a generalized version of a soap processing library known as soaplib.
The following legacy versions of soaplib are also available in the source repository at github
as branches.

* Soaplib-0.8 branch: http://github.com/arskom/rpclib/tree/soaplib-0_8
* Soaplib-1.0 branch: http://github.com/arskom/rpclib/tree/soaplib-1_0
* Soaplib-2.0 was never released as a stable package, but the branch is still
  available: http://github.com/arskom/rpclib/tree/soaplib-2_0

Requirements
============

Rpclib reportedly runs on any version of Python from 2.4 through 2.7. We're also
looking for volunteers to test Python 3.x.

While the aim is to have no requirements besides the standard Python library for
the Rpclib core, the following packages are needed if you want to run any
Rpclib service at all:

* `lxml <http://codespeak.net/lxml/>`_
* `pytz <http://pytz.sourceforge.net/>`_

both of which are available through ``easy_install``.

Additionally the following software packages are needed for various subsystems
that Rpclib supports:

* `SQLAlchemy <http://sqlalchemy.org>`_ for :class:`rpclib.model.table.TableModel`.
* `pyzmq <https://github.com/zeromq/pyzmq>`_ for
  :class:`rpclib.client.zeromq.ZeroMQClient` and
  :class:`rpclib.server.zeromq.ZeroMQServer`.
* A Wsgi server of your choice to wrap :class:`rpclib.server.wsgi.WsgiApplication`.

Installing
==========

You can get rpclib via pypi: ::

    easy_install rpclib

or you can clone from github: ::

    git clone git://github.com/arskom/rpclib.git

or get the source distribution from one of the download sites and unpack it.

To install from source distribution, you should run its setup script as usual: ::

    python setup.py install

To run the non-interop tests use: ::

    python setup.py test

And if you want to make any changes to the rpclib code, it's more comfortable to
use: ::

    python setup.py develop

Contributing
============

The main developers of rpclib lurk in the official soap implementors forum
in python.org, `here <http://mail.python.org/mailman/listinfo/soap/>`_.
That's mostly because rpclib is the continuation of soaplib, but also
because soap is an important part of rpclib.

If you wish to contribute to rpclib's development, create a personal fork
on GitHub.  When you are ready to push to the mainstream repository,
submit a pull request to bring your work to the attention of the core
committers. They will respond to review your patch and act accordingly.

To save both parties time, make sure the existing tests pass. If you are
adding new functionality or fixing a bug, please have the accompanying test.
This will both help us increase test coverage and insure your use-case
is immune to feature code changes. You could also summarize in one or
two lines how your work will affect the life of rpclib users in the
CHANGELOG file.

Please follow the `PEP 8 <http://www.python.org/dev/peps/pep-0008/>`_
style guidelines for both source code and docstrings.

We could also use help with the docs, which are built from
`restructured text <http://docutils.sourceforge.net/rst.html>`_ using
`Sphinx <http://sphinx.pocoo.org>`_.

Regular contributors may be invited to join as a core rpclib committer on
GitHub. Even if this gives the core committers the power to commit directly
to the core repository, we highly value code reviews and expect every
significant change to be committed via pull requests.

Submitting Pull Requests
------------------------

Github's pull-request feature is awesome, but
there's a subtlety that's not totally obvious for newcomers: If you continue
working on the branch that you used to submit a pull request, your commits will
"pollute" the pull request until it gets merged. This is not a bug, but a
feature -- it gives you the ability to address reviewers' concerns without
creating pull requests over and over again. So, if you intend to work on other
parts of rpclib after submitting a pull request, please do move your work to its
own branch and never submit a pull request from your master branch. This will
give you the freedom to continue working on rpclib while waiting for your pull
request to be reviewed.

