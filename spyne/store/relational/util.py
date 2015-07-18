#
# retrieved from https://github.com/kvesteri/sqlalchemy-utils
# commit 99e1ea0eb288bc50ddb4a4aed5c50772d915ca73
#
# Copyright (c) 2012, Konsta Vesterinen
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * The names of the contributors may not be used to endorse or promote products
#   derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

import os
from copy import copy

import sqlalchemy as sa
from sqlalchemy.engine import Dialect
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import object_session
from sqlalchemy.orm.exc import UnmappedInstanceError


def get_bind(obj):
    """
    Return the bind for given SQLAlchemy Engine / Connection / declarative
    model object.
    :param obj: SQLAlchemy Engine / Connection / declarative model object
    ::
        from sqlalchemy_utils import get_bind
        get_bind(session)  # Connection object
        get_bind(user)
    """
    if hasattr(obj, 'bind'):
        conn = obj.bind
    else:
        try:
            conn = object_session(obj).bind
        except UnmappedInstanceError:
            conn = obj

    if not hasattr(conn, 'execute'):
        raise TypeError(
            'This method accepts only Session, Engine, Connection and '
            'declarative model objects.'
        )
    return conn


def quote(mixed, ident):
    """
    Conditionally quote an identifier.
    ::
        from sqlalchemy_utils import quote
        engine = create_engine('sqlite:///:memory:')
        quote(engine, 'order')
        # '"order"'
        quote(engine, 'some_other_identifier')
        # 'some_other_identifier'
    :param mixed: SQLAlchemy Session / Connection / Engine / Dialect object.
    :param ident: identifier to conditionally quote
    """
    if isinstance(mixed, Dialect):
        dialect = mixed
    else:
        dialect = get_bind(mixed).dialect
    return dialect.preparer(dialect).quote(ident)


def database_exists(url):
    """Check if a database exists.

    :param url: A SQLAlchemy engine URL.

    Performs backend-specific testing to quickly determine if a database
    exists on the server. ::

        database_exists('postgres://postgres@localhost/name')  #=> False
        create_database('postgres://postgres@localhost/name')
        database_exists('postgres://postgres@localhost/name')  #=> True

    Supports checking against a constructed URL as well. ::

        engine = create_engine('postgres://postgres@localhost/name')
        database_exists(engine.url)  #=> False
        create_database(engine.url)
        database_exists(engine.url)  #=> True

    """

    url = copy(make_url(url))
    database = url.database
    if url.drivername.startswith('postgresql'):
        url.database = 'template1'
    else:
        url.database = None

    engine = sa.create_engine(url)

    if engine.dialect.name == 'postgresql':
        text = "SELECT 1 FROM pg_database WHERE datname='%s'" % database
        return bool(engine.execute(text).scalar())

    elif engine.dialect.name == 'mysql':
        text = ("SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA "
                "WHERE SCHEMA_NAME = '%s'" % database)
        return bool(engine.execute(text).scalar())

    elif engine.dialect.name == 'sqlite':
        return database == ':memory:' or os.path.exists(database)

    else:
        text = 'SELECT 1'
        try:
            url.database = database
            engine = sa.create_engine(url)
            engine.execute(text)
            return True

        except (ProgrammingError, OperationalError):
            return False


def create_database(url, encoding='utf8', template=None):
    """Issue the appropriate CREATE DATABASE statement.

    :param url: A SQLAlchemy engine URL.
    :param encoding: The encoding to create the database as.
    :param template:
        The name of the template from which to create the new database. At the
        moment only supported by PostgreSQL driver.

    To create a database, you can pass a simple URL that would have
    been passed to ``create_engine``. ::

        create_database('postgres://postgres@localhost/name')

    You may also pass the url from an existing engine. ::

        create_database(engine.url)

    Has full support for mysql, postgres, and sqlite. In theory,
    other database engines should be supported.
    """

    url = copy(make_url(url))

    database = url.database

    if url.drivername.startswith('postgresql'):
        url.database = 'template1'
    elif not url.drivername.startswith('sqlite'):
        url.database = None

    engine = sa.create_engine(url)

    if engine.dialect.name == 'postgresql':
        if engine.driver == 'psycopg2':
            from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
            engine.raw_connection().set_isolation_level(
                ISOLATION_LEVEL_AUTOCOMMIT
            )

        if not template:
            template = 'template0'

        text = "CREATE DATABASE {0} ENCODING '{1}' TEMPLATE {2}".format(
            quote(engine, database),
            encoding,
            quote(engine, template)
        )
        engine.execute(text)

    elif engine.dialect.name == 'mysql':
        text = "CREATE DATABASE {0} CHARACTER SET = '{1}'".format(
            quote(engine, database),
            encoding
        )
        engine.execute(text)

    elif engine.dialect.name == 'sqlite' and database != ':memory:':
        open(database, 'w').close()

    else:
        text = 'CREATE DATABASE {0}'.format(quote(engine, database))
        engine.execute(text)


def drop_database(url):
    """Issue the appropriate DROP DATABASE statement.

    :param url: A SQLAlchemy engine URL.

    Works similar to the :ref:`create_database` method in that both url text
    and a constructed url are accepted. ::

        drop_database('postgres://postgres@localhost/name')
        drop_database(engine.url)

    """

    url = copy(make_url(url))

    database = url.database

    if url.drivername.startswith('postgresql'):
        url.database = 'template1'
    elif not url.drivername.startswith('sqlite'):
        url.database = None

    engine = sa.create_engine(url)

    if engine.dialect.name == 'sqlite' and url.database != ':memory:':
        os.remove(url.database)

    elif engine.dialect.name == 'postgresql' and engine.driver == 'psycopg2':
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        engine.raw_connection().set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

        # Disconnect all users from the database we are dropping.
        version = list(
            map(
                int,
                engine.execute('SHOW server_version').first()[0].split('.')
            )
        )
        pid_column = (
            'pid' if (version[0] >= 9 and version[1] >= 2) else 'procpid'
        )
        text = '''
        SELECT pg_terminate_backend(pg_stat_activity.%(pid_column)s)
        FROM pg_stat_activity
        WHERE pg_stat_activity.datname = '%(database)s'
          AND %(pid_column)s <> pg_backend_pid();
        ''' % {'pid_column': pid_column, 'database': database}
        engine.execute(text)

        # Drop the database.
        text = 'DROP DATABASE {0}'.format(quote(engine, database))
        engine.execute(text)

    else:
        text = 'DROP DATABASE {0}'.format(quote(engine, database))
        engine.execute(text)
