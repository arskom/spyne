Overview
========

What is soaplib?
----------------

Soaplib is an easy to use python library for publishing soap web services
using WSDL 1.1 standard, and answering SOAP 1.1 requests.
With a very small amount of code, soaplib allows you to write
a useful web service and deploy it as a [WSGI](http://wsgi.org/wsgi) application.

The official soaplib discussion forum can be found [here](http://mail.python.org/mailman/listinfo/soap).

The legacy 0.8.x version of soaplib is also available in [this](http://github.com/arskom/soaplib/tree/0_8) github repository.

See the [downloads section](http://github.com/arskom/soaplib/downloads) for related downloads.

Features
--------
* Deploy services as WSGI applications
* Handles all xml (de)serialization
* On-demand WSDL generation
* Powerful customization features that supports many use-cases.
* doesn't get in your way!!!

Runtime Requirements
--------------------
* Python 2.4 or greater
* a WSGI-compliant web server (CherryPy, WSGIUtils, Flup, etc.)
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
