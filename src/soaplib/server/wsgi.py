
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

"""A soap server that uses http as transport, and wsgi as bridge api"""

from lxml import etree

import logging
logger = logging.getLogger(__name__)

import cgi
import traceback

import soaplib

from soaplib.type.exception import Fault
from soaplib.type.primitive import string_encoding

from soaplib.mime import apply_mtom
from soaplib.mime import collapse_swa
from soaplib.util import reconstruct_url

HTTP_500 = '500 Internal server error'
HTTP_200 = '200 OK'
HTTP_405 = '405 Method Not Allowed'

class ValidationError(Fault):
    pass

def _reconstruct_soap_request(http_env):
    """Reconstruct http payload using information in the http header
    """

    input = http_env.get('wsgi.input')
    length = http_env.get("CONTENT_LENGTH")
    http_payload = input.read(int(length))

    # fyi, here's what the parse_header function returns:
    # >>> import cgi; cgi.parse_header("text/xml; charset=utf-8")
    # ('text/xml', {'charset': 'utf-8'})
    content_type = cgi.parse_header(http_env.get("CONTENT_TYPE"))
    charset = content_type[1].get('charset',None)
    if charset is None:
        charset = 'ascii'

    return collapse_swa(content_type, http_payload), charset

class Application(soaplib.Application):
    transport = 'http://schemas.xmlsoap.org/soap/http'

    def __call__(self, req_env, start_response, wsgi_url=None):
        '''This method conforms to the WSGI spec for callable wsgi applications
        (PEP 333). It looks in environ['wsgi.input'] for a fully formed soap
        request envelope, will deserialize the request parameters and call the
        method on the object returned by the get_handler() method.

        @param the http environment
        @param a callable that begins the response message
        @param the optional url
        @returns the string representation of the soap call
        '''

        url = wsgi_url
        if url is None:
            url = reconstruct_url(req_env).split('.wsdl')[0]

        if self.__is_wsdl_request(req_env):
            return self.__handle_wsdl_request(req_env, start_response, url)

        elif req_env['REQUEST_METHOD'].lower() != 'post':
            start_response(HTTP_405, [('Allow', 'POST')])
            return ['']

        else:
            return self.__handle_soap_request(req_env, start_response)

    def __is_wsdl_request(self, req_env):
        # Get the wsdl for the service. Assume path_info matches pattern:
        # /stuff/stuff/stuff/serviceName.wsdl or
        # /stuff/stuff/stuff/serviceName/?wsdl

        return (
            req_env['REQUEST_METHOD'].lower() == 'get'
            and (
                   req_env['QUERY_STRING'].endswith('wsdl')
                or req_env['PATH_INFO'].endswith('wsdl')
            )
        )

    def __handle_wsdl_request(self, req_env, start_response, url):
        http_resp_headers = {'Content-Type': 'text/xml'}

        try:
            self.get_wsdl(url)
            self.on_wsdl(req_env, self.__wsdl) # implementation hook

            http_resp_headers['Content-Length'] = str(len(self.__wsdl))
            start_response(HTTP_200, http_resp_headers.items())

            return [self.__wsdl]

        except Exception, e:
            logger.error(traceback.format_exc())

            # implementation hook
            self.on_wsdl_exception(req_env, e)

            start_response(HTTP_500, http_resp_headers.items())

            return [""]

    def __handle_soap_request(self, req_env, start_response):
        ctx = soaplib.MethodContext()

        # implementation hook
        self.on_wsgi_call(req_env)

        in_string, in_string_charset = _reconstruct_soap_request(req_env)

        out_object = None
        try:
            in_object = self.deserialize_soap(ctx, in_string, self.IN_WRAPPER,
                                                            in_string_charset)
        except Fault,e:
            out_object = e

        return_code = HTTP_200
        http_resp_headers = {
            'Content-Type': 'text/xml',
            'Content-Length': '0',
        }

        if ctx.service is None:
            out_xml = self.serialize_soap(ctx, in_object, self.OUT_WRAPPER)
            out_string = etree.tostring(out_xml, xml_declaration=True,
                                                       encoding=string_encoding)
            return_code = HTTP_500

        else:
            if out_object is None:
                out_object = self.process_request(ctx, in_object)

            if isinstance(out_object, Fault):
                return_code = HTTP_500
            else:
                assert not isinstance(out_object, Exception)

            out_xml = self.serialize_soap(ctx, out_object,
                                                        Application.OUT_WRAPPER)
            out_string = etree.tostring(out_xml, xml_declaration=True,
                                                       encoding=string_encoding)

            # implementation hook
            self.on_wsgi_return(req_env, http_resp_headers, out_string)

        if ctx.descriptor.mtom:
            # when there are more than one return type, the result is 
            # encapsulated inside a list. when there's just one, the result
            # is returned unencapsulated. the apply_mtom always expects the
            # objects to be inside an iterable, hence the following test.
            out_type_info = ctx.descriptor.out_message._type_info
            if len(out_type_info) == 1:
                out_object = [out_object]

            http_resp_headers, out_string = apply_mtom(http_resp_headers,
                    out_string, ctx.descriptor.out_message._type_info.values(),
                    out_object)

        # initiate the response
        http_resp_headers['Content-Length'] = str(len(out_string))
        start_response(return_code, http_resp_headers.items())

        return [out_string]

    def on_wsgi_call(self, environ):
        '''This is the first method called when this WSGI app is invoked.

        @param the wsgi environment
        '''
        pass

    def on_wsdl(self, environ, wsdl):
        '''This is called when a wsdl is requested.

        @param the wsgi environment
        @param the wsdl string
        '''
        pass

    def on_wsdl_exception(self, environ, exc):
        '''Called when an exception occurs durring wsdl generation.

        @param the wsgi environment
        @param exc the exception
        @param the fault response string
        '''
        pass

    def on_wsgi_return(self, environ, http_headers, return_str):
        '''Called before the application returns.

        @param the wsgi environment
        @param http response headers as dict
        @param return string of the soap request
        '''
        pass

class ValidatingApplication(Application, soaplib.ValidatingApplication):
    pass
