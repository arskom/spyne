
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

"""Helpers for protocol boilerplate."""

from spyne import MethodContext
from spyne.server import ServerBase


def deserialize_request_string(string, app):
    """Deserialize request string using in_protocol in application definition.
    Returns the corresponding native python object.
    """

    server = ServerBase(app)
    initial_ctx = MethodContext(server)
    initial_ctx.in_string = [string]

    ctx = server.generate_contexts(initial_ctx)[0]
    server.get_in_object(ctx)
    return ctx.in_object
