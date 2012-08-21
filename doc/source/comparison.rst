.. _manual-comparison:

Comparison with other rpc frameworks
====================================

RPC is a very popular subject. There's a plethora of active and inactive
projects that satisfy a wide range of requirements. Here are the main sources
of information:

* http://pypi.python.org/pypi?%3Aaction=search&term=rpc
* http://www.ohloh.net/tags/python/rpc
* http://stackoverflow.com/questions/1879971/what-is-the-current-choice-for-doing-rpc-in-python

Ladon
-----

The Ladon project has almost the same goals and same approach to the rpc-related
issues as Spyne.

Discussion thread: https://answers.launchpad.net/ladon/+question/171664

* Supports JsonWSP protocol, which Spyne does not support.
    The main motive for designing JSON-WSP was the need for a JSON-based RPC
    protocol with a service description specification with built-in service /
    method documentation.
* Supports both Python 2 and Python 3.
* Auto-generates human-readable API documentation.
  (example: http://ladonize.org/python-demos/AlbumService) In Spyne, you need
  to do with the ugliness of a raw wsdl document.
* Does not support ZeroMQ.
* Uses standard python tools for xml parsing which is good for pure-python
  deployments. Spyne uses lxml, due to its excellent xml namespace support and
  speed. So Spyne-based solutions are easier to develop and faster to work with
  but more difficult to deploy.
* Does not do declarative input validation. Traditional (imperative) input
  validation is possible via a code injection mechanism similar to Spyne's
  events.
* Does not support HttpRpc.
* Does not have a Soap client.
    In fact, Ladon is pure server-side software - the whole idea of supporting a
    standard protocol like SOAP is that clients are already out there.
* Spyne uses own classes for denoting types, whereas ladon uses Python
  callables. This lets ladon api to be simpler, but gives the Spyne api the
  power to have declarative restrictions on input types.
* Does not test against ws-i.org deliverables for testing soap compatibility.
* Does not support parsing and/or modifying protocol & transport headers.

WSME
----

"""
Web Service Made Easy (WSME) is a very easy way to implement webservices in your
python web application. It is originally a rewrite of TGWebServices with focus
on extensibility, framework-independance and better type handling.
"""

* Supports TurboGears
* Supports REST+Json, REST+Xml, (a subset of) SOAP and ExtDirect.
* Supports type validation.
* No client support.
* Does not test against ws-i.org deliverables for testing soap compatibility.
* Only supports http as transport.
* Uses genshi for Xml support.

RPyC
----

This is preliminary. Please correct these points if you spot any error.

* Uses own protocol
* Does not do validation.
* Python-specific.
* Fast.
* Not designed for public servers. ??

rfoo
----

This is preliminary. Please correct these points if you spot any error.

* Uses own protocol
* Does not do validation.
* Python-specific.
* Fast.
* Not designed for public servers. ??


Suds
----

* Soap 1.1 / Wsdl 1.1 Client only.
* Excellent wsdl parser, very easy to use.
* Recommended way to interface with Spyne's Soap services.
* Uses own pure-python xml implementation, so it's roughly 10 times slower
  than Spyne's Soap client.
* Pure-python library, so relatively easier to deploy.

ZSI
---

* Unmaintained, although still works with recent Python versions
* Contains SOAPpy, which is not the same as SOAPy (notice the extra P)
* Supports attachments
* Requires code generation (wsdl2py) for complex data structures
* Almost complete lack of user-friendliness
* Lack of WSDL generator

SOAPy
------

* Really simple (only two files, both less than 500 lines of code)
* Client only
* Requires PyXML, thus unusable with recent Python versions

rsl
---

* Client only.
* Unmaintained.

PyRo
----

* Python Remote Objects
* ???
