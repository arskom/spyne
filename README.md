
NOTE: This fork of soaplib is experimental. Use at your own risk.

Overview
========

What is soaplib?
----------------

Soaplib is an easy to use python library for publishing soap web services
using WSDL 1.1 standard, and answering SOAP 1.1 requests.
With a very small amount of code, soaplib allows you to write
a useful web service and deploy it as a WSGI application. WSGI is a python
web standard for writing portable, extendable web applications in python.
More information on WSGI can be found [here](http://wsgi.org/wsgi).

Features
--------
* deploy services as WSGI applications
* handles all xml (de)serialization
* on-demand WSDL generation
* doesn't get in your way!!!

Requirements
------------
* Python 2.4 or greater (tested mainly on 2.4.3)
* [lxml](http://codespeak.net/lxml/) (available through easy_install)
* a WSGI-compliant web server (CherryPy, WSGIUtils, Flup, etc.)
* [pytz](http://pytz.sourceforge.net/)(available through easy_install)
* [easy_install](http://peak.telecommunity.com/dist/ez_setup.py) (optional)

Soaplib services can be deployed as WSGI applications, in any WSGI-compliant
web server. Soaplib services have been successfully run on the following web
servers:

* CherryPy 2.2
* Flup
* Twisted.web2
* WSGIUtils 0.9

