
#
# spyne - Copyright (C) Spyne contributors.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301
#

import logging
import functools

logger = logging.getLogger(__name__)

import sys
import datetime

from inspect import isgeneratorfunction
from spyne.util.six import PY3


try:
    from urllib import splittype
    from urllib import splithost
    from urllib import quote

except ImportError: # Python 3
    from urllib.parse import splittype
    from urllib.parse import splithost
    from urllib.parse import quote


def split_url(url):
    """Splits a url into (uri_scheme, host[:port], path)"""
    scheme, remainder = splittype(url)
    host, path = splithost(remainder)
    return scheme.lower(), host, path


def reconstruct_url(environ, protocol=True, server_name=True, path=True,
                                                             query_string=True):
    """Rebuilds the calling url from values found in the
    environment.

    This algorithm was found via PEP 333, the wsgi spec and
    contributed by Ian Bicking.
    """

    url = ''
    if protocol:
        url = environ['wsgi.url_scheme'] + '://'

    if server_name:
        if environ.get('HTTP_HOST'):
            url += environ['HTTP_HOST']

        else:
            url += environ['SERVER_NAME']

            if environ['wsgi.url_scheme'] == 'https':
                if environ['SERVER_PORT'] != '443':
                    url += ':' + environ['SERVER_PORT']

            else:
                if environ['SERVER_PORT'] != '80':
                    url += ':' + environ['SERVER_PORT']

    if path:
        if (quote(environ.get('SCRIPT_NAME', '')) == '/' and
            quote(environ.get('PATH_INFO', ''))[0] == '/'):
            #skip this if it is only a slash
            pass

        elif quote(environ.get('SCRIPT_NAME', ''))[0:2] == '//':
            url += quote(environ.get('SCRIPT_NAME', ''))[1:]

        else:
            url += quote(environ.get('SCRIPT_NAME', ''))

        url += quote(environ.get('PATH_INFO', ''))

    if query_string:
        if environ.get('QUERY_STRING'):
            url += '?' + environ['QUERY_STRING']

    return url


def check_pyversion(*minversion):
    return sys.version_info[:3] >= minversion


class Break(Exception):
    """Raised for breaking out of infinite loops inside coroutines."""
    pass


def coroutine(func):
    assert isgeneratorfunction(func)

    def start(*args, **kwargs):
        try:
            ret = func(*args, **kwargs)
        except TypeError as e:
            logger.error("Function %r at %s:%d got error %r", func.func_name,
                         func.__module__, func.__code__.co_firstlineno, e)
            raise

        try:
            next(ret)

        except StopIteration:
            return None

        except Exception as e:
            logger.exception(e)
            raise e

        return ret

    return start


class memoize(object):
    """A memoization decorator that keeps caching until reset."""

    def __init__(self, func):
        self.func = func
        self.memo = {}

    def __call__(self, *args, **kwargs):
        key = self.get_key(args, kwargs)
        if not key in self.memo:
            self.memo[key] = self.func(*args, **kwargs)
        return self.memo[key]

    def get_key(self, args, kwargs):
        return tuple(args), tuple(kwargs.items())

    def reset(self):
        self.memo = {}


class memoize_id(memoize):
    """A memoization decorator that keeps caching until reset for unhashable
    types. It works on id()'s of objects instead."""

    def get_key(self, args, kwargs):
        return tuple([id(a) for a in args]), \
                                  tuple([(k, id(v)) for k, v in kwargs.items()])


class memoize_id_method(memoize_id):
    """A memoization decorator that keeps caching until reset for unhashable
    types on instance methods. It works on id()'s of objects instead."""

    def __get__(self, obj, objtype):
        """Support instance methods."""
        fn = functools.partial(self.__call__, obj)
        fn.reset = self.reset
        return fn


def sanitize_args(a):
    try:
        args, kwargs = a
        if isinstance(args, tuple) and isinstance(kwargs, dict):
            return args, dict(kwargs)

    except (TypeError, ValueError):
        args, kwargs = (), {}

    if a is not None:
        if isinstance(a, dict):
            args = tuple()
            kwargs = a

        elif isinstance(a, tuple):
            if isinstance(a[-1], dict):
                args, kwargs = a[0:-1], a[-1]
            else:
                args = a
                kwargs = {}

    return args, kwargs


if PY3:
    def _bytes_join(val, joiner=b''):
        return joiner.join(val)
else:
    def _bytes_join(val, joiner=''):
        return joiner.join(val)

if hasattr(datetime.timedelta, 'total_seconds'):
    total_seconds = datetime.timedelta.total_seconds

else:
    def total_seconds(td):
        return (td.microseconds +
                            (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6


def TAttrDict(default=None):
    class AttrDict(object):
        def __init__(self, *args, **kwargs):
            self.__data = dict(*args, **kwargs)

        def __call__(self, **kwargs):
            retval = AttrDict(self.__data.items())
            for k,v in kwargs.items():
                setattr(retval, k, v)
            return retval

        def __setattr__(self, key, value):
            if key == "_AttrDict__data":
                return object.__setattr__(self, key, value)
            if key == 'items':
                raise ValueError("'items' is part of dict interface")
            self.__data[key] = value

        def __setitem__(self, key, value):
            self.__data[key] = value

        def __iter__(self):
            return iter(self.__data)

        def items(self):
            return self.__data.items()

        def get(self, key, *args):
            return self.__data.get(key, *args)

        def update(self, d):
            return self.__data.update(d)

        def __repr__(self):
            return "AttrDict(%s)" % ', '.join(['%s=%r' % (k, v)
                    for k,v in sorted(self.__data.items(), key=lambda x:x[0])])

        if default is None:
            def __getattr__(self, key):
                return self.__data[key]
            def __getitem__(self, key):
                return self.__data[key]
        else:
            def __getitem__(self, key):
                if key in self.__data:
                    return self.__data[key]
                else:
                    return default()
            def __getattr__(self, key):
                if key in ("_AttrDict__data", 'items', 'get', 'update'):
                    return object.__getattribute__(self, '__data')
                if key in self.__data:
                    return self.__data[key]
                else:
                    return default()

    return AttrDict

AttrDict = TAttrDict()
DefaultAttrDict = TAttrDict(lambda: None)


class AttrDictColl(object):
    AttrDictImpl = DefaultAttrDict
    def __init__(self, *args):
        for a in args:
            setattr(self, a, AttrDictColl.AttrDictImpl(NAME=a))
