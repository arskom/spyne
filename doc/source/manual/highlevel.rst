
.. _manual-highlevel:

High-Level Introduction to Rpclib
=================================

The impatient can just jump to the :ref:`manual-highlevel-nutshell` section.

Concepts
--------

The following is most of the Rpclib jargon:

* **Protocols:**
    Protocols define the rules for transmission of structured data. E.g., Rpclib
    implements a subset of Soap 1.1 protocol.

* **Transports:**
    Transports, also protocols themselves, encapsulate protocol data in their
    free-form data sections. E.g. Http is used as a transport for Soap, by
    tucking a Soap message in the Http byte-stream part of a Http POST request.
    The same Http is exposed as a "protocol" using the :class:`rpclib.protocol.http.HttpRpc`
    class. One could use Soap as a transport by tucking a protocol message in its
    base64-encoded ByteArray container.

    Transports are separated to two packages in Rpclib source code:
    :mod:`rpclib.client` and :mod:`rpclib.server`.

* **Models:**
    Models are used to define schemas. They are mere magic cookies that contain
    very little amount of serialization code They reside in the
    :mod:`rpclib.model` package.

* **Interfaces:**
    Interface documents strive to serialize, in a portable fashion, the
    information that is normally stored inside a, say, C header file. It a rigorous
    fashion the method calls, the kind of input expected by those method calls and
    the kind of output that should be expected as a result of calling those methods.

    :mod:`rpclib.interface` package is where you can find them.

* **Serializers:**
    Serializers can be considered mostly as apis around hiearchical key-value
    stores. Various xml apis like ``lxml.etree.Element``, Python's own
    ``xml.etree.ElementTree``, or apis around pickle, simplejson, YaML and the like
    fall in this category. They're a little bit more difficult to abstract away because
    each has their own strenghts and weaknesses when dealing with complex, hiearchical
    data with mixed types.

    Serializers are currently not distinguished in rpclib code. lxml.etree is
    used as xml serializer, and a custom wsgi callable is used as http serializer.

How your code is wrapped
------------------------

A typical Rpclib user will just write methods that will be exposed as
remote procedure calls to the outside world. The following is used to wrap that
code:

* **Decorators**:
    the ``@rpc`` and ``@srpc`` decorators from :mod:`rpclib.decorator` module
    are used to flag methods that will be exposed to the outside world, along
    with marking its input and output types.

* **Service Definition**:
    The :class:`rpclib.service.ServiceBase` is an abstract base class for
    service definitions. It is the smallest exposable service unit in rpclib. You
    can use one service class per method definition or you can use, say, a service
    class for read-only or read/write services or you can cram everything into one
    service class, it's up to you.

    You can define events, header classes, and other goodies on service classes,
    which make them suitable for grouping services that have common properties like
    logging, transaction management, header objects and whatnot. It's often a good
    idea to base your application services your own ServiceBase children.

* **Application**:
    The :class:`rpclib.application.Application` object is what ties services,
    interfaces protocols together, ready to be wrapped by a transport. It also lets
    you define events and hooks like ServiceBase does, so you can do more general,
    application-wide customizations like exception management.

    .. NOTE:: You might know that rpclib is a generalized version of a
        soap library. So inevitably, some artifacts of the Soap world creep in
        from here and there.

        Namespaces are another artifact of the Xml world. There are varying
        opinions about the usefulness of the concept of the namespaces in Xml,
        but we generally think it to be A Nice Thing, so we chose to keep it
        around.

        When instantiating the :class:`rpclib.application.Application`, you should also
        give it a targetNamespace (the ``tns`` argument to its constructor)
        string and an optional application name (the ``name`` argument to the
        :class:`Application` constructor), which are used to generally distinguish your
        application from other applications. While it's conventionally the URL and
        the name of the class of your application, you can put
        ``tns="Hogwarts", name="Harry"`` there and just be done with it.

        Every object in the Rpclib world has a name and belongs to a namespace.
        Public functions (and the implicit :class:`rpclib.model.complex.ComplexModel`
        children that are created for the input and output types of the functions you
        defined) are forced to be in the Application namespace, and have whatever you
        give them as public name in the :func:`rpclib.decorator.srpc` decorator.
        Rpclib-defined types generally belong to the relevant Xml namespace by default.
        User-defined objects have the module name as namespace string and class name as
        name string by default.

.. _manual-highlevel-nutshell:

In a nutshell
^^^^^^^^^^^^^^

Your code is inside @rpc-wrapped methods in ServiceBase children, which are
grouped in an Application instance, which communicates with the outside world
using given interface and protocol classes, and which is finally wrapped by a
client or server transport that takes the responsibility of moving the bits
around.

What's next?
------------

Now that you have a general idea about how Rpclib is supposed to work, let's get
coding. You can start by :ref:`manual-helloworld` tutorial right now.
