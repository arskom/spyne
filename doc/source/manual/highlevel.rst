
.. _manual-highlevel:

High-Level Introduction to Spyne
=================================

The impatient can just jump to the :ref:`manual-highlevel-nutshell` section,
or read a small
`presentation <http://arskom.github.com/spyne/multiple_protocols_presentation.pdf>`_
that illustrates the following concepts by examples.

Concepts
--------

The following is a quick introduction to the Spyne way of naming things:

* **Protocols:**
    Protocols define the rules for transmission of structured data. They are
    children of :class:`spyne.protocol._base.ProtocolBase` class. In an MVC
    world, you would call them "Views".

    For example: Spyne implements a subset of the Soap 1.1 protocol.

* **Transports:**
    Transports, also protocols themselves, encapsulate protocol data in their
    free-form data sections. They are subclasses of either
    :class:`spyne.client._base.ClientBase` or
    :class:`spyne.server._base.ServerBase` classes.

    For example, Http is used as a transport for Soap, by
    tucking a Soap message in the arbitrary byte-stream part of a Http POST
    request. The same Http is exposed as a protocol via the
    :class:`spyne.protocol.http.HttpRpc`
    class. One could use Soap as a transport by tucking a protocol message in
    its base64-encoded ByteArray container.

    Transports appear under two packages in Spyne source code:
    :mod:`spyne.client` and :mod:`spyne.server`.

* **Models:**
    Models are used to define schemas. They are mere magic cookies that contain
    very little amount of serialization logic. They are subclasses of
    :class:`spyne.model._base.ModelBase`.

    Types like ``Unicode``, ``Integer`` or ``ByteArray`` are all models. They
    reside in the :mod:`spyne.model` package.

* **Interface Documents:**
    Interface documents provide a machine-readable description of the expected
    input and output of the exposed method calls. Thus, they have pretty much
    the same purpose as a method signature in a programming language. They are
    subclasses of :class:`spyne.interface.base.InterfaceDocumentBase`.

    :mod:`spyne.interface` package is where you can find them.

* **Serializers:**
    Serializers are currently not distinguished in Spyne code. They are the
    protocol-specific representations of a serialized Python object.

    They can be anything between an lxml.etree.Element instance to a gzipped
    byte stream. Apis around pickle, simplejson, YaML and the like that serialize
    dynamic hieararchies of `dict`s also fall in this category.

How your code is wrapped
------------------------

While the information in the previous section gave you an idea about how Spyne
code is organized, this section is supposed to give you an idea about how *you*
should organize your code using the tools provided by Spyne.

Before proceeding further, having good idea about the following four terms used
throughout Spyne would be very useful:

* **User Methods** or **User Code**:
    User methods are the code that you wrote and decided to use spyne to
    expose to the outside world.

* **Decorators**:
    The ``@rpc`` and ``@srpc`` decorators from :mod:`spyne.decorator` module
    are used to flag methods that will be exposed to the outside world by
    marking their input and output types, as well as other properties.

* **Service Definition**:
    The :class:`spyne.service.ServiceBase` is an abstract base class for
    service definitions, which are the smallest exposable unit in Spyne.
    You can use one service class per method definition or you can use, say, a
    service class for read-only or read/write services or you can cram
    everything into one service class, it's up to you.

    Service definition classes are suitable for grouping services that have
    common properties like logging, transaction management and security policy.
    It's often a good idea to use your own ServiceBase subclass where such
    common operations are added via events instead of using the vanilla
    ``ServiceBase`` class offered by Spyne.

* **Application**:
    The :class:`spyne.application.Application` class is what ties services
    and protocols together, ready to be wrapped by a transport.

    It also lets you define events and hooks like you can with the `ServiceBase`
    class, so you can do more general, application-wide customizations like
    exception management.

    .. NOTE::
        You may know that spyne is a generalized version of a soap library.
        So inevitably, some artifacts of the Soap world creep in from here and
        there.

        One of those artifacts is the namespace feature of Xml. There are
        varying opinions about the usefulness of Xml namespaces, but as we think
        it's generally "A Nice Thing", we chose to keep it around.

        When instantiating the :class:`spyne.application.Application` class,
        you should also give it a targetNamespace (the ``tns`` argument to its
        constructor) string and an optional application name (the ``name``
        argument to the :class:`Application` constructor), which are used to
        generally distinguish your application from other applications
        *in the universe*.

        While it's conventionally the URL and the name of the class of your
        application, you can put ``tns="Hogwarts", name="Harry"`` there and
        just be done with it.

        Every object in the Spyne world has a name and belongs to a namespace.
        Public functions (and the implicit :class:`spyne.model.complex.ComplexModel`
        children that are created for the input and output types of the
        functions you defined) are forced to be in the tns of the `Application`
        and have whatever you give them as `public_name` in the
        :func:`spyne.decorator.srpc` decorator. Spyne-defined types generally
        belong to a pre-defined namespace by default. User-defined objects
        have the module name as namespace string and class name as name string
        by default.

.. _manual-highlevel-nutshell:

In a nutshell
^^^^^^^^^^^^^^

Your code is inside @rpc-wrapped methods in `ServiceBase` subclasses. The
`ServiceBase` subclasses in turn are wrapped by an Application instance. The
`Application` instantiation is used to assign input and output protocols to the
exposed methods. The `Application` is finally wrapped by a client or server
transport that takes the responsibility of moving the bits around.

In case you'd like to read about how *exactly* your code is wrapped, you can
refer to the relevant part in the :ref:`manual-t-and-p` section.

What's next?
------------

Now that you have a general idea about how Spyne is supposed to work, let's get
coding. You can start by :ref:`manual-helloworld` tutorial right now.
