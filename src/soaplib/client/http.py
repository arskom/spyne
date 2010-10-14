
#
# soaplib - Copyright (C) Soaplib contributors.
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

"""A soap client that uses http (urllib2) as transport"""

import urllib2

from soaplib.client import Service
from soaplib.client import ClientBase
from soaplib.client import RemoteProcedureBase

class _RemoteProcedure(RemoteProcedureBase):
    def __call__(self, *args, **kwargs):
        out_str = self.get_out_string(args, kwargs)

        request = urllib2.Request(self.url, out_str)
        code=200
        try:
            response = urllib2.urlopen(request)
            in_str = response.read()

        except urllib2.HTTPError,e:
            code=e.code
            in_str = e.read()

        return self.get_in_object(in_str, is_error=(code == 500))

class Client(ClientBase):
    def __init__(self, url, app):
        super(Client, self).__init__(url, app)

        self.service = Service(_RemoteProcedure, url, app)
