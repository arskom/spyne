
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
        http_resp_headers = {
            'Content-Type': 'text/xml',
            'Content-Length': '0',
        }
        return_code = HTTP_200

        # implementation hook
        self.on_wsgi_call(req_env)

        http_payload, charset = _reconstruct_soap_request(req_env)

        ctx = soaplib.MethodContext()

        result_raw = None
        try:
            params = self.deserialize_soap(ctx, http_payload, self.IN_WRAPPER,
                                                                        charset)
        except Fault,e:
            result_raw = e

        if ctx.service is None:
            envelope_xml = self.serialize_soap(ctx, params, self.OUT_WRAPPER)
            envelope_str = etree.tostring(envelope_xml, xml_declaration=True,
                                                       encoding=string_encoding)
            return_code = HTTP_500

        else:
            if result_raw is None:
                result_raw = self.process_request(ctx, params)

            if isinstance(result_raw, Exception):
                return_code = HTTP_500

            envelope_xml = self.serialize_soap(ctx, result_raw,
                                                        Application.OUT_WRAPPER)
            envelope_str = etree.tostring(envelope_xml, xml_declaration=True,
                                                       encoding=string_encoding)

            # implementation hook
            self.on_wsgi_return(req_env, http_resp_headers, envelope_str)

            if ctx.descriptor.mtom:
                http_resp_headers, envelope_str = apply_mtom(http_resp_headers,
                        envelope_str, ctx.descriptor.out_message._type_info,
                        [result_raw])

        # initiate the response
        http_resp_headers['Content-Length'] = str(len(envelope_str))
        start_response(return_code, http_resp_headers.items())

        return [envelope_str]

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
