# encoding: utf8
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

# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

import sys
import time

from time import strftime
from time import gmtime
from collections import deque

# This is a modified version of twisted's addCookie


def generate_cookie(k, v, max_age=None, domain=None, path=None,
                                       comment=None, secure=False):
    """Generate a HTTP response cookie. No sanity check whatsoever is done,
    don't send anything other than ASCII.

    :param k: Cookie key.
    :param v: Cookie value.
    :param max_age: Seconds.
    :param domain: Domain.
    :param path: Path.
    :param comment: Whatever.
    :param secure: If true, appends 'Secure' to the cookie string.
    """

    retval = deque(['%s=%s' % (k, v)])

    if max_age is not None:
        retval.append("Max-Age=%d" % max_age)
        assert time.time() < sys.maxint

        expires = time.time() + max_age
        expires = min(2<<30, expires) - 1  # FIXME
        retval.append("Expires=%s" % strftime("%a, %d %b %Y %H:%M:%S GMT",
                                                               gmtime(expires)))
    if domain is not None:
        retval.append("Domain=%s" % domain)
    if path is not None:
        retval.append("Path=%s" % path)
    if comment is not None:
        retval.append("Comment=%s" % comment)
    if secure:
        retval.append("Secure")

    return '; '.join(retval)
