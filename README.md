Overview
========

What is soaplib?
----------------

Soaplib is an easy to use python library for publishing soap web services
using WSDL 1.1 standard, and answering SOAP 1.1 requests.
With a very small amount of code, soaplib allows you to write
a useful web service and deploy it as a WSGI application.

WSGI is a python web standard for writing portable, extendable web
applications in python. More information on WSGI can be found [here](http://wsgi.org/wsgi).

The official soaplib discussion forum can be found [here](http://mail.python.org/mailman/listinfo/soap).

Features
--------
* deploy services as WSGI applications
* handles all xml (de)serialization
* on-demand WSDL generation
* doesn't get in your way!!!

Runtime Requirements
--------------------
* Python 2.4 or greater
* [lxml](http://codespeak.net/lxml/) (available through easy_install)
* a WSGI-compliant web server (CherryPy, WSGIUtils, Flup, etc.)
* [pytz](http://pytz.sourceforge.net/) (available through easy_install)

Soaplib services can be deployed as WSGI applications, in any WSGI-compliant
web server. See the examples directory in the source distribution for deployment
examples. Soaplib services have been successfully run on the following web
servers:

* CherryPy 2.2
* Flup
* twisted.web (8.2, 9.0)
* WSGIUtils 0.9

Development Requirements
------------------------
* Most examples and tests require Python 2.5 or greater
* Twisted is required for `soaplib.test.interop.server.basic` and `soaplib.test.interop.server.static`.
