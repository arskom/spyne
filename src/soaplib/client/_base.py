
from soaplib.model.exception import Fault

from lxml import etree
from soaplib import MethodContext
from soaplib.model.primitive import string_encoding

class Factory(object):
    def __init__(self, app):
        self.__app = app

    def create(self, object_name):
        return self.__app.get_class_instance(object_name)

class Service(object):
    def __init__(self, rpc_class, url, app):
        self.__app = app
        self.__url = url
        self.out_header = None
        self.rpc_class = rpc_class

    def __getattr__(self, key):
        return self.rpc_class(self.__url, self.__app, key, self.out_header)

class RemoteProcedureBase(object):
    def __init__(self, url, app, name, out_header):
        self.url = url
        self.app = app

        self.ctx = MethodContext()
        self.ctx.method_name = name
        self.ctx.service_class = self.app.get_service_class(name)
        self.ctx.service = self.app.get_service(self.ctx.service_class)
        self.ctx.service.out_header = out_header
        self.ctx.descriptor = self.ctx.service.get_method(self.ctx.method_name)

    def get_out_object(self, args, kwargs):
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

        return request_raw

    def get_out_string(self, out_object):
        request_xml = self.app.serialize_soap(self.ctx, out_object,
                                                            self.app.NO_WRAPPER)
        request_str = etree.tostring(request_xml,
            xml_declaration=True,
            encoding=string_encoding
        )

        return request_str

    def get_in_object(self, response_str, is_error=False):
        #response_xml = self.decompose_incoming_envelope(self.ctx, response_str)
        wrapped_response = self.app.deserialize_soap(self.ctx, response_str,
                                                           self.app.OUT_WRAPPER)

        if isinstance(wrapped_response, Fault) or is_error:
            raise wrapped_response

        else:
            type_info = self.ctx.descriptor.out_message._type_info

            if len(self.ctx.descriptor.out_message._type_info) == 1:
                wrapper_attribute = type_info.keys()[0]
                response_raw = getattr(wrapped_response, wrapper_attribute, None)

                return response_raw
            else:
                return wrapped_response

class Base(object):
    def __init__(self, url, app):
        """ Must be overridden to initialize the service properly"""
        self.factory = Factory(app)

    def set_options(self, **kwargs):
        self.service.out_header = kwargs.get('soapheaders', None)
