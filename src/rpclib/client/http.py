
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

"""The HTTP (urllib2) client transport."""

try:
    from urllib2 import Request
    from urllib2 import urlopen
    from urllib2 import HTTPError

except ImportError: # Python 3
    from urllib.request import Request
    from urllib.request import urlopen
    from urllib.error import HTTPError

from rpclib.client import Service
from rpclib.client import ClientBase
from rpclib.client import RemoteProcedureBase

class _RemoteProcedure(RemoteProcedureBase):
    def __call__(self, *args, **kwargs):
        # there's no point in the client making the same request over and over
        # again.
        self.ctx = self.contexts[0]

        self.get_out_object(self.ctx, args, kwargs) # sets ctx.out_object
        self.get_out_string(self.ctx) # sets ctx.out_string

        out_string = ''.join(self.ctx.out_string) # FIXME: just send the iterable to the http stream.
        request = Request(self.url, out_string)
        code = 200
        try:
            response = urlopen(request)
            self.ctx.in_string = [response.read()]

        except HTTPError, e:
            code = e.code
            self.ctx.in_string = [e.read()]

        self.get_in_object(self.ctx)

        if not (self.ctx.in_error is None):
            raise self.ctx.in_error
        elif code >= 400:
            raise self.ctx.in_error
        else:
            return self.ctx.in_object

class HttpClient(ClientBase):
    def __init__(self, url, app):
        super(HttpClient, self).__init__(url, app)

        self.service = Service(_RemoteProcedure, url, app)
