
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

import cgi
import logging
logger = logging.getLogger('soaplib')

import traceback

from lxml import etree

from soaplib.serializers.exception import Fault
from soaplib.serializers.primitive import string_encoding

from soaplib.soap import apply_mtom
from soaplib.soap import collapse_swa
from soaplib.soap import from_soap
from soaplib.soap import make_soap_envelope
from soaplib.soap import make_soap_fault
from soaplib.util import reconstruct_url

class ValidationError(Exception):
    pass

class AppBase(object):
    def __init__(self, service):
        '''
        @param A ServiceBase subclass that defines the exposed services.
        '''

        self.service = service

        self.__wsdl = None
        self.__schema = None

        self.__get_schema(self.get_service(None))

    def get_service(self, environment):
        return self.service(environment)

    def __get_wsdl(self, service, url):
        retval = self.__wsdl

        if retval is None:
            retval = self.__wsdl = service.get_wsdl(url)

        return retval

    def __get_schema(self, service):
        retval = self.__schema

        if retval is None:
            retval = self.__schema = service.get_schema()

        return retval

    def __call__(self, req_env, start_response, wsgi_url=None):
        '''
        This method conforms to the WSGI spec for callable wsgi applications
        (PEP 333). It looks in environ['wsgi.input'] for a fully formed soap
        request envelope, will deserialize the request parameters and call the
        method on the object returned by the get_handler() method.

        @param the http environment
        @param a callable that begins the response message
        @param the optional url
        @returns the string representation of the soap call
        '''

        method_name = ''
        http_resp_headers = {'Content-Type': 'text/xml'}
        soap_resp_headers = []

        # cache the wsdl
        service_name = req_env['PATH_INFO'].split('/')[-1]
        service = self.get_service(req_env)
        url = wsgi_url
        if url is None:
            url = reconstruct_url(req_env).split('.wsdl')[0]

        try:
            # implementation hook
            service.on_call(req_env)

            if req_env['REQUEST_METHOD'].lower() == 'get' and (
                    req_env['QUERY_STRING'].endswith('wsdl')
                 or req_env['PATH_INFO'].endswith('wsdl') ):

                # Get the wsdl for the service. Assume path_info matches pattern:
                # /stuff/stuff/stuff/serviceName.wsdl or
                # /stuff/stuff/stuff/serviceName/?wsdl
                service_name = service_name.split('.')[0]

                start_response('200 OK', http_resp_headers.items())
                try:
                    wsdl_content = self.__get_wsdl(service,url)

                    # implementation hook
                    service.on_wsdl(req_env, wsdl_content)

                except Exception, e:
                    # implementation hook
                    logger.error(traceback.format_exc())

                    fault_xml = make_soap_fault(str(e), service.get_tns(), detail="")
                    fault_str = etree.tostring(fault_xml,
                           xml_declaration=True, encoding=string_encoding)
                    logger.debug(fault_str)

                    service.on_wsdl_exception(req_env, e, fault_str)

                    # initiate the response
                    http_resp_headers['Content-length'] = str(len(fault_str))
                    start_response('500 Internal Server Error',
                        http_resp_headers.items())

                    return [fault_str]

                return [wsdl_content]

            if req_env['REQUEST_METHOD'].lower() != 'post':
                start_response('405 Method Not Allowed', [('Allow', 'POST')])
                return ''

            input = req_env.get('wsgi.input')
            length = req_env.get("CONTENT_LENGTH")
            body = input.read(int(length))
            logger.debug(body)

            #
            # decode body using information in the http header
            #
            # fyi, here's what the parse_header function returns:
            # >>> import cgi; cgi.parse_header("text/xml; charset=utf-8")
            # ('text/xml', {'charset': 'utf-8'})
            #
            content_type = cgi.parse_header(req_env.get("CONTENT_TYPE"))
            charset = content_type[1].get('charset',None)
            if charset is None:
                charset = 'ascii'

            body = body.decode(charset)
            body = collapse_swa(content_type, body)

            # deserialize the body of the message
            soap_req_payload, soap_req_header = from_soap(body)
            service.soap_req_header = soap_req_header

            # if there's a schema to validate against, validate the response
            schema = self.__get_schema(service)
            if schema != None:
                ret = schema.validate(soap_req_payload)
                logger.debug("validation result: %s" % str(ret))
                if ret == False:
                    raise ValidationError(schema.error_log.last_error)

            if soap_req_payload is not None and len(soap_req_payload) > 0:
                method_name = soap_req_payload.tag
            else:
                # check HTTP_SOAPACTION
                method_name = req_env.get("HTTP_SOAPACTION")
                if method_name.startswith('"') and method_name.endswith('"'):
                    method_name = method_name[1:-1]
                if method_name.find('/') >0:
                    method_name = method_name.split('/')[1]

            if not (method_name is None):
                logger.debug('\033[92m'+ method_name +'\033[0m')

            # retrieve the method descriptor
            descriptor = service.get_method(method_name)
            func = getattr(service, descriptor.name)

            if soap_req_payload is not None and len(soap_req_payload) > 0:
                params = descriptor.in_message.from_xml(*[soap_req_payload])
            else:
                params = ()

            # implementation hook
            service.on_method_exec(req_env, method_name, params, body)

            # call the method
            result_raw = func(*params)

            # create result message
            assert len(descriptor.out_message._type_info) == 1

            result_message = descriptor.out_message()
            attr_name = descriptor.out_message._type_info.keys()[0]
            setattr(result_message, attr_name, result_raw)

            # transform the results into an element
            # only expect a single element
            results_soap = None
            if not (descriptor.is_async or descriptor.is_callback):
                results_soap = descriptor.out_message.to_xml(result_message,
                                                              service.get_tns())

            # implementation hook
            service.on_results(req_env, result_raw, results_soap,
                                                          soap_resp_headers)

            # construct the soap response, and serialize it
            envelope = make_soap_envelope(results_soap, tns=service.get_tns(),
                                          header_elements=soap_resp_headers)
            results_str = etree.tostring(envelope, xml_declaration=True,
                                                       encoding=string_encoding)

            if descriptor.mtom:
                http_resp_headers, results_str = apply_mtom(http_resp_headers,
                    results_str,descriptor.out_message._type_info,[result_raw])

            service.on_return(req_env, http_resp_headers, results_str)

            # initiate the response
            start_response('200 OK', http_resp_headers.items())

            logger.debug('\033[91m'+ "Response" + '\033[0m')
            logger.debug(etree.tostring(envelope, xml_declaration=True,
                                                             pretty_print=True))

            # return the serialized results
            return [results_str]

        except Fault, e:
            # FIXME: There's no way to alter soap response headers for the user.

            # The user issued a Fault, so handle it just like an exception!
            fault_xml = make_soap_fault(
                service.get_tns(),
                e.faultstring,
                e.faultcode,
                e.detail,
                header_elements=soap_resp_headers)

            fault_str = etree.tostring(fault_xml, xml_declaration=True,
                                                    encoding=string_encoding)
            logger.error(fault_str)

            service.on_exception(req_env, http_resp_headers, e, fault_str)

            # initiate the response
            start_response('500 Internal Server Error',http_resp_headers.items())

            return [fault_str]

        except Exception, e:
            # Dump the stack trace to a buffer to be sent
            # back to the caller

            # capture stacktrace
            stacktrace=traceback.format_exc()

            # psycopg specific
            if hasattr(e,'statement') and hasattr(e,'params'):
                e.statement=""
                e.params={}

            faultstring = str(e)

            if method_name:
                faultcode = '%sFault' % method_name
            else:
                faultcode = 'Server'

            detail = ' '
            logger.error(stacktrace)

            fault_xml = make_soap_fault(service.get_tns(), faultstring,
                                                              faultcode, detail)
            fault_str = etree.tostring(fault_xml, xml_declaration=True,
                                                       encoding=string_encoding)
            logger.debug(fault_str)

            service.on_exception(req_env, e, fault_str)

            # initiate the response
            start_response('500 Internal Server Error',http_resp_headers.items())
            return [fault_str]
