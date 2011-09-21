
.. _manual-comparison:

Comparison with other rpc frameworks
====================================

Ladon
-----

The Ladon project has almost the same goals and same approach to the rpc-related
issues.

Discussion thread: https://answers.launchpad.net/ladon/+question/171664

* Supports JsonWSP protocol, which rpclib does not support.
    The main motive for designing JSON-WSP was the need for a JSON-based RPC
    protocol with a service description specification with built-in service /
    method documentation.
* Supports Python 3.x.
* Auto-generates human-readable API documentation.
  (example: http://ladonize.org/python-demos/AlbumService) In Rpclib, you need
  to do with the ugliness of a raw wsdl document.
* Supports both Python 2 and Python 3
* Serves up all protocols at once on same port (see the example above)
* Makes string encoding operations easy (You can control on method level whether
  you want all strings delivered as unicode or as str in a specific encoding)
* Does not support ZeroMQ.
* Uses standard python tools for xml parsing which is good for pure-python
  deployments. Rpclib uses lxml, due to its excellent namespace support and
  speed. So Rpclib-based solutions are easier to develop, faster to work with
  but more difficult to deploy.
* Does not do input validation for SOAP.
* Does not support events.
* Does not support HttpRpc.
* Does not have a Soap client.
    In fact, Ladon is pure server-side software - the whole idea of supporting a
    standard protocol like SOAP is that clients are already out there.
* Rpclib uses own classes for denoting types, whereas ladon uses python
  callables. This lets ladon api to be simpler, but gives the rpclib api the
  power to have declarative restrictions on input types.
* Does not test against ws-i.org deliverables for testing soap compatibility.
* Does not support modifying protocol & transport headers.
