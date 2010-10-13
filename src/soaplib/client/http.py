
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

from lxml import etree

from soaplib import MethodContext
from soaplib.type.primitive import string_encoding

class _Factory(object):
    def __init__(self, app):
        self.__app = app

    def create(self, object_name):
        return self.__app.get_class_instance(object_name)

class _Service(object):
    def __init__(self, url, app):
        self.__app = app
        self.__url = url

    def __getattr__(self, key):
        return _RemoteProcedureCall(self.__url, self.__app, key)

class _RemoteProcedureCall(object):
    def __init__(self, url, app, name):
        self.url = url
        self.app = app

        self.ctx = MethodContext()
        self.ctx.method_name = name
        self.ctx.service_class = self.app.get_service_class(name)
        self.ctx.service = self.app.get_service(self.ctx.service_class)
        self.ctx.descriptor = self.ctx.service.get_method(self.ctx.method_name)

    def __call__(self, *args, **kwargs):
        request_raw_class = self.ctx.descriptor.in_message
        request_type_info = request_raw_class._type_info
        request_raw = request_raw_class()

        for i in range(len(request_type_info)):
            if i < len(args):
                setattr(request_raw, request_type_info.keys()[i], args[i])
            else:
                setattr(request_raw, request_type_info.keys()[i], None)

        for k in request_type_info:
            if k in kwargs:
                setattr(request_raw, k, kwargs[k])

        request_xml = self.app.serialize_soap(self.ctx, request_raw,
                                                            self.app.NO_WRAPPER)
        request_str = etree.tostring(request_xml,
            xml_declaration=True,
            encoding=string_encoding
        )

        request = urllib2.Request(self.url, request_str)
        response = urllib2.urlopen(request)

        response_str = response.read()
        #response_xml = self.decompose_incoming_envelope(self.ctx, response_str)
        wrapped_response = self.app.deserialize_soap(self.ctx, response_str,
                                                           self.app.OUT_WRAPPER)

        wrapper_attribute = self.ctx.descriptor.out_message._type_info.keys()[0]
        response_raw = getattr(wrapped_response, wrapper_attribute, None)

        return response_raw

class Client(object):
    def __init__(self, url, app):
        self.service = _Service(url, app)
        self.factory = _Factory(app)
