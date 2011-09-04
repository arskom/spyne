
Warning! This is rpclib's unstable development branch. Not only that, but rpclib
project is experimental. You have been warned.

Overview
========

What is rpclib?
----------------

Rpclib is a library for publishing services that uses various protocols and
transports. Currently, it supports WSDL 1.1 interface to publish services
that use SOAP 1.1 or the (Rest-minus-the-verbs) HttpRPC protocol over either
ZeroMQ or HTTP (using WSGI).

With a very small amount of code, rpclib allows you to write a useful remote
procedure call pack and deploy it using your transport of choice.

The official rpclib discussion forum can be found [here](http://mail.python.org/mailman/listinfo/soap).

See the [downloads section](http://github.com/arskom/rpclib/downloads) for related downloads.

The documentation [here](http://arskom.github.com/rpclib)

Rpclib is a generalized version of a soap processing library known as soaplib.
The legacy versions of soaplib are also available in this repository.
See [here](http://github.com/arskom/rpclib/tree/soaplib-0_8) for the stable soaplib-0.8 branch.
See [here](http://github.com/arskom/rpclib/tree/soaplib-1_0) for the stable soaplib-1.0 branch.
See [here](http://github.com/arskom/rpclib/tree/soaplib-2_0) for the stable soaplib-2.0 branch.

Features
--------
* Handles all (de)serialization.
* On-demand WSDL generation.
* Powerful customization features to support many use-cases.

Runtime Requirements
--------------------
* Python 2.4 through 2.7 (looking for volunteers to test Python 3.x)
* A WSGI-compliant web server for http services. (CherryPy, WSGIUtils, Twisted, etc.)
* [lxml](http://codespeak.net/lxml/) for soap. (available through easy_install)
* [pytz](http://pytz.sourceforge.net/) (available through easy_install)

See the examples directory in the source distribution for deployment
examples. Rpclib services have been successfully run on the following web
servers:

* CherryPy 2.2
* Flup
* twisted.web (8.2, 9.0)
* WSGIUtils 0.9

Development Requirements
------------------------
* Most examples and tests require Python 2.5 and greater. You need Python 2.7 to
  run all of the tests.
* Twisted is required for `rpclib.test.interop.server.basic` and
  `rpclib.test.interop.server.static`.
* To run automated tests, see instructions under test/README
