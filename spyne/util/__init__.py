
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

import sys
import datetime

from spyne.util import six

from spyne.util.six import PY3

from spyne.util.coopmt import coroutine
from spyne.util.coopmt import Break

from spyne.util.memo import memoize
from spyne.util.memo import memoize_id
from spyne.util.memo import memoize_id_method

from spyne.util.attrdict import AttrDict
from spyne.util.attrdict import AttrDictColl
from spyne.util.attrdict import DefaultAttrDict

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


def check_pyversion(*minversion):
    return sys.version_info[:3] >= minversion


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

