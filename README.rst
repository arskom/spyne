
Warning! This is from rpclib's unstable development branch.

About
=====

Rpclib is an unobstrusive Python library that helps you expose your APIs to a
wider audience via various remote procedure call protocols and transports.

It currently supports the WSDL 1.1 interface definition standard, along with
SOAP 1.1 and the rest-minus-the-verbs HttpRpc protocols which can be
transported via HTTP or ZeroMQ in a both client or server environment.

The source code is `here <https://github.com/arskom/rpclib>`_.

The official rpclib discussion forum can be found `here <http://mail.python.org/mailman/listinfo/soap>`_.

See the `downloads section <http://github.com/arskom/rpclib/downloads>`_ for related downloads.

The documentation is `here <http://arskom.github.com/rpclib>`_.

Rpclib is a generalized version of a soap processing library known as soaplib.
The following legacy versions of soaplib are also available:

 * See `here <http://github.com/arskom/rpclib/tree/soaplib-0_8>`_ for the stable soaplib-0.8 branch.
 * See `here <http://github.com/arskom/rpclib/tree/soaplib-1_0>`_ for the stable soaplib-1.0 branch.
 * See `here <http://github.com/arskom/rpclib/tree/soaplib-2_0>`_ for the stable soaplib-2.0 branch.

Requirements
============

Rpclib reportedly runs on any version of Python from 2.4 through 2.7. We're also
looking for volunteers to test Python 3.x.

The aim is to have no requirements besides the standard Python library for the
Rpclib core. While much progress was made towards this goal, there's still some
work to be done. So currently, the following is needed if you want to run any
Rpclib service at all:

* `lxml <http://codespeak.net/lxml/>`_. (available through easy_install)
* `pytz <http://pytz.sourceforge.net/>`_. (available through easy_install)

And the following is needed for various subsystems that Rpclib supports:

* `SQLAlchemy <http://sqlalchemy.org>`_ for :class:`rpclib.model.table.TableModel`.
* `pyzmq <https://github.com/zeromq/pyzmq>`_ for
  :class:`rpclib.client.zeromq.ZeroMQClient` and
  :class:`rpclib.server.zeromq.ZeroMQServer`.
* A Wsgi server of your choice to wrap :class:`rpclib.server.wsgi.WsgiApplication`.

Please note that the examples assume Python 2.5 and up.

Installing
==========

To install rpclib, you can use git to clone from github or install from pypi::

    git clone git://github.com/arskom/rpclib.git
    cd rpclib
    python setup.py install

    # to run the non-interop tests use:
    python setup.py test

    # if you want to make any changes to the rpclib code, it's more comfortable
    # to use:
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
