
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

"""A soap client that uses http as transport"""

import urllib2

class _Factory(object):
    def __init__(self, app):
        self.__app = app

    def create(self, object_name):
        return self.__app

class _Service(object):
    def __init__(self, url, app):
        self.__app = app
        self.__url = url

    def __getattr__(self, key):
        return _RemoteProcedureCall(self.__url, key)

class _RemoteProcedureCall(object):
    def __init__(self, url, name):
        self.name = name
        self.url = url

    def __call__(self, *args, **kwargs):
        request_str = "" # TODO: fill this using args and kwargs

        request = urllib2.Request(self.url, request_str)
        response = urllib2.urlopen(request)

        response_str = response.read()

        return "punk" # TODO: return the above serialized

class Client(object):
    def __init__(self, url, app):
        self.service = _Service(url, app)
        self.factory = _Factory(app)
