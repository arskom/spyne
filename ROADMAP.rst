
Roadmap and Criticism
=====================

This is an attempt to make a free-for-all area to display opinions about the
feature direction of spyne. Doing it in a text file in the source repository
may not be the best approach for the job, but it should be enough to at least
spark a discussion around this topic.

So the following is missing in Spyne:

Processing Pipeline
-------------------

We think spyne package has one last missing element whose addition can result
in touching most of the codebase: A proper lazily-evaluated pipeline for
request processing.

Currently, every artifact of the rpc processing pipeline remain in memory for the
entire life time of the context object. This also results in having the whole
message in memory while processing. While this is not a problem for small
messages, which is spyne's main target, it limits spyne capabilities.

A prerequisite of having such a lazy pipeline is to have ProtocolBase offer a
``.feed()`` call, which accepts data fragments coming in from socket stream.
Currently, spyne can only work with transports who support message semantics
-- i.e. those that offer a way of delimiting messages using without having to
parse the contents. While the most popular transports support this, it prevents
spyne from making use of low-level operating system primitives like tcp
sockets.

Serializer Support
------------------

See the :ref:`manual-highlevel` section for a small introductory paragraph about
serializers.

Currently, serializers are not distinguished in the spyne source code. Making
them pluggable would:

#. Make spyne more flexible
#. Make it easy to share code between protocols.

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
more mature cousins. E.g. Soap already has a security layer defined. If the
serializer is abstracted away, it could be easier to port security code from
Soap to JsonRpc.

Models need (yet another) overhaul
----------------------------------

Spyne should rely less on a class inheriting from ModelBase and more on a
class having a predetermined attribute (like _type_info). The ComplexModel
metaclass should just be responsible for filling out this information if it's
not already there (which is mostly the case now) and other parts of spyne
should rely on this *one* class attribute to do all (de)serialization and
constraint checking.

When you call :func:``customize`` function on a ModelBase child, a shallow
copy of that class definition is created. While this works great if the class
does not leave spyne code, (simply because spyne also looks for
spyne-specific ``_is_clone_of`` attribute to match classes) it turned out that
this is not what libraries that make heavy use of Python's powerful
metaprogramming features (like SQLAlchemy) expect. So the way Spyne breaks
the "is" operator hinders Spyne's interoperability prospects with other
libraries.

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
* WebSockets as client/server transport.
* Implement converting csv output to pdf.
* Implement DNS as transport
* Support security extensions to Soap (maybe using `PyXMLSec <http://pypi.python.org/pypi/PyXMLSec/0.3.0>`_ ?)
* Support addressing (routing) extensions to Soap
* Add WSDL Parsing support to Soap client
* Reflect transport and protocol pairs other than Soap/Http to the Wsdl.
