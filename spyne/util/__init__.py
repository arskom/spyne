
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

import sys

try:
    from urllib import splittype
    from urllib import splithost
    from urllib import quote

except ImportError: # Python 3
    from urllib.parse import splittype
    from urllib.parse import splithost
    from urllib.parse import quote


def split_url(url):
    '''Splits a url into (uri_scheme, host[:port], path)'''
    scheme, remainder = splittype(url)
    host, path = splithost(remainder)
    return scheme.lower(), host, path


def reconstruct_url(environ):
    '''
    Rebuilds the calling url from values found in the
    environment.

    This algorithm was found via PEP 333, the wsgi spec and
    contributed by Ian Bicking.
    '''

    url = environ['wsgi.url_scheme'] + '://'

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

    if (quote(environ.get('SCRIPT_NAME', '')) == '/' and
        quote(environ.get('PATH_INFO', ''))[0] == '/'):
        #skip this if it is only a slash
        pass

    elif quote(environ.get('SCRIPT_NAME', ''))[0:2] == '//':
        url += quote(environ.get('SCRIPT_NAME', ''))[1:]

    else:
        url += quote(environ.get('SCRIPT_NAME', ''))

    url += quote(environ.get('PATH_INFO', ''))
    if environ.get('QUERY_STRING'):
        url += '?' + environ['QUERY_STRING']

    return url


def check_pyversion(*minversion):
    return sys.version_info[:3] >= minversion


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
    def get_key(self, args, kwargs):
        return tuple([id(a) for a in args]), \
                                    tuple([ (k,id(v)) for k,v in kwargs.items()])


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


if sys.version > '3':
    def _bytes_join(val, joiner=''):
        return bytes(joiner).join(val)
else:
    def _bytes_join(val, joiner=''):
        return joiner.join(val)
