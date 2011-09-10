
Rpclib
======

About
-----

Rpclib is an unobstrusive Python library that helps you expose your APIs to a
wider audience via various Remote Procedure Call protocols and transports.

It currently supports the WSDL 1.1 interface definition standard, along with
SOAP 1.1 and the rest-minus-the-verbs HttpRpc protocol which can be
transported via HTTP or ZeroMQ in a both client or server architecture.

The source code is `here <https://github.com/arskom/rpclib>`.

Installing
----------

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
------------

The main developers of rpclib lurk in the official soap implementors forum
in python.org, `here <http://mail.python.org/mailman/listinfo/soap/>`.
That's mostly because rpclib is the continuation of soaplib, but also
because soap is an important part of rpclib.

If you wish to contribute to rpclib's development, create a personal fork
on GitHub.  When you are ready to push to the mainstream repository,
submit a pull request to bring your work to the attention of the core
committers. They will respond to review your patch and act accordingly.

To save both parties time, make sure the existing tests pass. If you are
adding new functionality or fixing a bug, please have the accompanying test.
This will both help us increase test coverage and insure your use-case
is immunte to feature code changes. You could also summarize in one or
two lines how your work will affect the life of rpclib users in the
CHANGELOG file.

Please follow the `PEP 8 <http://www.python.org/dev/peps/pep-0008/>`
style guidelines for both source code and docstrings.

We could also use help with the docs, which are built from reStructureText
using Sphinx.

Regular contributors may be invited to join as a core rpclib committer on
GitHub. Even if this gives the core committers the power to commit directly
to the core repository, we highly value code reviews and expect every
significant change to be committed via pull requests.


Contents:
---------

.. toctree::
   :maxdepth: 2

   tutorial/index
   #reference/index
   #pages/serializers
   #pages/binaryfiles
   #pages/hooks
   #pages/serializer_api
   #pages/soap
   #pages/wsgi
   #pages/service

Frequently Asked Questions
--------------------------
.. toctree::
   :maxdepth: 2

   pages/faq

Change Log
----------
.. toctree::
   :maxdepth: 2

   pages/changelog


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

