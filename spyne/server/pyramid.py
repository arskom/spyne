# encoding: utf-8
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

"""The ``spyne.server.pyramid`` module contains a Pyramid-compatible Http
transport. It's a thin wrapper around
:class:`spyne.server.wsgi.WsgiApplication`.
"""

from __future__ import absolute_import

from pyramid.response import Response
from spyne.server.wsgi import WsgiApplication


class PyramidApplication(WsgiApplication):
    """Pyramid View Wrapper. Use this for regular RPC"""

    def __call__(self, request):
        retval = Response()

        def start_response(status, headers):
            status, reason = status.split(' ', 1)

            retval.status_int = int(status)
            for header, value in headers:
                retval.headers[header] = value

        response = WsgiApplication.__call__(self, request.environ,
                                            start_response)
        retval.body = b"".join(response)

        return retval

    def set_response(self, retval, response):
        retval.body = b"".join(response)


class StreamingPyramidApplication(WsgiApplication):
    """You should use this when you're generating HUGE data as response."""

    def set_response(self, retval, response):
        retval.app_iter = response
