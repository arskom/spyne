.. soaplib documentation master file, created by
   sphinx-quickstart on Sat May  8 09:26:12 2010.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

soaplib
===============

.. contents::
    :depth: 3

About
--------
Soaplib is an easy to use python library for publishing soap web services using
WSDL 1.1 standard, and answering SOAP 1.1 requests. With a very small amount of
code, soaplib allows you to write a useful web service and deploy it as a WSGI
application.

The official soaplib discussion forum can be found here.

The legacy versions of soaplib are also available in this repository. See here
for the stable soaplib-0.8 branch. See here for the stable soaplib-1.0 branch.


Installing
-------------
To install soaplib, you can use git to clone from github or install from pypi.

git clone git://github.com/arskom/soaplib.git
cd soaplib

python setup.py install

# if you want to make any changes to the soaplib code, use:

python setup.py develop

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


Server
--------
.. toctree::
   :maxdepth: 2

   pages/server


Client
---------
.. toctree::
   :maxdepth: 2

   pages/client


Service
---------

.. toctree::
   :maxdepth: 2

   pages/service


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

