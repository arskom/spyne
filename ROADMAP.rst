
Roadmap and Criticism
=====================

This is an attempt to make a free-for-all area to display opinions about the
feature direction of rpclib. Doing it in a text file in the source repository
may not be the best approach for the job, but it should be enough to at least spark
a discussion around this topic.

So the following is missing in Rpclib:

Processing Pipeline
-------------------

We think rpclib package has one last missing element whose addition can result in
touching most of the codebase: A proper pipeline for request processing.

Currently, every artifact of the rpc processing pipeline remain in memory for the
entire life time of the context object. This also causes to have the whole message
in memory while processing. While this is not a problem for small messages, which is
rpclib's main target, it limits rpclib capabilities.

Serializer Support
------------------

See the :ref:`manual-highlevel` section for a small introductory paragraph about
serializers.

Currently, serializers are not distinguished in the rpclib source code. Making
them pluggable would:

#. Make rpclib more flexible
#. Make it easy to share code between protocols.

An initial attempt to make them pluggable would result in the lxml dependency
for Soap being relaxed, which would make it possible to deploy rpclib in
pure-python environments. However, this is comparatively easy to do, given
the fact that the ElementTree api is a well-known de-facto standard in the
Python world.

Adding other serializers like json to the mix would certainly be a nice
exercise in oo interface design, but this may be a solution in search of a
problem. Would anybody be interested using Soap over Json instead of Xml?
Probably not :)

It would, however, help newer serialization formats by reusing code from their
more mature cousins. E.g. Soap already has a security layer defined. If the
serializer is abstracted away, it could be easier to port security code from
Soap to JsonRpc.

Miscellanous
------------

The following would definitely be nice to have, but are just modules that should
not cause a change in unrelated areas of rpclib. Those would increment the minor
version number of the Rpclib version once implemented.

* Currently, parameter validation is performed only by lxml's schema validator.
  Implement soft validation that'd work for any serializer for the primitives.
* Support for the JsonObject (a la XmlObject) and JsonRpc protocols.
* Support for the JsonSchema interface document standard.
* Support for the Thrift binary protocol.
* Support for the Thrift IDL -- The Thrift Interface Definition Language.
* Support for the XmlRpc standard. Thanks to the XmlObject protocol, this
  is 90% ready!
* Support for EXI -- The Efficient Xml Interchange as a serializer.
* SMTP as server transport.
* SMTP as client transport.
* Improve HttpRpc to be Rest compliant. Probably by dumping HttpRpc as it is
  and rewriting it as a wrapper to Werkzeug or a similar WSGI library.
* Implement converting csv output to pdf.
* Implement DNS as transport
* Support security extensions to Soap (maybe using `PyXMLSec <http://pypi.python.org/pypi/PyXMLSec/0.3.0>`_ ?)
* Support addressing (routing) extensions to Soap
* Add WSDL Parsing support to Soap client
* Reflect transport and protocol pairs other than Soap/Http to the Wsdl.
* Fix the tests that fail due to api changes.
