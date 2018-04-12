
.. _manual-sqlalchemy:

SQLAlchemy Integration
======================

This tutorial builds on the :ref:`manual-user-manager` tutorial. If you
haven't done so, we recommend you to read it first.

In this tutorial, we talk about using Spyne tools that make it easy to deal
with database-related operations using `SQLAlchemy <http://sqlalchemy.org>`_.
SQLAlchemy is a well-established and mature SQL generation and ORM library
that is well worth the time invested in climbing its learning curve.

We will show how to integrate SQLAlchemy and Spyne object definitions, and
how to do painless transaction management using Spyne events.

There are two ways of integrating with SQLAlchemy:

1. The first and supported method is to use the output of the
   :class:`spyne.model.complex.TTableModel`.

   The ``TTableModel`` class is a templated callable that produces a
   ``ComplexModel`` that has enough information except table name to be mapped
   with a SQL table. It takes an optional ``metadata`` argument and creates a
   new one when one isn't supplied.

   **WARNING:** While the machinery around ``TTableModel`` is in production
   use in a few places, it should be considered *experimental* as it's a
   relatively new feature which is not as battle-tested as the rest of the
   Spyne code.

   Also, this is only tested with `PostgreSQL <http://postgresql.org>`_ and
   to some extent, `SQLite <http://sqlite.org>`_\.
   We're looking for volunteers to test and integrate other RDBMSs, please
   open an issue and chime in.

2. The second method is to use :class:`spyne.model.table.TableModel` as a
   second base class together with the declarative base class (output of the
   :func:`sqlalchemy.orm.declarative_base` callable). This is deprecated [#]_
   and won't be developed any further, yet it also won't be removed in the
   foreseeable feature as apparently there are people who are quite fine with
   its quirks and would prefer to have it shipped within the Spyne package.

This document will cover only the first method. The documentation for the
second method can be found in the :mod:`spyne.model.table` documentation or in
the Spyne 2.9 documentation.

The semantics of SQLAlchemy's and Spyne's object definition are almost the
same, except a few small differences:

#. SQLAlchemy's ``Integer`` maps to Spyne's ``Integer32`` or ``Integer64``\,
   depending on the RDBMS. Spyne's ``Integer``\, as it's an arbitrary-size
   number, is converted to :class:`sqlalchemy.Decimal` type as it's the only
   type that can acommodate arbitrary-size numbers. So it's important to use a
   bounded integer type like ``Integer32`` or ``Integer64``\, especially as
   primary key.

#. SQLAlchemy's ``UnicodeText`` is Spyne's ``Unicode`` with no ``max_len``
   restriction. If you need a length-limited ``UnicodeText``, you can use
   Spyne's ``Unicode`` object as follows: ::

        class SomeTable(TableModel):
            __tablename__ = "some_table"

            # text
            some_text = Unicode(2048, db_type=sqlalchemy.UnicodeText)

            # varchar
            some_varchar = Unicode(2048)

            # text
            some_more_text = Unicode

   Default mapping for text types is ``varchar``\. Note that the limit is only
   enforced to incoming data, in this case the database type is bounded only
   by the limits of the database system.

#. Spyne does not reflect all restrictions to the database -- some are only
   enforced to incoming data when validation is enabled. These include range
   and value restrictions for numbers, and ``min_len`` and ``pattern``
   restrictions for Spyne types.

Okay, enough with the introductory & disclaimatory stuff, let's get coding :)

There's a fully functional example at
:download:`examples/user_manager/server_sqlalchemy.py <../../../examples/user_manager/server_sqlalchemy.py>`\.
in the source distribution.

First, we need a database handle: ::

    db = create_engine('sqlite:///:memory:')
    Session = sessionmaker(bind=db)
    metadata = MetaData(bind=db)

Now, we must define our own ``TableModel`` base class. This must be defined
for every ``MetaData`` instance.

    TableModel = TTableModel(metadata)

Doing this is also possible: ::

    TableModel == TTableModel()
    TableModel.Attributes.sqla_metadata.bind = db

... but the first method is arguably cleaner.

We're finally ready to define Spyne types mapped to SQLAlchemy tables. At this
point, we have two options: Do everything with the Spyne markers, or re-use
existing SQLAlchemy code we might already have.

The Spyne Way
-------------

Let's consider the following two class definitions: ::

    class Permission(TableModel):
        __tablename__ = 'permission'

        id = UnsignedInteger32(pk=True)
        application = Unicode(values=('usermgr', 'accountmgr'))
        operation = Unicode(values=('read', 'modify', 'delete'))

    class User(TableModel):
        __tablename__ = 'user'

        id = UnsignedInteger32(pk=True)
        user_name = Unicode(32, min_len=4, pattern='[a-z0-9.]+', unique=True)
        full_name = Unicode(64, pattern='\w+( \w+)+')
        email = Unicode(64, pattern=r'[a-z0-9._%+-]+@[a-z0-9.-]+\.[A-Z]{2,4}')
        last_pos = Point(2, index='gist')
        permissions = Array(Permission).store_as('table')

A couple of points about the above block:

A ``TableModel`` subclass won't be mapped to a database table if it's missing
both the ``__table__`` and ``__tablename__`` attributes. As we're defining the
table in this object, we just pass the ``__tablename__`` attribute -- the
``__table__`` object (which is a :class:`sqlalchemy.schema.Table` instance)
will be generated automatically.

The definitions of the ``id``\, ``user_name``\, ``full_name`` and ``email``
fields should be self-explanatory. There are other database-specific arguments
that can be passed to the column definition, see the
:class:`spyne.model.ModelBase` reference for more information.

The ``last_pos`` field is a spatial type -- a 2D point, to be
exact. PostGIS docs suggest to use 'gin' or 'gist' indexes with spatial
fields. Here we chose to use the 'gist' index [#]_.

As for the ``permissions`` field, due to the ``store_as('table')`` call, it
will be stored using a one-to-many relationship. Spyne automatically
generates a foreign key column inside the ``permission`` table with 'user_id'
as default value.

If we'd let the ``store_as()`` call out: ::

        permissions = Array(Permission)

... the permissions field would not exist as far as SQLAlchemy is concerned.

Calling ``store_as()`` is just a shortcut for calling
``.customize(store_as='table')``\. 

While the default is what appears to make most sense when defining such
relations, it might not always be appropriate. Spyne offers the so-called
"compound option object"s to make it easy to configure persistance options.

Using the :class:`spyne.model.complex.table` object, we change the
``permissions`` field to be serialized using the many-to-many pattern:

::
        from spyne.model.complex import table

        permissions = Array(Permission).store_as(table(multi=True))

In this case, Spyne takes care of creating a relation table with appropriate
foreign key columns. 

We can also alter column names or the relation table name:

::

        from spyne.model.complex import table

        permissions = Array(Permission).store_as(table(
                  multi='user_perm_rel',
                  left='u_id', right='perm_id',
              ))


See the :class:`spyne.model.complex.table` reference for more details on
configuring object relations.

Using SQL Databases as Hybrid Document Stores
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``'table'`` is not the only option for persisting objects to a database. Other
options are ``'json'`` and ``'xml'``\. These use the relevant column types to
store the object serialized to JSON or XML.

Let's modify the previous example to store the ``Permission`` entity in a JSON
column. ::

    class Permission(ComplexModel):
        application = Unicode(values=('usermgr', 'accountmgr'))
        operation = Unicode(values=('read', 'modify', 'delete'))

    class User(TableModel):
        __tablename__ = 'user'

        id = UnsignedInteger32(pk=True)
        user_name = Unicode(32, min_len=4, pattern='[a-z0-9.]+')
        full_name = Unicode(64, pattern='\w+( \w+)+')
        email = Unicode(64, pattern=r'[a-z0-9._%+-]+@[a-z0-9.-]+\.[A-Z]{2,4}')
        permissions = Array(Permission).store_as('json')

Note that nothing has changed in the ``User`` object except the storage
parameter for the ``permissions`` field, whereas the ``Permission`` object now
inherits from ``ComplexModel`` and does not have (nor need) a primary key.

As the ``Array(Permission)`` is now stored in a document-type column inside
the table, it's possible to make arbitrary changes to the schema of the
``Permission`` object without worrying about schema migrations -- If the
changes are backwards-compatible, everything will work flawlessly. If not,
attributes in that are not defined in the latest object definition will just
be ignored [#]_.

Such changes are never reflected to the schema. In other words, your clients
will never know how your objects are persisted just by looking at your schema
alone.

You can play with the example at `spyne.io <http://spyne.io/#s=sql>`_ to
experiment how Spyne's model engine interacts with SQLAlchemy.

Integrating with Existing SQLAlchemy objects
--------------------------------------------

Let's consider the following fairly ordinary SQLAlchemy object: ::

    class User(DeclarativeBase):
        __tablename__ = 'spyne_user'

        id = Column(sqlalchemy.Integer, primary_key=True)
        user_name = Column(sqlalchemy.String(256))
        first_name = Column(sqlalchemy.String(256))
        last_name = Column(sqlalchemy.String(256))

Assigning an existing SQLAlchemy table to the ``__table__`` attribute of the
``TableModel`` ... ::

    class User(TableModel):
        __table__ = User.__table__

... creates the corresponding Spyne object. This conversion works for simple
column types, but complex ORM constructs like ``relationship``\ are not
converted.

If you want to override which columns are exposed, you must set everything
manually: ::

    class User(TableModel):
        __table__ = User.__table__

        id = UnsignedInteger32
        user_name = Unicode(32, min_len=4, pattern='[a-z0-9.]+')
        full_name = Unicode(64, pattern='\w+( \w+)+')
        email = Unicode(64, pattern=r'[a-z0-9._%+-]+@[a-z0-9.-]+\.[A-Z]{2,4}')

Any field not listed here does not exist as far as Spyne is concerned.

This is still one of the weaker spots of SQLAlchemy integration, please chime
in with your ideas on how we should handle different cases!

What's next?
------------

This tutorial walks you through most of what you need to know to implement
complex, real-world services. You can read the :ref:`manual-metadata` section
where service metadata management APIs are introduced, but otherwise, you're
mostly set.

You also refer to the reference of the documentation or the mailing list if
you have further questions.


.. [#] The reasons for its depreciation are as follows:

       #. The old way of trying to fuse metaclasses was a nightmare to
          maintain.

       #. The new API can handle existing SQLAlchemy objects via the
          ``__table__`` attribute trick.

       #. It's not easy to add arbitrary restrictions (like pattern) when
          using the SQLAlchemy API.

.. [#] It's not possible to use an Array of primitives directly for
       ``'table'`` storage -- create a ComplexModel with a primary key field
       as a workaround. (or, you guessed it, send a patch!...)

.. [#] To make the case with non-backwards-compatible changes work, an
       implicit versioning support must be added. Assuming that everybody
       agrees that this is a good idea, adding this feature would be another
       interesting project.

       Feedback is welcome!
