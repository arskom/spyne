
Overview
========

What is soaplib?
----------------

Soaplib is an easy to use python library for publishing soap web services
using WSDL 1.1 standard, and answering SOAP 1.1 requests.
With a very small amount of code, soaplib allows you to write
a useful web service and deploy it as a [WSGI](http://wsgi.org/wsgi) application.

The official soaplib discussion forum can be found [here](http://mail.python.org/mailman/listinfo/soap).

The legacy versions of soaplib are also available in this repository. 
See [here](http://github.com/arskom/soaplib/tree/0_8) for the stable soaplib-0.8 branch. 
See [here](http://github.com/arskom/soaplib/tree/1_0) for the stable soaplib-1.0 branch.

See the [downloads section](http://github.com/arskom/soaplib/downloads) for related downloads.

Features
--------
* Deploy services as WSGI applications
* Handles all xml (de)serialization
* On-demand WSDL generation
* Powerful customization features to support many use-cases
* Doesn't get in your way!!!

Runtime Requirements
--------------------
* Python 2.4 or greater
* A WSGI-compliant web server (CherryPy, WSGIUtils, Twisted, etc.)
* [lxml](http://codespeak.net/lxml/) (available through easy_install)
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
