# encoding: utf-8
#
# rpclib - Copyright (C) Rpclib contributors.
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

from django.http import HttpResponse
from rpclib.server.wsgi import WsgiApplication

class DjangoApplication(WsgiApplication):
    def __call__(self, request):
        django_response = HttpResponse()

        def start_response(status, headers):
            status, reason = status.split(' ', 1)

            django_response.status_code = int(status)
            for header, value in headers:
                django_response[header] = value

        environ = request.META.copy()
        environ['wsgi.input'] = request
        environ['wsgi.multithread'] = False

        response = WsgiApplication.__call__(self, environ, start_response)

        django_response.content = "\n".join(response)

        return django_response
