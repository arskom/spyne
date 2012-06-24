
Changelog
=========

rpclib-2.8.0-rc -> spyne-2.8.0-rc
---------------------------------
 * Rpclib is dead. Long live Spyne!
 * Add support for JsonObject protocol.
 * Make DateTime string format customizable.
 * Implement the server transport that exposes ``Application`` as a
   ``twisted.web.resource.Resource`` child.
 * Remove Deprecated XMLAttribute and XMLAttributeRef. Use ``XmlAttribute``
   and ``XmlAttributeRef`` instead.
 * Xml Schema: Add support for the <any> tag.
 * Add a chapter about Validation to the manual.
 * Interface documents are no longer subclasses of InterfaceBase. It's up
   to the transport to expose the application using a given interface document
   standard now. The ``interface`` argument to the ``Application`` ctor is
   now ignored.
 * Html: Added a very simple lxml-based templating scheme called _HtmlPage.
 * Html: Added row-based tables: They show fields in rows. It's good for
   showing one object per table.
 * Html: Added ImageUri support. They now render as <img> tags.
 * Html: Added support for locales. You can now render field names as human
   readable strings.
 * Add support for async methods, which execute after the primary user code
   returns. Currently, the only async execution method is via threads.
 * Xml & friends: Start tags are now in the same namespace as the definitions
   themselves. Intermediate tags are in the parent's namespace, just as before.
 * Xml & friends: Make the 'bare' mode work.
 * rpclib.util.xml: :func:`get_object_as_xml` can also get class suggestion.
 * rpclib.util.xml: :func:`get_xml_as_object` has argument order swapped:
   cls, elt -> elt, cls. See ab91a3e2ad4756b71d1a2752e5b0d2af8551e061.
 * Relevant pull requests:
    * https://github.com/arskom/spyne/pull/128
    * https://github.com/arskom/spyne/pull/129
    * https://github.com/arskom/spyne/pull/133
    * https://github.com/arskom/spyne/pull/137
    * https://github.com/arskom/spyne/pull/138
    * https://github.com/arskom/spyne/pull/139
    * https://github.com/arskom/spyne/pull/141
    * https://github.com/arskom/spyne/pull/142
    * https://github.com/arskom/spyne/pull/144
    * https://github.com/arskom/spyne/pull/146
    * https://github.com/arskom/spyne/pull/145

rpclib-2.7.0-beta
-----------------
 * Add support for non-chunked encoding to Wsgi transport.
 * Add support for Html Microformats.
 * Add ``function`` property to MethodContext that is re-initialized from
   ``descriptor.function`` for each new request. Stay away from
   ``descriptor.function`` unless you understand the consequences!..
 * String and Unicode models are now separate objects with well-defined
   (de)serialization behaviour.
 * Argument order change in Application ctor:

       interface, in_protocol, out_protocol

   becomes:

       in_protocol, out_protocol, interface

   See here: https://github.com/arskom/spyne/commit/45f5af70aa826640008222bda96299d51c9df980#diff-1

 * Full changelog:
     * https://github.com/arskom/spyne/pull/123
     * https://github.com/arskom/spyne/pull/124
     * https://github.com/arskom/spyne/pull/125

rpclib-2.6.1-beta
-----------------
 * Fix (for real this time) the race condition in wsgi server's wsdl handler.

rpclib-2.6.0-beta
-----------------
 * HttpRpc now parses POST/PUT/PATCH bodies, can accept file uploads.
   Uses werkzeug to do that, which is now a soft dependency.
 * ByteArray now child of SimpleModel. It's now possible to customize it simply
   by calling it.
 * Fix race condition in wsgi server wsdl request.
 * Full change log: https://github.com/arskom/spyne/pull/122

rpclib-2.5.2-beta
-----------------
 * Misc. fixes.
 * Full change log: https://github.com/arskom/spyne/pull/118

rpclib-2.5.1-beta
-----------------
 * Switched to magic cookie constants instead of strings in protocol logic.
 * check_validator -> set_validator in ProtocolBase
 * Started parsing Http headers in HttpRpc protocol.
 * HttpRpc now properly validates nested value frequencies.
 * HttpRpc now works with arrays of simple types as well.
 * Full change log: https://github.com/arskom/spyne/pull/117
                    https://github.com/arskom/spyne/pull/116

rpclib-2.5.0-beta
-----------------
 * Implemented fanout support for transports and protocols that can handle
   that.
 * Implemented a helper module that generates a Soap/Wsdl 1.1 application in
   ``rpclib.util.simple``
 * Some work towards supporting Python3 using ``2to3``. See issue #113.
 * ``ctx.descriptor.reset_function`` implemented. It's now safe to fiddle
   with that value in event handlers.
 * Incorporated a cleaned-up version of the Django wrapper: https://gist.github.com/1316025
 * Fix most of the tests that fail due to api changes.
 * Fix Http soap client.
 * Full change log: https://github.com/arskom/spyne/pull/115

rpclib-2.4.7-beta
-----------------
 * Made color in logs optional
 * Fixed ByteArray serializer

rpclib-2.4.5-beta
-----------------
 * Time primitive was implemented.
 * Fix for multiple ports was integrated.
 * Added http cookie authentication example with suds.
 * Full change log: https://github.com/arskom/spyne/pull/109

rpclib-2.4.3-beta
-----------------
 * Many issues with 'soft' validation was fixed.
 * ``MethodDescriptor.udp`` added. Short for "User-Defined Properties", you can
   use it to store arbitrary metadata about the decorated method.
 * Fix HttpRpc response serialization.
 * Documentation updates.

rpclib-2.4.1-beta
-----------------
 * Fixed import errors in Python<=2.5.
 * A problem with rpclib's String and unicode objects was fixed.

rpclib-2.4.0-beta
-----------------
 * Fixed Fault publishing in Wsdl.
 * Implemented 'soft' validation.
 * Documentation improvements. It's mostly ready!
 * A bug with min/max_occurs logic was fixed. This causes rpclib not to send
   null values for elements with min_occurs=0 (the default value).
 * Native value for ``rpclib.model.primitive.String`` was changed to
   ``unicode``. To exchange raw data, you should use
   ``rpclib.model.binary.ByteArray``.
 * Full change log: https://github.com/arskom/spyne/pull/90

rpclib-2.3.3-beta
-----------------
 * Added MAX_CONTENT_LENGTH = 2 * 1024 * 1024 and BLOCK_LENGTH = 8 * 1024
   constants to rpclib.server.wsgi module.
 * rpclib.model.binary.Attachment is deprecated, and is replaced by ByteArray.
   The native format of ByteArray is an iterable of strings.
 * Exception handling was formalized. HTTP return codes can be set by exception
   classes from rpclib.error or custom exceptions.
 * Full change log: https://github.com/arskom/spyne/pull/88

rpclib-2.3.2-beta
-----------------
 * Limited support for sqlalchemy.orm.relationship (no string arguments)
 * Added missing event firings.
 * Documented event api and fundamental data structures (rpclib._base)
 * Full change log: https://github.com/arskom/spyne/pull/87

rpclib-2.3.1-beta
-----------------
 * HttpRpc protocol now returns 404 when a requested resource was not found.
 * New tests added for HttpRpc protocol.
 * Miscellanous other fixes. See: https://github.com/arskom/spyne/pull/86

rpclib-2.3.0-beta
-----------------
 * Documentation improvements.
 * rpclib.protocol.xml.XmlObject is now working as out_protocol.
 * Many fixes.

rpclib-2.2.3-beta
------------------
 * Documentation improvements.
 * rpclib.client.http.Client -> rpclib.client.http.HttpClient
 * rpclib.client.zeromq.Client -> rpclib.client.zeromq.ZeroMQClient
 * rpclib.server.zeromq.Server -> rpclib.server.zeromq.ZeroMQServer
 * rpclib.model.table.TableSerializer -> rpclib.model.table.TableModel

rpclib-2.2.2-beta
-----------------
 * Fixed call to rpclib.application.Application.call_wrapper
 * Fixed HttpRpc server transport instantiation.
 * Documentation improvements.

rpclib-2.2.1-beta
-----------------
 * rpclib.application.Application.call_wrapper introduced
 * Documentation improvements.

rpclib-2.2.0-beta
-----------------

 * The serialization / deserialization logic was redesigned. Now most of the
   serialization-related logic is under the responsibility of the ProtocolBase
   children.
 * Interface generation logic was redesigned. The WSDL logic is separated to
   XmlSchema and Wsdl11 classes. 'add_to_schema' calls were renamed to just
   'add' and were moved inside rpclib.interface.xml_schema package.
 * Interface and Protocol assignment of an rpclib application is now more
   explicit. Both are also configurable during instantion. This doesn't mean
   there's much to configure :)
 * WS-I Conformance is back!. See https://github.com/arskom/spyne/blob/master/src/rpclib/test/interop/wsi-report-rpclib.xml
   for the latest conformance report.
 * Numeric types now support range restrictions. e.g. Integer(ge=0) will only
   accept positive integers.
 * Any -> AnyXml, AnyAsDict -> AnyDict. AnyAsDict is not the child of the AnyXml
   anymore.
 * rpclib.model.exception -> rpclib.model.fault.

rpclib-2.1.0-alpha
------------------

 * The method dispatch logic was rewritten: It's now possible for the protocols
   to override how method request strings are matched to methods definitions.
 * Unsigned integer primitives were added.
 * ZeroMQ client was fixed.
 * Header confusion in native http soap client was fixed.
 * Grouped transport-specific context information under ctx.transport
   attribute.
 * Added a self reference mechanism.

rpclib-2.0.10-alpha
-------------------

 * The inclusion of base xml schemas were made optional.
 * WSDL: Fix out header being the same as in header.
 * Added type checking to outgoing Integer types. it's not handled as nicely as
   it should be.
 * Fixed the case where changing the _in_message tag name of the method
   prevented it from being called.
 * SOAP/WSDL: Added support for multiple {in,out}_header objects.
 * Fix some XMLAttribute bugs.

rpclib-2.0.9-alpha
------------------

 * Added inheritance support to rpclib.model.table.TableSerializer.

rpclib-2.0.8-alpha
------------------

 * The NullServer now also returns context with the return object to have it
   survive past user-defined method return.

rpclib-2.0.7-alpha
------------------

 * More tests are migrated to the new api.
 * Function identifier strings are no more created directly from the function
   object itself. Function's key in the class definition is used as default
   instead.
 * Base xml schemas are no longer imported.

rpclib-2.0.6-alpha
------------------

 * Added rpclib.server.null.NullServer, which is a server class with a client
   interface that attempts to do no (de)serialization at all. It's intended to
   be used in tests.

rpclib-2.0.5-alpha
------------------

 * Add late mapping support to sqlalchemy table serializer.

rpclib-2.0.4-alpha
------------------

 * Add preliminary support for a sqlalchemy-0.7-compatible serializer.

rpclib-2.0.3-alpha
------------------

 * Migrate the HttpRpc serializer to the new internal api.

rpclib-2.0.2-alpha
------------------

 * SimpleType -> SimpleModel
 * Small bugfixes.

rpclib-2.0.1-alpha
------------------

 * EventManager now uses ordered sets instead of normal sets to store event
   handlers.
 * Implemented sort_wsdl, a small hack to sort wsdl output in order to ease
   debugging.

rpclib-2.0.0-alpha
------------------

 * Implemented EventManager and replaced hook calls with events.
 * The rpc decorator now produces static methods. The methods still get an implicit
   first argument that holds the service contexts. It's an instance of the
   MethodContext class, and not the ServiceBase (formerly DefinitionBase) class.
 * The new srpc decorator doesn't force the methods to have an implicit first
   argument.
 * Fixed fault namespace resolution.
 * Moved xml constants to rpclib.const.xml_ns
 * The following changes to soaplib were ported to rpclib's SOAP/WSDL parts:
    * duration object is now compatible with Python's native timedelta.
    * WSDL: Support for multiple <service> tags in the wsdl (one for each class in the
      application)
    * WSDL: Support for multiple <portType> tags and multiple ports.
    * WSDL: Support for enumerating exceptions a method can throw was added.
    * SOAP: Exceptions got some love to be more standards-compliant.
    * SOAP: Xml attribute support
 * Moved all modules with packagename.base to packagename._base.
 * Renamed classes to have module name as a prefix:
    * rpclib.client._base.Base -> rpclib.client._base.ClientBase
    * rpclib.model._base.Base -> rpclib.model._base.ModelBase
    * rpclib.protocol._base.Base -> rpclib.protocol._base.ProtocolBase
    * rpclib.server._base.Base -> rpclib.server._base.ServerBase
    * rpclic.service.DefinitionBase -> rpclib.service.ServiceBase
    * rpclib.server.wsgi.Application  -> rpclib.server.wsgi.WsgiApplication
 * Moved some classes and modules around:
    * rpclib.model.clazz -> rpclib.model.complex
    * rpclib.model.complex.ClassSerializer -> rpclib.model.complex.ComplexModel
    * rpclib.Application -> rpclib.application.Application
    * rpclib.service.rpc, srpc -> rpclib.decorator.rpc, srpc

soaplib-3.x -> rpclib-1.1.1-alpha
---------------------------------

 * Soaplib is now also protocol agnostic. As it now supports protocols other
   than soap (like Rest-minus-the-verbs HttpRpc), it's renamed to rpclib. This
   also means soaplib can now support multiple versions of soap and wsdl
   standards.
 * Mention of xml and soap removed from public api where it's not directly
   related to soap or xml. (e.g. a hook rename: on_method_exception_xml ->
   on_method_exception_doc)
 * Protocol serializers now return iterables instead of complete messages. This
   is a first step towards eliminating the need to have the whole message in
   memory during processing.

soaplib-2.x
-----------

 * This release transformed soaplib from a soap server that exclusively supported
   http to a soap serialization/deserialization library that is architecture and
   transport agnostic.
 * Hard dependency on WSGI removed.
 * Sphinx docs with working examples: http://arskom.github.com/rpclib/
 * Serializers renamed to Models.
 * Standalone xsd generation for ClassSerializer objects has been added. This
   allows soaplib to be used to define generic XML schemas, without SOAP
   artifacts.
 * Annotation Tags for primitive Models has been added.
 * The soaplib client has been re-written after having been dropped from
   recent releases. It follows the suds API but is based on lxml for better
   performance.
   WARNING: the soaplib client is not well-tested and future support is tentative
   and dependent on community response.
 * 0mq support added.
 * Twisted supported via WSGI wrappers.
 * Increased test coverage for soaplib and supported servers

soaplib-1.0
-----------

 * Standards-compliant Soap Faults
 * Allow multiple return values and return types

soaplib-0.9.4
-------------

 * pritimitive.Array -> clazz.Array
 * Support for SimpleType restrictions (pattern, length, etc.)

soaplib-0.9.3
-------------

 * Soap header support
 * Tried the WS-I Test first time. Many bug fixes.

soaplib-0.9.2
-------------

 * Support for inheritance.

soaplib-0.9.1
-------------

 * Support for publishing multiple service classes.

soaplib-0.9
-----------

 * Soap server logic almost completely rewritten.
 * Soap client removed in favor of suds.
 * Object definition api no longer needs a class types: under class definition.
 * XML Schema validation is supported.
 * Support for publishing multiple namespaces. (multiple <schema> tags in the wsdl)
 * Support for enumerations.
 * Application and Service Definition are separated. Application is instantiated
   on server start, and Service Definition is instantiated for each new request.
 * @soapmethod -> @rpc

soaplib-0.8.1
-------------

 * Switched to lxml for proper xml namespace support.

soaplib-0.8.0
-------------

 * First public stable release.
