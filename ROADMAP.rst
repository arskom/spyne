
Roadmap and Criticism
=====================

This is an attempt to make a free-for-all area to display opinions about the
feature direction of rpclib. Doing it in a text file in the source repository
may not be the best tool for the job, but it should be enough to at least spark
a discussion around this topic.

Processing Pipeline
-------------------

We think rpclib package has one last missing element whose addition can result in
touching most of the codebase: A proper pipeline for request processing.

Currently, every artifact of the rpc processing pipeline remain in memory for the
life time of the context object. This also causes to have the whole message in
memory while processing. While this is not a problem for small messages, it
limits rpclib capabilities.

Serializer Support
------------------

Currently, serializers are not distinguished in the rpclib source code. Making
them pluggable would:

#. Make rpclib more flexible
#. Make it easy to share code between protocols.

Miscellanous
------------

The following are also nice and probably popular features to have, but are just
modules that should not cause a change in unrelated areas of rpclib. Those would
increment the minor revision number of the Rpclib version once implemented.

 * Support for a JsonObject and JsonRpc protocols.
 * Support for the JsonSchema interface document standard.
 * Support for the Thrift binary protocol.
 * Support for the Thrift IDL -- The Thrift Interface Definition Language.
 * Support for the XmlRpc standard. Thanks to the XmlObject protocol, this
   is 90% ready!
 * Support for EXI -- The Efficient Xml Interchange as a serializer.
 * SMTP as server tranport.
 * SMTP as client tranport.
 * Improve HttpRpc to be Rest compliant. Probably by dumping HttpRpc as it is
   and rewriting it as a wrapper to Werkzeug or a similar WSGI library.
 * Implement converting csv output to pdf.
 * Implement DNS as transport
 * Support security extensions to Soap (maybe using `PyXMLSec <http://pypi.python.org/pypi/PyXMLSec/0.3.0>`_ ?)
