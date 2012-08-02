
Roadmap and Criticism
=====================

This is an attempt to make a free-for-all area to display opinions about the
feature direction of spyne. Doing it in a text file in the source repository
may not be the best approach for the job, but it should be enough to at least
spark a discussion around this topic.

So the following is missing in Spyne:

Serializer Support
------------------

See the :ref:`manual-highlevel` section for a small introductory paragraph about
serializers.

Currently, serializers are not distinguished in the spyne source code. Making
them pluggable would make it easy to share code between protocols.

An initial attempt to make them pluggable would result in the lxml dependency
for Soap being relaxed, which would make it possible to deploy spyne in
pure-python environments. However, this is comparatively easy to do, given
the fact that the ElementTree api is a well-known de-facto standard in the
Python world.

Adding other serializers like json to the mix would certainly be a nice
exercise in oo interface design, but this may be a solution in search of a
problem. Would anybody be interested using Soap over Json instead of Xml?
Probably not :)

It would, however, help newer serialization formats by reusing code from their
more mature cousins. E.g. Xml already has a well-defined security protocol
(XmlSec). If the serializer is abstracted away (and if somebody actually
implements XmlSec in spyne) it could be easier to port security code from
XmlObject to JsonObject.

Miscellanous
------------

The following would definitely be nice to have, but are just modules that should
not cause a change in unrelated areas of spyne. Those would increment the minor
version number of the Spyne version once implemented.

* Support for polymorphism in XML Schema.
* Support for the JsonRpc protocol.
* Support for the JsonSchema interface document standard.
* Support for the Thrift binary protocol.
* Support for the Thrift IDL -- The Thrift Interface Definition Language.
* Support for the XmlRpc standard.
* Support for EXI -- The Efficient Xml Interchange as a serializer.
* SMTP as client/server transport.
* SPDY as client/server transport.
* Implement converting csv output to pdf.
* Support security extensions to Soap (maybe using `PyXMLSec <http://pypi.python.org/pypi/PyXMLSec/0.3.0>`_ ?)
* Support addressing (routing) extensions to Soap
* Add WSDL Parsing support to Soap client
* Reflect transport and protocol pairs other than Soap/Http to the Wsdl.
* etc.
