
Changelog
=========

spyne-2.12.13
-------------
* Fixed inclusive ranges for DateTime and friends.
* Turns out SQLAlchemy 1.1 causes funky crashes. We're fixated on 1.0 until
  the issue can be investiaged. #506
* Implemented MIN_GC_INTERVAL to prevent excessive calls to ``gc.collect()``
  See issue #472. PR: #515

spyne-2.12.12
-------------
* Return to pre 2.12 behaviour - coroutine exceptions are not silenced but
  sent up the stack. This is backport of 2.13 fix.
* Proper serialization of ComplexModels subclasses of other ComplexModels
  when initialized from lists.
* Minor bug fixes all around.

spyne-2.12.11
-------------
* Fix self-referential relationships pointing the wrong way
* Fix wrong use of string interpolation operator in logging call slowing Spyne
  down for no visible reason
* Detect and prevent name clashes between the foreign key column name and the
  object itself.
* Silence a lot of (wrong) customized class instantiation warnings.

spyne-2.12.10
-------------
* IpAddress types now support PostgreSQL's PGInet.
* Drop trial for twisted tests and switch to pytest-twisted.
* ``_safe_set`` now returns True on success so that protocols can react
  accordingly.
* \*DictDoc now logs properly whether a value is discarded or passed to the
  deserialized instance.
* Minor bug fixes here and there.

spyne-2.12.9
------------
* Make ``DateTime`` handle unicode date format strings for Python 2.
* Fix idle timer not starting on connectionMade for ``MessagePackTransportBase``

spyne-2.12.7
------------
* Not beta anymore. Woo!
* Made ServiceBase subclasses reusable
* Implemented class customization via ``__getitem__``\.
* Fixed an ``ImportError`` running Python 3.4 under Pydev using PyCharm.
  (Eclipse still has issues, see
  `issue #432 <https://github.com/arskom/spyne/issues/432>`_. Any help would be
  much appreciated)
* Fixed DateTime corner case with μs values between 999995 and 999999.
* Help misguided user code that returns an int for a string type by implicitly
  yet not-so-silently converting the ``int``/``long`` to ``str``\.
* Fixed \*Cloth sometimes getting stuck ``repr()``\'ing  passed instance.
* Fixed ``SimpleDictDocument`` confusing a missing value and an empty value for
  array types. When the client wants to denote an empty array, it should pass
  ``array_field=empty``\. Normally it passes something along the lines of:
  ``array_field[0]=Something&array_field[1]=SomethingElse``\.
* Split ``MessagePackServerBase`` to ``MessagePackTransportBase`` and
  ``MessagePackServerBase``\. No API was harmed during this change.
* Implement optional idle timeout for ``MessagePackTransportBase``\.
* Add support for PGObjectJson, PGObjectXml and PGFileJson to sql table
  reflection.
* ``log_repr`` now consults ``NATIVE_MAP`` as a last resort before freaking out.
* Removed some dead code.

spyne-2.12.6-beta
-----------------
* Thanks to `issue #446 <https://github.com/arskom/spyne/issues/446>`_
  we noticed that in some cases, SOAP messages inside HTTP requests got
  processed even when the request method != 'POST'. This got resolved, but you
  should check whether this is the case in your setup and take the necessary
  precautions before deploying Spyne.

spyne-2.12.[12345]-beta
-----------------------
* Many bugs fixed very quick.

spyne-2.12.0-beta
-----------------
* XmlObject: Support for ``attribute_of`` is removed.
* NullServer now supports async.
* XmlCloth was rewritten while less sleep-deprived.
* ProtocolBase now also implements serializing primitives to unicode.
* Add initial support for input polymorphism to XmlDocument (parsing xsi:type).
  It's an experimental feature.
* Add output polymorphism for all protocols. It's off-by-default for XmlDocument
  and friends, on-by-default for others.
* Add stub implementation for SOAP 1.2
* Add initial implementation for SOAP 1.2 Faults.
* Remove the deprecated ``interface`` argument to ``Application``\.
* HierDictDocument's broken wrapped dict support was fixed. Even though this is
  supposed to break compatibility with 2.11, virtually no one seems to use this
  feature. Only now it's mature enough to be set on stone. Let us know!
* We now validate kwargs passed to ``@rpc``\. Be sure to test your daemons
  before deploying for production, because if you got leftovers, the server will
  refuse to boot!
* It's now forbidden (by assert) to inherit from a customized class.
* It's also forbidden (by convention) to instantiate a customized class. Don't
  do it! The warning will be converted to an assert in the future.

spyne-2.11.0
------------
* Experimental Python 3 Support for all of the Xml-related (non-Html)
  components.
* Add support for altering output protocol by setting ``ctx.out_protocol``.
* Add returning ctx.out_string support to null server (The ``ostr`` argument).
* Add support for XmlData modifier. It lets mapping the data in the xml body
  to an object field via xsd:simpleContent.
* Remove deprecated ``JsonObject`` identifier. Just do a gentle
  ``s/JsonObject/JsonDocument/g`` if you're still using it.
* SQLAlchemy: Implement storing arrays of simple types in a table.
* SQLAlchemy: Make it work with multiple foreign keys from one table to
  another.
* SQLAlchemy: Implement a hybrid file container that puts file metadata in a
  json column in database and and file data in file system. Fully supported by
  all protocols as a binary File.Value instance.
* Implement an Xml Schema parser.
* Import all model markers as well as the ``@rpc``\, ``@srpc``\, ``@mrpc``,
  ``ServiceBase`` and ``Application`` to the root ``spyne`` package.
* Implement JsonP protocol.
* Implement SpyneJsonRpc 1.0 protocol -- it supports request headers.

  Sample request:  ``{"ver":1, "body": {"div": [4,2]}, "head": {"id": 1234}}``
  Sample response: ``{"ver":1, "body": 2}``

  Sample request:  ``{"ver":1, "body": {"div": {"dividend":4,"divisor":0]}}``
  Sample response: ``{"ver":1, "fault": {"faultcode": "Server", "faultstring": "Internal Error"}}}``

* Steal and integrate the experimental WebSocket tranport from Twisted.
* Support Django natively using `spyne.server.django.DjangoView` and
  `spyne.server.django.DjangoServer`.
* It's now possible to override the ``JsonEncoder`` class ``JsonDocument`` uses.
* Remove hard-coded utf-8 defaults from almost everywhere.
* Remove hard-coded pytz.utc defaults from everywhere. Use spyne.LOCAL_TZ to
  configure the default time zone.
* As a result of the above change, ``datetime`` objects deserialized by Spyne
  are forced to the above time zone during soft validation (nothing should have
  changed from the user code perspective).
* Add ``default_factory`` to ModelBase customizer. It's a callable that produces
  default values on demand. Suitable to be used with e.g. lambdas that return
  mutable defaults.
* New ``spyne.util.AttrDict`` can be used for passing various dynamic
  configuration data.
* ``child_attrs`` can now be passed to the ComplexModelBase customizer in order
  to make object-specific in-place customizations to child types.
* Add mapper between Django models and `spyne.util.django.DjangoComplexModel`
  types.
* Spyne now tracks subclasses and adds them to the interface if they are in the
  same namespace as their parent.
* Simple dictionary protocol's ``hier_delim`` default value is now '.'
* Fixes support for XmlAttributes with max_occurs>1 referencing the same
  'attribute_of' element in a ComplexModel subclass.
* Renders ``spyne.model.File`` as ``twisted.web.static.File`` when using HttpRpc
  over ``TwistedWebResource``. This lets twisted handle Http 1.1-specific
  functionality like range requests.
* Many, many, many bugs fixed.

spyne-2.10.10
-------------
* Fix wsdl rendering in TwistedWebResource.
* Fix http response header propagation in TwistedWebResource.
* Fix handling of fractions in microsecond values.
* Fix spyne.util.get_validation_schema()

spyne-2.10.9
------------
* Fix total_seconds quirk for Python 2.6.
* Turn off Xml features like entity resolution by default. This mitigates
  an information disclosure attack risk in services whose response contain
  some fragments or all of the request. Also prevents DoS attacks that make use
  of entity expansion. See https://bitbucket.org/tiran/defusedxml for more info.
* Drop Python 2.5 support (It wasn't working anyway).

spyne-2.10.8
------------
* Fix Unicode losing pattern on re-customization
* Fix Duration serialization, add a ton of test cases.
* Fix binary urlsafe_base64 encoding.
* Fix arbitrary exception serialization.
* Fix some doc errors.

spyne-2.10.7
------------
* Fix logic error in wsdl caching that prevented the url in Wsdl document from
  being customized.
* Fix dictdoc not playing well with functions with empty return values.

spyne-2.10.6
------------
* Fix exception serialization regression in DictDocument family.
* Fix xml utils (and its example).

spyne-2.10.5
------------
* Fix default value handling in ``HttpRpc``.
* Fix invalid document type raising ``InternalError`` in DictDocument family.
  It now raises ``ValidationError``.
* HttpRpc: Fix ``ByteArray`` deserialization.
* HttpRpc: Fix many corner cases with ``Array``\s.
* Fix Csv serializer.
* Fix Mandatory variants of ``Double`` and ``Float`` inheriting from decimal.

spyne-2.10.4
------------
* Fix handling of ``spyne.model.binary.File.Value`` with just path name.
* Fix decimal restrictions (some more).
* Make user code that doesn't return anything work with twisted server
  transport.

spyne-2.10.3
------------
* Add validation tests for HierDictDocument and fix seen issues.
* Add validation tests for FlatDictDocument and fix seen issues.
* Clarify Json and Http behavior in relevant docstrings.
* Fix Python2.6 generating max_occurs="inf" instead of "unbounded" sometimes.

spyne-2.10.2
------------
* Fix ByteArray support accross all protocols.
* Fix namespaces of customized simple types inside ``XmlAttribute`` not being
  imported.

spyne-2.10.1
------------
* Fix confusion in Decimal restriction assignment.
* Fix classmethod calls to ProtocolBase.
* Fix schema generation error in namespaced xml attribute case.

spyne-2.10.0
------------
* Returning twisted's Deferred from user code is now supported.
* You can now set Http response headers via ctx.out_header when
  out_protocol is HttpRpc. https://github.com/arskom/spyne/pull/201
* lxml is not a hard requirement anymore.
* XmlDocument and friends: cleanup_namespaces is now True by default.
* XmlDocument and friends: Added ``encoding`` and ``pretty_print`` flags that
  are directly passed to ``lxml.etree.tostring()``.
* XmlDocument and friends:'attribute_of' added to ModelBase to add attribute
  support for primitives. This is currently ignored by (and mostly irrelevant
  to) other protocols.
* XmlDocument and friends: Attribute serialization is working for arrays.
* Add support for exposing existing whose source code via the _args argument
  to the srpc decorator. See the existing_api example for usage examples.
* Add Streaming versions of Pyramid and Django bridge objects.
* Remove destructor from ``MethodContext``. Now transports need to call
  ``.close()`` explicitly to close object and fire relevant events.
* Application event 'method_context_constructed' was renamed to
  ``'method_context_created'``.
* Application event 'method_context_destroyed' was removed. The
  ``'method_context_closed'`` event can be used instead.
* SQLAlchemy integration now supports advanced features like specifying
  indexing methods.
* The object composition graph can now be cyclic.
* Integers were overhauled. Now boundary values of limited-size types are
  accessible via ``Attributes._{min,max}_bounds``.
* We now have six spatial types, ``Point``, ``LineString`` and ``Polygon``
  along with their ``Multi*`` variants.
* The deprecated ``ProtocolBase.set_method_descriptor`` function was removed.
* It's now possible to override serialization in service implementations.
  You can set ``ctx.out_document`` to have the return value from user funtion
  ignored. You can also set ``ctx.out_string`` to have the ``ctx.out_document``
  ignored as well.
* Added as_timezone support to DateTime. It calls
  ``.astimezone(as_time_zone).replace(tzinfo=None)`` on native values.
* Added YAML support via PyYaml.
* Split dict logic in DictDocument as ``HierDictDocument`` and
  ``FlatDictDocument``.
* Complete revamp of how DictDocument family work. skip_depth is replaced by
  richer functionalty that is enabled by two flags: ``ignore_wrappers`` and
  ``complex_as``.
* Added cookie parsing support to HttpRpc via ``Cookie.SimpleCookie``.
* Moved ``{to,from}_string`` logic from data models to ProtocolBase.
  This gives us the ability to have more complex fault messages
  with other fault subelements that are namespace-qualified without
  circular dependency problems - Stefan Andersson <norox81@gmail.com>
* DictDocument and friends: ``ignore_wrappers`` and ``complex_as`` options
  added as a way to customize protocol output without hindering other parts
  of the interface.

Check the documentation at http://spyne.io/docs for changelogs of the older
versions
