
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
logger = logging.getLogger(__name__)

from spyne.util import six

from spyne.util.coopmt import keepfirst
from spyne.util.coopmt import coroutine
from spyne.util.coopmt import Break

from spyne.util.memo import memoize
from spyne.util.memo import memoize_first
from spyne.util.memo import memoize_ignore
from spyne.util.memo import memoize_ignore_none
from spyne.util.memo import memoize_id

from spyne.util.attrdict import AttrDict
from spyne.util.attrdict import AttrDictColl
from spyne.util.attrdict import DefaultAttrDict

from spyne.util._base import utctime
from spyne.util._base import get_version


try:
    import thread

    from urllib import splittype, splithost, quote, urlencode
    from urllib2 import urlopen, Request, HTTPError

except ImportError: # Python 3
    import _thread as thread

    from urllib.parse import splittype, splithost, quote, urlencode
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError


def split_url(url):
    """Splits a url into (uri_scheme, host[:port], path)"""
    scheme, remainder = splittype(url)
    host, path = splithost(remainder)
    return scheme.lower(), host, path


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


if six.PY2:
    def _bytes_join(val, joiner=''):
        return joiner.join(val)
else:
    def _bytes_join(val, joiner=b''):
        if isinstance(val, six.binary_type):
            return val
        return joiner.join(val)


def utf8(s):
    if isinstance(s, bytes):
        return s.decode('utf8')

    if isinstance(s, list):
        return [utf8(ss) for ss in s]

    if isinstance(s, tuple):
        return tuple([utf8(ss) for ss in s])

    if isinstance(s, set):
        return {utf8(ss) for ss in s}

    if isinstance(s, frozenset):
        return frozenset([utf8(ss) for ss in s])

    return s
