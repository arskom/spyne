.. soaplib documentation master file, created by
   sphinx-quickstart on Sat May  8 09:26:12 2010.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

About
--------
Soaplib is an easy to use python library for publishing soap web services using
WSDL 1.1 standard, and answering SOAP 1.1 requests. With a very small amount of
code, soaplib allows you to write a useful web service and deploy it as a WSGI
application.

The official soaplib discussion forum/mailing list
is `here <http://mail.python.org/mailman/listinfo/soap/>`_


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
If you wish to contribute to soaplib's development simply create a personal fork
on github.  When you are ready to push to the repo simply submit a pull request.
For code changes make sure the existing test pass; if you are adding new
features please have accompanying test.


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
.. toctree::
   :maxdepth: 2

   pages/model_api


WSDL Reprensation
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

