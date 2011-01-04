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

from soaplib.core.model.primitive import String
from soaplib.core.service import soap, DefinitionBase

class S1(DefinitionBase):
    name = 'S1Fools'
    __namespace__ = 'Hippity'

    @soap(String, _returns=String)
    def echo_string_s1(self, string):
        return string


class S2(DefinitionBase):
    name = 'S2Fools'
    __namespace__ = 'Hoppity'

    @soap(String, _returns=String)
    def bobs(self, string):
        return string 


class S3(DefinitionBase):

    name = 'S3Fools'
    __namespace__ = 'Hoppity'
    __service_interface__ = 'BLAHHHHAHHHAHHHHA'
    __port_types__ = ['bobhope', 'larry']


    @soap(String, _returns=String)
    def echo(self, string):
        return string

    @soap(String, _port_type='bobhope', _returns=String)
    def echo_bob_hope(self,  string):
        return 'Bob Hope'



class MissingRPCPortService(DefinitionBase):

    name = 'MissingRPCPortService'
    __namespace__ = 'MissingRPCPortService'
    __service_interface__ = 'MissingRPCPortService'
    __port_types__ = ['existing']

    @soap(String, _returns=String)
    def raise_exception(self, string):
        return string

class BadRPCPortService(DefinitionBase):
    name = 'MissingRPCPortService'
    __namespace__ = 'MissingRPCPortService'
    __service_interface__ = 'MissingRPCPortService'
    __port_types__ = ['existing']

    @soap(String,_port_type='existingss', _returns=String)
    def raise_exception(self, string):
        return string

#MissingServicePortService
class MissingServicePortService(DefinitionBase):
    name = 'MissingRPCPortService'
    __namespace__ = 'MissingRPCPortService'
    __service_interface__ = 'MissingRPCPortService'
    __port_types__ = ['existing']

    @soap(String,_port_type='existingss', _returns=String)
    def raise_exception(self, string):
        return string


class SinglePortService(DefinitionBase):
    name = 'SinglePort'
    __service_interface__ = 'SinglePortService_ServiceInterface'
    __namespace__ = 'SinglePortNS'
    __port_types__ = ['FirstPortType']

    @soap(String, _port_type='FirstPortType', _returns=String)
    def echo_default_port_service(self, string):
        return string


class DoublePortService(DefinitionBase):

    name = 'DoublePort'
    __namespace__ = 'DoublePort'
    __port_types__ = ['FirstPort', 'SecondPort']

    @soap(String, _port_type='FirstPort', _returns=String)
    def echo_first_port(self, string):
        return string

    @soap(String,_port_type='SecondPort', _returns=String)
    def echo_second_port(self, string):
        return string