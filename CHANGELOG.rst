
Changelog
=========

spyne-2.14.0
------------
* Python 3.10 support.
* msgpack 1.x support.
* sqlalchemy 1.2, 1.3, 1.4 support.
* Ported the Http subsystem to Python 3.
* Support for interface document customization.
  Thanks to github.com/PyGuDev
* Dropped deprecated integration for SqlAlchemy.
  In other words, ``spyne.model.table`` is gone.
* Bug fixes and one DoS fix: GHSL-2021-115.
  Thanks to github.com/kevinbackhouse and Github security team.
* Jenkins run: https://jenkins.arskom.com.tr/job/spyne/job/origin-stable/192/

spyne-2.13.16
-------------
* Python 3.9 support
* A lot of small fixes here and there.

spyne-2.13.15
-------------
* A lot of small fixes here and there blocking the stable release.

spyne-2.13.14-beta
-------------------
* Test and fix polymorphic roundtrip via XmlDocument.
* Implement support for relationship tables with >2 foreign keys.

spyne-2.13.13-beta
-------------------
* Implement wrapped/not_wrapped for ComplexModel and HierDict family.

spyne-2.13.12-beta
-------------------
* Python 3 support is now beta !!!!. All tests pass and there are no known bugs

spyne-2.13.11-alpha
-------------------
* SOAP: Repaired MtoM parsing.
* Faults: The Fault api is now much more consistent.
* Various fixes across the board.
* ``sqla_column_args`` is now only a dict. It can override column name without
  changing mapped object attribute name.
* Various Python 3 fixes for the Twisted frontend.


spyne-2.13.4-alpha
------------------
* ``Date(format="%Y")`` no longer works. Use ``Date(date_format="%Y")`` just
  like the api docs say

spyne-2.13.3-alpha
------------------
* Add support for sqlalchemy-1.2.
* Implement _logged for @rpc.
* Fix memory leak in ComplexModelBase.as_dict. 
* Switch to homegrown jenkins as test infrastructure. See
  https://jenkins.arskom.com.tr
* Fix decimal totalDigits blunder.

spyne-2.13.2-alpha
------------------
* ``ServiceBase`` is deprecated in favor of ``Service``. It's just a name change
  in order to make it consistent with the rest of the package. ServiceBase will
  be kept until Spyne 3.

* Introduced internal keys for services and methods. Uniqueness is enforced
  during Application instantiation. If your server refuses to boot after
  migrating to 2.13 raising ``MethodAlreadyExistsError``, explicitly setting a
  unique ``__service_name__`` in one of the offending ``ServiceBase``
  subclasses should fix the problem.

  See 2fee1435c30dc50f7503f0915b5e56220dff34d0 for the change.

* EXPERIMENTAL library-wide Python 3 Support! Yay!

    * MessagePack uses backwards-compatible raws with a hard-coded UTF-8 encoding
      for Unicode (non-ByteArray) types. Please open an issue if not happy with
      this.
    * It's the transports' job to decide on a codec. Use UTF-8 when in doubt, as
      that's what we're doing.
    * Avoid the async keyword for Python 3.7.
    * Float rounding behaviour seems to have changed in Python 3. In Python 2,
      ``round(2.5) = 3`` and ``round(3.5) = 4`` whereas in Python 3,
      ``round(2.5) = 2`` and ``round(3.5) = 4``. This is called half-to-even
      rounding and while being counterintuitive, it seems to make better sense from
      a statistical standpoint.

      You will have to live with this or use ``decimal.Decimal``.

      This changes the way datetime and time microseconds are rounded. See
      ``test_datetime_usec`` and ``test_time_usec`` in
      ``spyne.test.model.test_primitive``.

* ``spyne.model.Unicode`` used to tolerate (i.e. implicitly but not-so-silenty
  casted to ``str``) int values. This is no longer the case. If you want to
  set proper numbers to a Unicode-designated field, you must provide a
  casting function. Generally, ``Unicode(cast=str)`` is what you want to do.
  See d495aa3d56451bd02c0076a9a1f14c6450eadc8e for the change.
* ``exc_table`` is deprecated in favour of ``exc_db``\. Please do a
  s/exc_table/exc_db/g in your codebase when convenient.
* Django 1.6 support dropped. Supporting 1.7-1.10.
* Bare methods with non-empty output now have
  ``descriptior.body_style = spyne.BODY_STYLE_EMPTY_OUT_BARE``\, which was
  ``spyne.BODY_STYLE_EMPTY`` before. This hould not break anything unless you
  are doing some REAL fancy stuff in the method decorators or service events.
* Auxproc is DEPRECATED. Just get rid of it.
* ``spyne.protocol.dictdoc.simple``, ``spyne.server.twisted.http`` and
  ``spyne.server.django`` are not experimental anymore.
* No major changes otherwise but we paid a lot of technical debt. e.g. We
  revamped the test infrastructure.
* ``_in_variable_names`` argument to ``@rpc`` was deprecated in favour of
  ``_in_arg_names``
* ``_udp`` argument to ``@rpc`` was deprecated in favour of ``_udd``. UDP is
  too well known as user datagram protocol which could be confusing.
* ``_when`` argument to ``@mrpc`` now needs to be a callable that satisfies
  the ``f(self, ctx)`` signature. It was ``f(self)`` before.
* Attachment is removed. It's been deprecated since ages.
* Usual bug fixes.

spyne-2.12.15
-------------
* Fix graceful import failures for Python 3

spyne-2.12.14
-------------
* Fixed inclusive ranges for DateTime and friends. #506
* Turns out SQLAlchemy 1.1 causes funky crashes. We're fixated on 1.0 until
  the issue can be investiaged.
* Implemented MIN_GC_INTERVAL to prevent excessive calls to ``gc.collect()``
  See issue #472. PR: #515

spyne-2.12.13
-------------
* Dang.

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

Check the documentation at http://spyne.io/docs for changelogs of the older
versions
