
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


"""The Django client transport for testing Spyne apps the way you'd test Django
apps."""


from __future__ import absolute_import

from spyne import RemoteService, ClientBase, RemoteProcedureBase

from django.test.client import Client


class _RemoteProcedure(RemoteProcedureBase):
    def __init__(self, url, app, name, out_header=None, *args, **kwargs):
        super(_RemoteProcedure, self).__init__(url, app, name, out_header=out_header)

        self.secure = kwargs.get('secure', False)

    def __call__(self, *args, **kwargs):
        response = self.get_django_response(*args, **kwargs)
        code = response.status_code
        self.ctx.in_string = [response.content]

        # this sets ctx.in_error if there's an error, and ctx.in_object if
        # there's none.
        self.get_in_object(self.ctx)

        if not (self.ctx.in_error is None):
            raise self.ctx.in_error
        elif code >= 400:
            raise self.ctx.in_error
        else:
            return self.ctx.in_object

    def get_django_response(self, *args, **kwargs):
        """Return Django ``HttpResponse`` object as RPC result."""
        # there's no point in having a client making the same request more than
        # once, so if there's more than just one context, it is a bug.
        # the comma-in-assignment trick is a general way of getting the first
        # and the only variable from an iterable. so if there's more than one
        # element in the iterable, it'll fail miserably.
        self.ctx, = self.contexts

        # sets ctx.out_object
        self.get_out_object(self.ctx, args, kwargs)

        # sets ctx.out_string
        self.get_out_string(self.ctx)

        out_string = b''.join(self.ctx.out_string)
        # Hack
        client = Client()
        return client.post(self.url, content_type='text/xml', data=out_string, secure=self.secure)


class DjangoTestClient(ClientBase):
    """The Django test client transport."""

    def __init__(self, url, app, secure=False):
        super(DjangoTestClient, self).__init__(url, app)

        self.service = RemoteService(_RemoteProcedure, url, app, secure=secure)
