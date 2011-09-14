
.. _manual-highlevel

High-Level Introduction to Rpclib 
=================================

Concepts
--------

Rpclib defines some concepts that was identified to be shared by all of the rpc
systems.

 * **Protocols:**
    Protocols define the transmission of structured data. Popular examples
    include Soap, Json, Thrift, etc. They can be found in the
    :module:`rpclib.protocol` package.

 * **Transports:**
    Transports, also protocols themselves, encapsulate protocols in their
    arbitrary-data sections. E.g. Http is used as a transport for Soap, by
    tucking a Soap message in the Http byte-stream. One could use Soap as a
    transport by tucking a message that adheres to a certain schema for a
    protocol in its base64-encoded ByteArray.

    Transports are separated to two packages in Rpclib source code: Client and
    server. They can be found in the :module:`rpclib.client` and
    :module:`rpclib.client` packages.

 * **Models:**
    Models are used to define schemas. They are mere magic cookies who contain
    very little amount of serialization code They reside in the
    :module:`rpclib.model` package.

 * **Interfaces:**
    Interface documents strive to serialize, in a portable fashion, what is
    normally stored inside a, say, C header file. It documents method calls,
    the kind of input expected by those method calls, and of course, the kind
    of output that should be expected as a result of calling those methods.

    Except for the obvious overheads involved with remote procedure call, the
    goal of the interface document is to make the remote procedure call as
    seamless as possible by documenting a rigorous definition of the exposed
    services.

    :module:`rpclib.interface` package is where you can find them.

 * **Serializers:**
    Serializers are currently not distinguished in rpclib code. They are mostly
    apis around hiearchical key-value stores. Various xml apis like
    ``lxml.etree.Element``, Python's own ``xml.etree.ElementTree``, or pickle,
    simplejson, YaML and the like fall in this category. They're a little bit
    more difficult to abstract away because each has their own strenghts and
    weaknesses when dealing with complex, hiearchical data with mixed types.

    An initial attempt to make them pluggable would result in the lxml dependency
    for Soap being relaxed, which would make it possible to deploy rpclib in
    pure-python environments. However, this is comparatively easy to do, given
    the fact that the ElementTree api is a well-known de-facto standard in the
    Python world.

    Adding other serializers like json to the mix would certainly be a nice
    excersize in interface design, but this may be a solution in search of a
    problem. Would anybody be interested using Soap over Json instead of Xml?
    Probably not :)

    It would, however, help newer serialization formats by reusing code from
    their more mature cousins. E.g. Soap already has a security layer defined.
    If the serializer is abstracted away, it'd be trivial to port security code
    from Soap to Json.

How your code is wrapped
------------------------

All this machinery is there to have your code inside a method in a ServiceBase
child have answer requests from anywhere around the world. This is all fine and
dandy, but how do those elements interact together? Let's answer that message by
looking at how a Soap message is processed:

**TO BE DONE**



