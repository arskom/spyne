
.. _manual-highlevel:

High-Level Introduction to Rpclib
=================================

The impatient can just jump to the :ref:`manual-highlevel-nutshell` section,
or read a small
`presentation <http://arskom.github.com/rpclib/multiple_protocols_presentation.pdf>`_
that illustrates the following concepts by examples.

Concepts
--------

The following is a quick introduction to the Rpclib way of naming things:

* **Protocols:**
    Protocols define the rules for transmission of structured data. They are
    children of :class:`rpclib.protocol._base.ProtocolBase` class.

    For example: Rpclib implements a subset of the Soap 1.1 protocol.

* **Transports:**
    Transports, also protocols themselves, encapsulate protocol data in their
    free-form data sections. They are
    children of either :class:`rpclib.client._base.ClientBase` or
    :class:`rpclib.server._base.ServerBase` classes.

    For example, Http is used as a transport for Soap, by
    tucking a Soap message in the arbitrary byte-stream part of a Http POST
    request. The same Http is exposed as a "protocol" using the
    :class:`rpclib.protocol.http.HttpRpc`
    class. One could use Soap as a transport by tucking a protocol message in its
    base64-encoded ByteArray container.

    Transports appear under two packages in Rpclib source code:
    :mod:`rpclib.client` and :mod:`rpclib.server`.

* **Models:**
    Models are used to define schemas. They are mere magic cookies that contain
    very little amount of serialization logic. They are
    children of :class:`rpclib.model._base.ModelBase` class.

    Types like ``String``, ``Integer`` or ``ByteArray`` are all models. They
    reside in the
    :mod:`rpclib.model` package,

* **Interfaces:**
    Interface documents provide a machine-readable description of the input
    the services expect and output they emit. It thus serves a roughly similar
    purpose as a method signature in a programming language. They are
    children of :class:`rpclib.interface._base.InterfaceBase` class.

    :mod:`rpclib.interface` package is where you can find them.

* **Serializers:**
    Serializers are currently not distinguished in rpclib code. They are the
    protocol-specific representations of a serialized python object.

    They can be anything between an lxml.etree.Element instance to a gzipped
    byte stream. Apis around pickle, simplejson, YaML and the like also
    fall in this category.

How your code is wrapped
------------------------

While the information in the previous section gave you an idea about how Rpclib
code is organized, this section is supposed to give you an idea about how *you*
should organize your code using the tools provided by Rpclib.

A typical Rpclib user will just write methods that will be exposed as remote
procedure calls to the outside world. The following is used to wrap that
code:

* **User Methods**: User methods are the code that you wrote and decided to use
    rpclib to expose to the outside world.

* **Decorators**:
    the ``@rpc`` and ``@srpc`` decorators from :mod:`rpclib.decorator` module
    are used to flag methods that will be exposed to the outside world by
    marking their input and output types, as well as other properties.

* **Service Definition**:
    The :class:`rpclib.service.ServiceBase` is an abstract base class for
    service definitions, which are the smallest exposable service unit in rpclib.
    You can use one service class per method definition or you can use, say, a
    service class for read-only or read/write services or you can cram
    everything into one service class, it's up to you.

    Service definition classes are suitable
    for grouping services that have common properties like logging, transaction
    management and security policy. It's often a good idea to base your
    service definitions on your own ServiceBase children instead of using the
    vanilla ``ServiceBase`` class offered by Rpclib.

* **Application**:
    The :class:`rpclib.application.Application` class is what ties services,
    interfaces and protocols together, ready to be wrapped by a transport.
    It also lets you define events and hooks like ServiceBase does, so you can
    do more general, application-wide customizations like exception management.

    .. NOTE::
        You may know that rpclib is a generalized version of a
        soap library. So inevitably, some artifacts of the Soap world creep in
        from here and there.

        One of those artifacts is xml namespaces. There are varying
        opinions about the usefulness of the concept of the namespace in the
        Xml standard, but we generally think it to be A Nice Thing, so we chose
        to keep it around.

        When instantiating the :class:`rpclib.application.Application` class,
        you should also give it a targetNamespace (the ``tns`` argument to its
        constructor) string and an optional application name (the ``name``
        argument to the :class:`Application` constructor), which are used to
        generally distinguish your application from other applications. While
        it's conventionally the URL and the name of the class of your
        application, you can put ``tns="Hogwarts", name="Harry"`` there and
        just be done with it.

        Every object in the Rpclib world has a name and belongs to a namespace.
        Public functions (and the implicit :class:`rpclib.model.complex.ComplexModel`
        children that are created for the input and output types of the
        functions you defined) are forced to be in the Application namespace,
        and have whatever you give them as public name in the
        :func:`rpclib.decorator.srpc` decorator. Rpclib-defined types generally
        belong to a pre-defined namespace by default. User-defined objects
        have the module name as namespace string and class name as name string
        by default.

In case you'd like to read on how *exactly* your code is wrapped, you can refer
to the relevant part in the :ref:`manual-t-and-p` section.

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
