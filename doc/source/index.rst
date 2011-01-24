.. soaplib documentation master file, created by
   sphinx-quickstart on Sat May  8 09:26:12 2010.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

About
--------
Soaplib is an easy to use Python library for publishing SOAP web services using
WSDL 1.1 standard, and answering SOAP 1.1 requests. With a very small amount of
code, soaplib allows you to write a useful web service and deploy it as a WSGI
application. (Non-WSGI scenarios are also supported.)

Public discussion about soaplib can be found on the `Python general SOAP mailing
list <http://mail.python.org/mailman/listinfo/soap/>`_.

The source code is `here <https://github.com/soaplib/soaplib>`_.

The legacy versions of soaplib are also available in this repository.

See `here <https://github.com/soaplib/soaplib/tree/0_8>`_ for the soaplib-0.8 branch.

See `here <https://github.com/soaplib/soaplib/tree/1_0>`_ for the soaplib-1.0 branch.


Installing
-------------
To install soaplib, you can use git to clone from github or install from pypi.

git clone git://github.com/soaplib/soaplib.git

cd soaplib

python setup.py install

# to run the non-interop tests use:

python setup.py test

# if you want to make any changes to the soaplib code, use:

python setup.py develop


Contributing
--------------
If you wish to contribute to soaplib's development, create a personal fork
on GitHub.  When you are ready to push to the repo, submit a pull request,
and one of the core committers will review and respond.

For code changes make sure the existing tests pass; if you are adding new
features please have accompanying test. Of course, we're also interested in
increasing test coverage, so new tests are especially welcome!

Please follow the `PEP 8 <http://www.python.org/dev/peps/pep-0008/>`_
style guidelines for both source code and docstrings.

We could also use help with the docs, which are built from reStructureText
using Sphinx. It's easy to learn, and if you need help getting started,
contact us on the `mailing list <http://mail.python.org/mailman/listinfo/soap/>`_
and we'll help.

Regular contributors may be invited to join the soaplib organization on GitHub.
This provides a way for multiple contributors to commit to the same repository,
with no need for pull requests. It also provides stable home for the soaplib
repository, despite any "changing of the guard" as team members join and
leave the project.


History
-----------
.. toctree::
   :maxdepth: 2

   pages/changelog


Examples
----------

.. toctree::
   :maxdepth: 2
   
   pages/helloworld
   pages/usermanager
   pages/serializers
   pages/binaryfiles
   pages/message_api
   pages/hooks
   pages/apache_axis


Model API
------------
The soaplib.model API provides an elegant way of declaring within Python classes
the XML Schema (W3C) elements which make up a WSDL. This can also be used to
produce generic XSD for non-SOAP applications.

.. toctree::
   :maxdepth: 2

   pages/model_api


WSDL Representation
-------------------
.. toctree::
    :maxdepth: 2

    pages/wsdl

Server
--------
.. toctree::
   :maxdepth: 2

   pages/server


Service
---------

.. toctree::
   :maxdepth: 2

   pages/service


Application
-------------
.. toctree::
    :maxdepth: 2

    pages/application


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

