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

from soaplib.model.primitive import String
from soaplib.service import soap, DefinitionBase

class S1(DefinitionBase):
    name = 'S1Fools'
    namespace = 'Hippity'

    @soap(String, _returns=String)
    def echo_string_s1(self, string):
        return string


class S2(DefinitionBase):
    name = 'S2Fools'
    namespace = 'Hoppity'

    @soap(String, _returns=String)
    def bobs(self, string):
        return string 


class S3(DefinitionBase):

    name = 'S3Fools'
    namespace = 'Hoppity'
    service_interface = 'BLAHHHHAHHHAHHHHA'
    port_types = ['bobhope', 'larry']


    @soap(String, _returns=String)
    def echo(self, string):
        return string

    @soap(String, _port_type='bobhope', _returns=String)
    def echo_bob_hope(self,  string):
        return 'Bob Hope'



class MissingRPCPortService(DefinitionBase):

    name = 'MissingRPCPortService'
    namespace = 'MissingRPCPortService'
    service_interface = 'MissingRPCPortService'
    port_types = ['existing']

    @soap(String, _returns=String)
    def raise_exception(self, string):
        return string

class BadRPCPortService(DefinitionBase):
    name = 'MissingRPCPortService'
    namespace = 'MissingRPCPortService'
    service_interface = 'MissingRPCPortService'
    port_types = ['existing']

    @soap(String,_port_type='existingss', _returns=String)
    def raise_exception(self, string):
        return string

#MissingServicePortService
class MissingServicePortService(DefinitionBase):
    name = 'MissingRPCPortService'
    namespace = 'MissingRPCPortService'
    service_interface = 'MissingRPCPortService'
    port_types = ['existing']

    @soap(String,_port_type='existingss', _returns=String)
    def raise_exception(self, string):
        return string


class SinglePortService(DefinitionBase):
    name = 'SinglePort'
    service_interface = 'SinglePortService_ServiceInterface'
    namespace = 'SinglePortNS'
    port_types = ['FirstPortType']

    @soap(String, _port_type='FirstPortType', _returns=String)
    def echo_default_port_service(self, string):
        return string


class DoublePortService(DefinitionBase):

    name = 'DoublePort'
    namespace = 'DoublePort'
    port_types = ['FirstPort', 'SecondPort']

    @soap(String, _port_type='FirstPort', _returns=String)
    def echo_first_port(self, string):
        return string

    @soap(String,_port_type='SecondPort', _returns=String)
    def echo_second_port(self, string):
        return string