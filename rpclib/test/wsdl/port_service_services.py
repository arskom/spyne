
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

class S1(ServiceBase):
    name = 'S1Fools'
    __namespace__ = 'Hippity'

    @rpc(String, _returns=String)
    def echo_string_s1(self, string):
        return string

class S2(ServiceBase):
    name = 'S2Fools'
    __namespace__ = 'Hoppity'

    @rpc(String, _returns=String)
    def bobs(self, string):
        return string

class S3(ServiceBase):
    name = 'S3Fools'
    __namespace__ = 'Hoppity'
    __service_name__ = 'BlahService'
    __port_types__ = ['bobhope', 'larry']


    @rpc(String, _returns=String)
    def echo(self, string):
        return string

    @rpc(String, _soap_port_type='bobhope', _returns=String)
    def echo_bob_hope(self,  string):
        return 'Bob Hope'

class MissingRPCPortService(ServiceBase):
    name = 'MissingRPCPortService'
    __namespace__ = 'MissingRPCPortService'
    __service_name__ = 'MissingRPCPortService'
    __port_types__ = ['existing']

    @rpc(String, _returns=String)
    def raise_exception(self, string):
        return string

class BadRPCPortService(ServiceBase):
    name = 'MissingRPCPortService'
    __namespace__ = 'MissingRPCPortService'
    __service_name__ = 'MissingRPCPortService'
    __port_types__ = ['existing']

    @rpc(String, _soap_port_type='existingss', _returns=String)
    def raise_exception(self, string):
        return string

class MissingServicePortService(ServiceBase):
    name = 'MissingRPCPortService'
    __namespace__ = 'MissingRPCPortService'
    __service_name__ = 'MissingRPCPortService'
    __port_types__ = ['existing']

    @rpc(String, _soap_port_type='existingss', _returns=String)
    def raise_exception(self, string):
        return string

class SinglePortService(ServiceBase):
    name = 'SinglePort'
    __service_name__ = 'SinglePortService_ServiceInterface'
    __namespace__ = 'SinglePortNS'
    __port_types__ = ['FirstPortType']

    @rpc(String, _soap_port_type='FirstPortType', _returns=String)
    def echo_default_port_service(self, string):
        return string

class DoublePortService(ServiceBase):
    name = 'DoublePort'
    __namespace__ = 'DoublePort'
    __port_types__ = ['FirstPort', 'SecondPort']

    @rpc(String, _soap_port_type='FirstPort', _returns=String)
    def echo_first_port(self, string):
        return string

    @rpc(String, _soap_port_type='SecondPort', _returns=String)
    def echo_second_port(self, string):
        return string
