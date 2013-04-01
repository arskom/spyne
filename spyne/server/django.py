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

"""The ``spyne.server.django`` module contains a Django-compatible Http
transport. It's a thin wrapper around
:class:`spyne.server.wsgi.WsgiApplication`.
"""

from __future__ import absolute_import

from django.http import HttpResponse

try:
    from django.http import StreamingHttpResponse
except ImportError, e:
    def StreamingHttpResponse(*args, **kwargs):
        raise e

from spyne.server.wsgi import WsgiApplication


class DjangoApplication(WsgiApplication):
    """You should use this for regular RPC."""

    HttpResponseObject = HttpResponse

    def __call__(self, request):
        retval = self.HttpResponseObject()

        def start_response(status, headers):
            # Status is one of spyne.const.http
            status, reason = status.split(' ', 1)

            retval.status_code = int(status)
            for header, value in headers:
                retval[header] = value

        environ = request.META.copy()

        # FIXME: No idea what these two did.
        #        They were commented out to fix compatibility issues with
        #        Django-1.2.x
        # See http://github.com/arskom/spyne/issues/222.
        #environ['wsgi.input'] = request
        #environ['wsgi.multithread'] = False

        response = WsgiApplication.__call__(self, environ, start_response)
        self.set_response(retval, response)

        return retval

    def set_response(self, retval, response):
        retval.content = ''.join(response)


class StreamingDjangoApplication(DjangoApplication):
    """You should use this when you're generating HUGE data as response.
    This is new in Django 1.5.
    """

    HttpResponseObject = StreamingHttpResponse

    def set_response(self, retval, response):
        retval.streaming_content = response
