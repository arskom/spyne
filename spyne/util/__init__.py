
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

from spyne.model.complex import Array
from spyne.const import MAX_STRING_FIELD_LENGTH
from spyne.const import MAX_ARRAY_ELEMENT_NUM

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
        key = (tuple(args), tuple(kwargs.items()))
        if not key in self.memo:
            self.memo[key] = self.func(*args, **kwargs)
        return self.memo[key]

    def reset(self):
        self.memo = {}

def safe_repr(obj, cls=None):
    """Use this function if you want to echo a ComplexModel subclass. It will
    limit output size of the String types, thus make your logs smaller.
    """

    if cls is None:
        cls = obj.__class__

    if issubclass(cls, Array):
        retval = []

        cls, = cls._type_info.values()
        for i,o in enumerate(obj):
            retval.append(_safe_repr_obj(o, cls))

            if i > MAX_ARRAY_ELEMENT_NUM:
                retval.append("(...)")
                break

        return "%s([%s])" % (cls.get_type_name(), ', '.join(retval))

    else:
        return _safe_repr_obj(obj, cls)

def _safe_repr_obj(obj, cls):
    retval = []
    for k,t in cls.get_flat_type_info(cls).items():
        v = getattr(obj, k, None)
        if v is not None:
            if issubclass(t, Unicode) and len(v) > MAX_STRING_FIELD_LENGTH:
                s = '%s=%r%s' % (k, v[:MAX_STRING_FIELD_LENGTH] , "(...)")
            else:
                s = '%s=%r' % (k, v)

            retval.append(s)

    return "%s(%s)" % (cls.get_type_name(), ', '.join(retval))

from spyne.model.primitive import Unicode
