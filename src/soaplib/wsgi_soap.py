
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

import logging
import traceback

from soaplib.soap import apply_mtom
from soaplib.soap import collapse_swa
from soaplib.soap import from_soap

from lxml import etree

from soaplib.serializers.exception import Fault
from soaplib.serializers.primitive import string_encoding
from soaplib.service import ServiceBase
from soaplib.soap import apply_mtom
from soaplib.soap import collapse_swa
from soaplib.soap import make_soap_envelope
from soaplib.soap import make_soap_fault
from soaplib.util import reconstruct_url

class WSGIApp(object):
    '''
    This is the base object representing a soap web application, and conforms
    to the WSGI specification (PEP 333).  This object should be overridden
    and get_handler(environ) overridden to provide the object implementing
    the specified functionality.  Hooks have been added so that the subclass
    can react to various events that happen durring the execution of the
    request.
    '''

    def on_call(self, environ):
        '''
        This is the first method called when this WSGI app is invoked
        @param the wsgi environment
        '''
        pass

    def on_wsdl(self, environ, wsdl):
        '''
        This is called when a wsdl is requested
        @param the wsgi environment
        @param the wsdl string
        '''
        pass

    def on_wsdl_exception(self, environ, exc, resp):
        '''
        Called when an exception occurs durring wsdl generation
        @param the wsgi environment
        @param exc the exception
        @param the fault response string
        '''
        pass

    def on_method_exec(self, environ, py_params, soap_params):
        '''
        Called BEFORE the service implementing the functionality is called
        @param the wsgi environment
        @param the body element of the soap request
        @param the tuple of python params being passed to the method
        @param the soap elements for each params
        '''
        pass

    def on_results(self, environ, py_results, soap_results, soap_headers):
        '''
        Called AFTER the service implementing the functionality is called
        @param the wsgi environment
        @param the python results from the method
        @param the xml serialized results of the method
        @param soap headers as a list of lxml.etree._Element objects
        '''
        pass

    def on_exception(self, environ, exc, resp):
        '''
        Called when an error occurs durring execution
        @param the wsgi environment
        @param the exception
        @param the response string
        '''
        pass

    def on_return(self, environ, http_headers, return_str):
        '''
        Called before the application returns
        @param the wsgi environment
        @param http response headers as dict
        @param return string of the soap request
        '''
        pass

    def get_handler(self, environ):
        '''
        This method returns the object responsible for processing a given
        request, and needs to be overridden by a subclass to handle
        the application specific  mapping of the request to the appropriate
        handler.
        @param the wsgi environment
        @returns the object to be called for the soap operation
        '''
        raise Exception("Not implemented")

    def __call__(self, http_request_env, start_response, address_url=None):
        '''
        This method conforms to the WSGI spec for callable wsgi applications
        (PEP 333). It looks in environ['wsgi.input'] for a fully formed soap
        request envelope, will deserialize the request parameters and call the
        method on the object returned by the get_handler() method.
        @param the http environment
        @param a callable that begins the response message
        @returns the string representation of the soap call
        '''
        methodname = ''
        http_resp_headers = {'Content-Type': 'text/xml'}
        soap_response_headers = []

        # cache the wsdl
        service_name = http_request_env['PATH_INFO'].split('/')[-1]
        service = self.get_handler(http_request_env)
        if address_url:
            url = address_url
        else:
            url = reconstruct_url(http_request_env).split('.wsdl')[0]

        try:
            wsdl_content = service.wsdl(url)
        except:
            pass

        try:
            # implementation hook
            self.on_call(http_request_env)

            if ((http_request_env['QUERY_STRING'].endswith('wsdl') or
                 http_request_env['PATH_INFO'].endswith('wsdl')) and
                http_request_env['REQUEST_METHOD'].lower() == 'get'):

                #
                # Get the wsdl for the service. Assume path_info matches pattern:
                # /stuff/stuff/stuff/serviceName.wsdl or
                # /stuff/stuff/stuff/serviceName/?WSDL
                #
                service_name = service_name.split('.')[0]

                start_response('200 OK', http_resp_headers.items())
                try:
                    wsdl_content = service.wsdl(url)

                    # implementation hook
                    self.on_wsdl(http_request_env, wsdl_content)

                except Exception, e:
                    # implementation hook
                    logging.error(traceback.format_exc())

                    fault_str = etree.tostring(make_soap_fault(str(e),
                           self.get_tns(), detail=""), encoding=string_encoding)
                    logging.debug(fault_str)

                    self.on_wsdl_exception(http_request_env, e, fault_str)

                    # initiate the response
                    http_resp_headers['Content-length'] = str(len(fault_str))
                    start_response('500 Internal Server Error',
                        http_resp_headers.items())

                    return [fault_str]

                return [wsdl_content]

            if http_request_env['REQUEST_METHOD'].lower() != 'post':
                start_response('405 Method Not Allowed', [('Allow', 'POST')])
                return ''

            input = http_request_env.get('wsgi.input')
            length = http_request_env.get("CONTENT_LENGTH")
            body = input.read(int(length))

            methodname = http_request_env.get("HTTP_SOAPACTION")

            if not (methodname is None):
                logging.debug('\033[92m'+ methodname +'\033[0m')
            logging.debug(body)

            body = collapse_swa(http_request_env.get("CONTENT_TYPE"), body)

            # deserialize the body of the message
            request_payload, request_header = from_soap(body)

            if request_payload is not None and len(request_payload) > 0:
                methodname = request_payload.tag
            else:
                # check HTTP_SOAPACTION
                methodname = http_request_env.get("HTTP_SOAPACTION")
                if methodname.startswith('"') and methodname.endswith('"'):
                    methodname = methodname[1:-1]
                if methodname.find('/') >0:
                    methodname = methodname.split('/')[1]

            # retrieve the method descriptor
            descriptor = service.get_method(methodname)
            func = getattr(service, descriptor.name)

            if self.validating_service:
                self.validation_schema.assert_(request_payload)

            if request_payload is not None and len(request_payload) > 0:
                params = descriptor.in_message.from_xml(*[request_payload])
            else:
                params = ()

            # implementation hook
            self.on_method_exec(http_request_env, params, body)

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
                results_soap = descriptor.out_message.to_xml(result_message, service.get_tns())

            # implementation hook
            self.on_results(http_request_env, result_raw, results_soap,
                                                          soap_response_headers)

            # construct the soap response, and serialize it
            envelope = make_soap_envelope(results_soap, tns=service.get_tns(),
                                          header_elements=soap_response_headers)
            results_str = etree.tostring(envelope, encoding=string_encoding)

            if descriptor.mtom:
                http_resp_headers, results_str = apply_mtom(http_resp_headers,
                    results_str,descriptor.out_message._type_info,[result_raw])

            self.on_return(http_request_env, http_resp_headers, results_str)

            # initiate the response
            start_response('200 OK', http_resp_headers.items())

            logging.debug('\033[91m'+ "Response" + '\033[0m')
            logging.debug(etree.tostring(envelope, pretty_print=True))

            # return the serialized results
            return [results_str]

        except Fault, e:
            # FIXME: There's no way to alter soap response headers for the user.

            # The user issued a Fault, so handle it just like an exception!
            fault = make_soap_fault(
                service.get_tns(),
                e.faultstring,
                e.faultcode,
                e.detail,
                header_elements=soap_response_headers)

            fault_str = etree.tostring(fault, encoding=string_encoding)
            logging.error(fault_str)

            self.on_exception(http_request_env, http_resp_headers, e, fault_str)

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

            if methodname:
                faultcode = '%sFault' % methodname
            else:
                faultcode = 'Server'

            detail = ' '
            logging.error(stacktrace)

            fault_str = etree.tostring(make_soap_fault(service.get_tns(),
                faultstring,
                faultcode, detail), encoding=string_encoding)
            logging.debug(fault_str)

            self.on_exception(http_request_env, e, fault_str)

            # initiate the response
            start_response('500 Internal Server Error',http_resp_headers.items())
            return [fault_str]


class SimpleWSGIApp(WSGIApp, ServiceBase):
    '''
    This object is a VERY simple extention of the base WSGIApp.
    It subclasses both WSGIApp, and ServiceBase, so that
    an object can simply subclass this single object, and it will
    be both a wsgi application and a soap service.  This is convenient
    if you want to only expose some functionality, and dont need
    complex handler mapping, and all of the functionality can be put
    in a single class.
    '''

    def __init__(self):
        WSGIApp.__init__(self)
        ServiceBase.__init__(self)

    def get_handler(self, environ):
        return self

class ValidatingWSGISoapApp(SimpleWSGIApp):
    def __init__(self):
        SimpleWSGIApp.__init__(self)
        self.validating_service = True
