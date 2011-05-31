
#
# rpclib - Copyright (C) rpclib contributors.
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

from rpclib.model.primitive import String
from rpclib.service import ServiceBase
from rpclib.decorator import rpc

class DefaultPortService(ServiceBase):
    @rpc(String, _returns=String)
    def echo_default_port_service(self, string):
        return string

class DefaultPortServiceMultipleMethods(ServiceBase):
    @rpc(String, _returns=String)
    def echo_one(self, string):
        return string

    @rpc(String, _returns=String)
    def echo_two(self, string):
        return string

    @rpc(String, _returns=String)
    def echo_three(self, string):
        return string
