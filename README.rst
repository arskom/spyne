
Warning! This is from rpclib's unstable development branch.

*****
About
*****

Rpclib aims to save the protocol implementers the hassle of implementing their
own remote procedure call api and the application programmers the hassle of
jumping through hoops just to expose a service using multiple protocols and
transports.

Rpclib comes with the implementations of popular transports, protocols and
interface documents along with an easy-to-use API that lets you extend existing
functionality. It currently supports the WSDL 1.1 interface definition standard,
along with SOAP 1.1 and the rest-minus-the-verbs HttpRpc protocols which can be
transported mainly via HTTP. We also support ZeroMQ tranport where appropriate.
The transports can be used in a both client or server environment.

The documentation for Rpclib can be found `here <http://arskom.github.com/rpclib>`_.

The source code is `here <https://github.com/arskom/rpclib>`_.

The official rpclib discussion forum can be found `here <http://mail.python.org/mailman/listinfo/soap>`_.

See the `downloads section <http://github.com/arskom/rpclib/downloads>`_ for related downloads.

Rpclib is a generalized version of a soap processing library known as soaplib.
The following legacy versions of soaplib are also available:

 * See `here <http://github.com/arskom/rpclib/tree/soaplib-0_8>`_ for the stable soaplib-0.8 branch.
 * See `here <http://github.com/arskom/rpclib/tree/soaplib-1_0>`_ for the stable soaplib-1.0 branch.
 * See `here <http://github.com/arskom/rpclib/tree/soaplib-2_0>`_ for the stable soaplib-2.0 branch.

************
Requirements
************

Rpclib reportedly runs on any version of Python from 2.4 through 2.7. We're also
looking for volunteers to test Python 3.x.

Our aim is to have no requirements besides the standard Python library for the
Rpclib core. While much progress was made towards this goal, there's still some
work to be done. So currently, the following is needed if you want to run any
Rpclib service at all:

* `lxml <http://codespeak.net/lxml/>`_
* `pytz <http://pytz.sourceforge.net/>`_

both of which are available through ``easy_install``.

And the following is needed for various subsystems that Rpclib supports:

* `SQLAlchemy <http://sqlalchemy.org>`_ for :class:`rpclib.model.table.TableModel`.
* `pyzmq <https://github.com/zeromq/pyzmq>`_ for
  :class:`rpclib.client.zeromq.ZeroMQClient` and
  :class:`rpclib.server.zeromq.ZeroMQServer`.
* A Wsgi server of your choice to wrap :class:`rpclib.server.wsgi.WsgiApplication`.

**********
Installing
**********

To install rpclib, you can use git to clone from github or install from pypi::

    git clone git://github.com/arskom/rpclib.git

and run its setup script as usual: ::

    cd rpclib
    python setup.py install

To run the non-interop tests use: ::

    python setup.py test

And if you want to make any changes to the rpclib code, it's more comfortable to use: ::

    python setup.py develop

************
Contributing
************

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
