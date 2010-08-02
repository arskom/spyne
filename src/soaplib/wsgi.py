
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
import shutil
import tempfile
import traceback

logger = logging.getLogger(__name__)

from lxml import etree

import soaplib

from soaplib.serializers.exception import Fault
from soaplib.serializers.primitive import string_encoding

from soaplib.service import _SchemaEntries
from soaplib.soap import apply_mtom
from soaplib.soap import collapse_swa
from soaplib.soap import from_soap
from soaplib.soap import make_soap_envelope
from soaplib.soap import make_soap_fault
from soaplib.util import reconstruct_url

class ValidationError(Exception):
    pass

class Application(object):
    def __init__(self, services, tns):
        '''
        @param A ServiceBase subclass that defines the exposed services.
        '''

        self.services = services
        self.call_routes = {}

        self.__wsdl = None
        self.__schema = None
        self.tns = tns

        self.__build_schema()

    def get_tns(self):
        if not (self.tns is None):
            return self.tns

        service_name = self.__class__.__name__.split('.')[-1]

        retval = '.'.join((self.__class__.__module__, service_name))
        if self.__class__.__module__ == '__main__':
            retval = '.'.join((service_name, service_name))

        if retval.startswith('soaplib'):
            retval = self.services[0].get_tns()

        return retval

    def __get_schema_node(self, pref, schema_nodes, types):
        # create schema node
        if not (pref in schema_nodes):
            if types is None:
                schema = etree.Element("{%s}schema" % soaplib.ns_xsd,
                                                        nsmap=soaplib.nsmap)
            else:
                schema = etree.SubElement(types, "{%s}schema" % soaplib.ns_xsd)

            schema.set("targetNamespace", soaplib.nsmap[pref])
            schema.set("elementFormDefault", "qualified")

            schema_nodes[pref] = schema

        else:
            schema = schema_nodes[pref]

        return schema

    def __build_schema_nodes(self, schema_entries, types=None):
        schema_nodes = {}

        for pref in schema_entries.namespaces:
            schema = self.__get_schema_node(pref, schema_nodes, types)

            # append import tags
            for namespace in schema_entries.imports[pref]:
                import_ = etree.SubElement(schema, "{%s}import" % soaplib.ns_xsd)
                import_.set("namespace", namespace)
                if types is None:
                    import_.set('schemaLocation', "%s.xsd" %
                                        soaplib.get_namespace_prefix(namespace))

            # append element tags
            for node in schema_entries.namespaces[pref].elements.values():
                schema.append(node)

            # append simpleType and complexType tags
            for node in schema_entries.namespaces[pref].types.values():
                schema.append(node)

        return schema_nodes

    def __build_schema(self, types=None):
        if types is None:
            # populate call routes
            for s in self.services:
                inst = s()

                for method in inst.public_methods:
                    method_name = "{%s}%s" % (self.get_tns(), method.name)

                    if method_name in self.call_routes:
                        cur_tns = s.get_tns()
                        old_tns = self.call_routes[method_name].get_tns()
                        raise Exception("%s.%s overwrites %s.%s" %
                                                            (old_tns, method.name,
                                                             cur_tns, method.name) )

                    else:
                        logger.debug('adding method %r' % method_name)
                        self.call_routes[method_name] = s

        # populate types
        schema_entries = None
        for s in self.services:
            s.__tns__ = self.get_tns()

            inst = s()
            schema_entries = inst.add_schema(schema_entries)

        schema_nodes = self.__build_schema_nodes(schema_entries,types)

        if types is None:
            logger.debug("generating schema...")
            tmp_dir_name = tempfile.mkdtemp()

            # serialize nodes to files
            for k,v in schema_nodes.items():
                file_name = '%s/%s.xsd' % (tmp_dir_name, k)
                f = open(file_name, 'w')
                etree.ElementTree(v).write(f, pretty_print=True)
                f.close()
                logger.debug("writing %r for ns %s" % (file_name, soaplib.nsmap[k]))

            pref_tns = soaplib.get_namespace_prefix(self.get_tns())
            f = open('%s/%s.xsd' % (tmp_dir_name, pref_tns), 'r')

            logger.debug("building schema...")
            self.__schema = etree.XMLSchema(etree.parse(f))

            logger.debug("schema %r built, cleaning up..." % self.__schema)
            f.close()
            shutil.rmtree(tmp_dir_name)
            logger.debug("removed %r" % tmp_dir_name)

            return self.__schema

    def get_service(self, method_name, http_req_env):
        return self.call_routes[method_name](http_req_env)

    def get_schema(self):
        if self.__schema is None:
            return self.__build_schema()
        else:
            return self.__schema

    def get_wsdl(self, url):
        if self.__wsdl is None:
            return self.__build_wsdl(url)
        else:
            return self.__wsdl

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

    def __build_wsdl(self, url):
        ns_wsdl = soaplib.ns_wsdl
        ns_tns = self.get_tns()
        ns_plink = soaplib.ns_plink
        pref_tns = soaplib.get_namespace_prefix(ns_tns)

        # FIXME: doesn't look so robust
        url = url.replace('.wsdl', '')

        # TODO: we may want to customize service_name.
        service_name = self.__class__.__name__.split('.')[-1]

        # this needs to run before creating definitions tag in order to get
        # soaplib.nsmap populated.

        # create wsdl root node
        root = etree.Element("{%s}definitions" % ns_wsdl, nsmap=soaplib.nsmap)
        root.set('targetNamespace', ns_tns)
        root.set('name', service_name)

        # create types node
        types = etree.SubElement(root, "{%s}types" % ns_wsdl)

        for s in self.services:
            s=s()

            self.__build_schema(types)
            s.add_messages_for_methods(root, service_name, types, url)

        # create plink node
        plink = etree.SubElement(root, '{%s}partnerLinkType' % ns_plink)
        plink.set('name', service_name)

        # create service node
        service = etree.SubElement(root, '{%s}service' % ns_wsdl)
        service.set('name', service_name)

        # create portType node
        port_type = etree.SubElement(root, '{%s}portType' % ns_wsdl)
        port_type.set('name', service_name)

        # create binding nodes
        binding = etree.SubElement(root, '{%s}binding' % ns_wsdl)
        binding.set('name', service_name)
        binding.set('type', '%s:%s'% (pref_tns, service_name))

        cb_binding = None

        for s in self.services:
            s=s()
            s.add_port_type(root, service_name, types, url, port_type)
            s.add_partner_link(root, service_name, types, url, plink)
            cb_binding = s.add_bindings_for_methods(root, service_name, types,
                                                       url, binding, cb_binding)
            s.add_service(root, service_name, types, url, service)

        self.__wsdl = etree.tostring(root, xml_declaration=True, encoding="UTF-8")

        return self.__wsdl

    def __handle_wsdl_request(self, req_env, start_response, url):
        retval = ['']

        http_resp_headers = {'Content-Type': 'text/xml'}

        start_response('200 OK', http_resp_headers.items())
        try:
            self.get_wsdl(url)
            self.on_wsdl(req_env, self.__wsdl) # implementation hook

            return [self.__wsdl]

        except Exception, e:
            # implementation hook
            logger.error(traceback.format_exc())

            tns = self.get_tns()
            fault_xml = make_soap_fault(str(e), tns, detail=" ")
            fault_str = etree.tostring(fault_xml,
                   xml_declaration=True, encoding=string_encoding)
            logger.debug(fault_str)

            self.on_wsdl_exception(req_env, e, fault_str)

            # initiate the response
            http_resp_headers['Content-length'] = str(len(fault_str))
            start_response('500 Internal Server Error',
                http_resp_headers.items())

            return [fault_str]

    def __decode_soap_request(self, http_env, http_payload):
        # decode body using information in the http header
        #
        # fyi, here's what the parse_header function returns:
        # >>> import cgi; cgi.parse_header("text/xml; charset=utf-8")
        # ('text/xml', {'charset': 'utf-8'})
        content_type = cgi.parse_header(http_env.get("CONTENT_TYPE"))
        charset = content_type[1].get('charset',None)
        if charset is None:
            charset = 'ascii'

        http_payload = collapse_swa(content_type, http_payload)

        # deserialize the body of the message
        req_payload, req_header = from_soap(http_payload, charset)

        return req_header, req_payload

    def validate_request(self, service, payload):
        # if there's a schema to validate against, validate the response
        schema = self.__schema
        if schema != None:
            ret = schema.validate(payload)
            logger.debug("validation result: %s" % str(ret))
            if ret == False:
                raise ValidationError(schema.error_log.last_error)

    def __get_method_name(self, http_req_env, soap_req_payload):
        retval = None

        if soap_req_payload is not None and len(soap_req_payload) > 0:
            retval = soap_req_payload.tag
        else:
            # check HTTP_SOAPACTION
            retval = http_req_env.get("HTTP_SOAPACTION")
            if retval.startswith('"') and retval.endswith('"'):
                retval = retval[1:-1]
            if retval.find('/') >0:
                retval = retval.split('/')[1]

        return retval

    def __handle_soap_request(self, req_env, start_response, url):
        http_resp_headers = {'Content-Type': 'text/xml'}
        soap_resp_headers = []
        method_name = None

        try:
            # implementation hook
            self.on_call(req_env)

            if req_env['REQUEST_METHOD'].lower() != 'post':
                start_response('405 Method Not Allowed', [('Allow', 'POST')])
                return ['']

            input = req_env.get('wsgi.input')
            length = req_env.get("CONTENT_LENGTH")
            body = input.read(int(length))

            try:
                soap_req_header, soap_req_payload = self.__decode_soap_request(
                                                                req_env, body)
                method_name = self.__get_method_name(req_env, soap_req_payload)
                service = self.get_service(method_name, req_env)
                service.soap_req_header = soap_req_header

                self.validate_request(service, soap_req_payload)

            finally:
                # for performance reasons, we don't want the following to run
                # in production even if we don't see the results.
                if logger.level == logging.DEBUG:
                    logger.debug('\033[92mMethod name: %r\033[0m' % method_name)
                    logger.debug(etree.tostring(etree.fromstring(body),
                                                             pretty_print=True))

            # retrieve the method descriptor
            descriptor = service.get_method(method_name)
            func = getattr(service, descriptor.name)

            # decode method arguments
            if soap_req_payload is not None and len(soap_req_payload) > 0:
                params = descriptor.in_message.from_xml(soap_req_payload)
            else:
                params = ()

            # implementation hook
            service.on_method_call(req_env, method_name, params, body)

            # call the method
            result_raw = service.call_wrapper(func, params)

            # create result message
            result_message = descriptor.out_message()

            # assign raw result to its wrapper, result_message
            attr_name = descriptor.out_message._type_info.keys()[0]
            setattr(result_message, attr_name, result_raw)

            # transform the results into an element
            # only expect a single element
            results_soap = None
            if not (descriptor.is_async or descriptor.is_callback):
                results_soap = descriptor.out_message.to_xml(result_message,
                                                              self.get_tns())

            # implementation hook
            service.on_method_return(req_env, result_raw, results_soap,
                                                            soap_resp_headers)

            # construct the soap response, and serialize it
            envelope = make_soap_envelope(results_soap, tns=self.get_tns(),
                                          header_elements=soap_resp_headers)
            results_str = etree.tostring(envelope, xml_declaration=True,
                                                       encoding=string_encoding)

            if descriptor.mtom:
                http_resp_headers, results_str = apply_mtom(http_resp_headers,
                    results_str,descriptor.out_message._type_info,[result_raw])

            self.on_return(req_env, http_resp_headers, results_str)

            # initiate the response
            start_response('200 OK', http_resp_headers.items())

            if logger.level == logging.DEBUG:
                logger.debug('\033[91m'+ "Response" + '\033[0m')
                logger.debug(etree.tostring(envelope, xml_declaration=True,
                                                             pretty_print=True))

            # return the serialized results
            return [results_str]

        except Fault, e:
            # FIXME: There's no way to alter soap response headers for the user.

            # The user issued a Fault, so handle it just like an exception!
            fault_xml = make_soap_fault(
                self.get_tns(),
                e.faultstring,
                e.faultcode,
                e.detail,
                header_elements=soap_resp_headers)

            fault_str = etree.tostring(fault_xml, xml_declaration=True,
                                                    encoding=string_encoding)
            logger.error(fault_str)

            service.on_method_exception(req_env, http_resp_headers, e, fault_str)

            # initiate the response
            start_response('500 Internal Server Error',http_resp_headers.items())

            return [fault_str]

        except Exception, e:
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


            fault_xml = make_soap_fault(self.get_tns(), faultstring,
                                                              faultcode, detail)
            fault_str = etree.tostring(fault_xml, xml_declaration=True,
                                                       encoding=string_encoding)
            logger.debug(fault_str)

            service.on_method_exception(req_env, e, fault_str)

            # initiate the response
            start_response('500 Internal Server Error',http_resp_headers.items())

            return [fault_str]

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

        url = wsgi_url
        if url is None:
            url = reconstruct_url(req_env).split('.wsdl')[0]

        if self.__is_wsdl_request(req_env):
            return self.__handle_wsdl_request(req_env, start_response, url)
        else:
            return self.__handle_soap_request(req_env, start_response, url)

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

    def on_return(self, environ, http_headers, return_str):
        '''
        Called before the application returns
        @param the wsgi environment
        @param http response headers as dict
        @param return string of the soap request
        '''
        pass
