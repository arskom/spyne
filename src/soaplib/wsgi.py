
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
logger = logging.getLogger(__name__)

import cgi
import shutil
import tempfile
import traceback

from lxml import etree

import soaplib

from soaplib.serializers.exception import Fault
from soaplib.serializers.primitive import string_encoding

from soaplib.soap import apply_mtom
from soaplib.soap import collapse_swa
from soaplib.soap import from_soap
from soaplib.util import reconstruct_url

HTTP_500 = '500 Internal server error'
HTTP_200 = '200 OK'
HTTP_405 = '405 Method Not Allowed'

class ValidationError(Fault):
    pass

def get_schema_node(pref, schema_nodes, types):
    """
    Return schema node for the given namespace prefix.
    types == None means the call is for creating a standalone xml schema file
                  for one single namespace.
    tyoes != None means the call is for creating the wsdl file.
    """

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

class Application(object):
    def __init__(self, services, tns, name=None, _with_partnerlink=False):
        '''
        @param A ServiceBase subclass that defines the exposed services.
        '''

        self.services = services
        self.__tns = tns
        self.__name = name
        self._with_plink = _with_partnerlink

        self.call_routes = {}
        self.__wsdl = None
        self.__public_methods = {}
        self.schema = self.build_schema()

    def get_name(self):
        """
        Returns service name that is seen in the name attribute of the
        definitions tag.
        """
        retval = self.__name

        if retval is None:
            retval = self.__class__.__name__.split('.')[-1]

        return retval

    name = property(get_name)

    def get_tns(self):
        """
        Returns default namespace that is seen in the targetNamespace attribute
        of the definitions tag.
        """
        retval = self.__tns

        if retval is None:
            service_name = self.get_name()

            if self.__class__.__module__ == '__main__':
                retval = '.'.join((service_name, service_name))
            else:
                retval = '.'.join((self.__class__.__module__, service_name))

            if retval.startswith('soaplib'):
                retval = self.services[0].get_tns()

        return retval

    tns = property(get_tns)

    def __build_schema_nodes(self, schema_entries, types=None):
        """
        Fill individual <schema> nodes for every service that are part of this
        app.
        """

        schema_nodes = {}

        for pref in schema_entries.namespaces:
            schema = get_schema_node(pref, schema_nodes, types)

            # append import tags
            for namespace in schema_entries.imports[pref]:
                import_ = etree.SubElement(schema, "{%s}import"% soaplib.ns_xsd)
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

    def build_schema(self, types=None):
        """
        Unify the <schema> nodes required for this app.
        """

        if types is None:
            # populate call routes
            for s in self.services:
                s.__tns__ = self.get_tns()
                inst = self.get_service(s)

                for method in inst.public_methods:
                    method_name = "{%s}%s" % (self.get_tns(), method.name)

                    if method_name in self.call_routes:
                        o = self.call_routes[method_name]
                        raise Exception("%s.%s.%s overwrites %s.%s.%s" %
                                        (s.__module__, s.__name__, method.name,
                                         o.__module__, o.__name__, method.name))

                    else:
                        logger.debug('adding method %r' % method_name)
                        self.call_routes[method_name] = s
                        self.call_routes[method.name] = s

        # populate types
        schema_entries = None
        for s in self.services:
            inst = self.get_service(s)
            schema_entries = inst.add_schema(schema_entries)

        schema_nodes = self.__build_schema_nodes(schema_entries, types)

        return schema_nodes

    def get_service_class(self, method_name):
        """
        This call maps method names to the services that will handle them.
        Override this function to alter the method mappings. Just try not to get
        too crazy with regular expressions :)
        """
        return self.call_routes[method_name]

    def get_service(self, service, http_req_env=None):
        """
        The function that maps service classes to service instances. Overriding
        this function is useful in case e.g. you need to pass additional
        parameters to service constructors.
        """
        return service(http_req_env)

    def get_schema(self):
        """
        Simple accessor method that caches application's xml schema, once
        generated.
        """
        if self.schema is None:
            return self.build_schema()
        else:
            return self.schema

    def get_wsdl(self, url):
        """
        Simple accessor method that caches the wsdl of the application, once
        generated.
        """
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
        """
        Build the wsdl for the application.
        """
        ns_wsdl = soaplib.ns_wsdl
        ns_soap = soaplib.ns_soap
        ns_plink = soaplib.ns_plink

        ns_tns = self.get_tns()
        pref_tns = soaplib.get_namespace_prefix(ns_tns) #'tns'
        # FIXME: this can be enabled when soaplib.nsmap is no longer global
        #soaplib.set_namespace_prefix(ns_tns, pref_tns)

        # FIXME: doesn't look so robust
        url = url.replace('.wsdl', '')

        service_name = self.get_name()

        # create wsdl root node
        root = etree.Element("{%s}definitions" % ns_wsdl, nsmap=soaplib.nsmap)
        root.set('targetNamespace', ns_tns)
        root.set('name', service_name)

        # create types node
        types = etree.SubElement(root, "{%s}types" % ns_wsdl)

        self.build_schema(types)
        messages = set()

        for s in self.services:
            s=self.get_service(s,None)

            s.add_messages_for_methods(root, messages)

        if self._with_plink:
            # create plink node
            plink = etree.SubElement(root, '{%s}partnerLinkType' % ns_plink)
            plink.set('name', service_name)
            self.add_partner_link(root, service_name, types, url, plink)

        # create service node
        service = etree.SubElement(root, '{%s}service' % ns_wsdl)
        service.set('name', service_name)
        self.add_service(root, service_name, types, url, service)

        # create portType node
        port_type = etree.SubElement(root, '{%s}portType' % ns_wsdl)
        port_type.set('name', service_name)

        # create binding nodes
        binding = etree.SubElement(root, '{%s}binding' % ns_wsdl)
        binding.set('name', service_name)
        binding.set('type', '%s:%s'% (pref_tns, service_name))

        soap_binding = etree.SubElement(binding, '{%s}binding' % ns_soap)
        soap_binding.set('style', 'document')
        soap_binding.set('transport', 'http://schemas.xmlsoap.org/soap/http')

        for s in self.services:
            s = self.get_service(s)
            s.add_port_type(root, service_name, types, url, port_type)
            s.add_bindings_for_methods(root, service_name, types, url, binding)

        self.__wsdl = etree.tostring(root, xml_declaration=True,
                                                               encoding="UTF-8")

        return self.__wsdl

    def add_partner_link(self, root, service_name, types, url, plink):
        """
        Add the partnerLinkType node to the wsdl.
        """
        ns_plink = soaplib.ns_plink
        pref_tns = soaplib.get_namespace_prefix(self.get_tns())

        role = etree.SubElement(plink, '{%s}role' % ns_plink)
        role.set('name', service_name)

        plink_port_type = etree.SubElement(role, '{%s}portType' % ns_plink)
        plink_port_type.set('name', '%s:%s' % (pref_tns, service_name))

    def add_service(self, root, service_name, types, url, service):
        """
        Add service node to the wsdl.
        """
        pref_tns = soaplib.get_namespace_prefix(self.get_tns())

        wsdl_port = etree.SubElement(service, '{%s}port' % soaplib.ns_wsdl)
        wsdl_port.set('name', service_name)
        wsdl_port.set('binding', '%s:%s' % (pref_tns, service_name))

        addr = etree.SubElement(wsdl_port, '{%s}address' % soaplib.ns_soap)
        addr.set('location', url)

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

    def __decode_soap_request(self, http_env, http_payload):
        """
        Decode http payload using information in the http header
        """

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

    def validate_request(self, payload):
        """
        Method to be overriden to perform any sort of custom input validation.
        """
        pass

    def __get_method_name(self, http_req_env, soap_req_payload):
        """
        Guess method name basing on various information in the request.
        """
        retval = None

        if soap_req_payload is not None:
            retval = soap_req_payload.tag
            logger.debug("\033[92mMethod name from xml tag: %r\033[0m" % retval)
        else:
            # check HTTP_SOAPACTION
            retval = http_req_env.get("HTTP_SOAPACTION")

            if retval is not None:
                if retval.startswith('"') and retval.endswith('"'):
                    retval = retval[1:-1]

                if retval.find('/') >0:
                    retvals = retval.split('/')
                    retval = '{%s}%s' % (retvals[0], retvals[1])

                logger.debug("\033[92m"
                             "Method name from HTTP_SOAPACTION: %r"
                             "\033[0m" % retval)

        return retval

    def __handle_soap_request(self, req_env, start_response, url):
        """
        This function is too big.
        """

        http_resp_headers = {
            'Content-Type': 'text/xml',
            'Content-Length': '0',
        }
        method_name = None

        try:
            # implementation hook
            self.on_call(req_env)

            if req_env['REQUEST_METHOD'].lower() != 'post':
                http_resp_headers['Allow'] = 'POST'
                start_response(HTTP_405, http_resp_headers.items())
                return ['']

            input = req_env.get('wsgi.input')
            length = req_env.get("CONTENT_LENGTH")
            body = input.read(int(length))

            try:
                service = None
                soap_req_header, soap_req_payload = self.__decode_soap_request(
                                                                req_env, body)
                if not (soap_req_payload is None):
                    self.validate_request(soap_req_payload)

                method_name = self.__get_method_name(req_env, soap_req_payload)
                if method_name is None:
                    resp = "Could not extract method name from the request!"
                    http_resp_headers['Content-Length'] = str(len(resp))
                    start_response(HTTP_500, http_resp_headers.items())
                    return [resp]

                service_class = self.get_service_class(method_name)
                service = self.get_service(service_class, req_env)

            finally:
                # for performance reasons, we don't want the following to run
                # in production even though we won't see the results.
                if logger.level == logging.DEBUG:
                    try:
                        logger.debug(etree.tostring(etree.fromstring(body),
                                                             pretty_print=True))
                    except etree.XMLSyntaxError,e:
                        logger.debug(body)
                        raise Fault('Client.XMLSyntax', 'Error at line: %d, col: %d'
                                                                    % e.position)

            # retrieve the method descriptor
            descriptor = service.get_method(method_name)
            func = getattr(service, descriptor.name)

            # decode header object
            if soap_req_header is not None and len(soap_req_header) > 0:
                in_header = descriptor.in_header
                service.soap_in_header = in_header.from_xml(soap_req_header)

            # decode method arguments
            if soap_req_payload is not None and len(soap_req_payload) > 0:
                params = descriptor.in_message.from_xml(soap_req_payload)
            else:
                params = [None] * len(descriptor.in_message._type_info)

            # implementation hook
            service.on_method_call(req_env, method_name, params,
                                                               soap_req_payload)

            # call the method
            result_raw = service.call_wrapper(func, params)

            # construct the soap response, and serialize it
            envelope = etree.Element('{%s}Envelope' % soaplib.ns_soap_env,
                                                            nsmap=soaplib.nsmap)

            #
            # header
            #
            soap_header_elt = etree.SubElement(envelope,
                                             '{%s}Header' % soaplib.ns_soap_env)

            if service.soap_out_header != None:
                if descriptor.out_header is None:
                    logger.warning("Skipping soap response header as %r method "
                                   "is not published to have a soap response "
                                   "header" % method_name)
                else:
                    descriptor.out_header.to_xml(
                        service.soap_out_header,
                        self.get_tns(),
                        soap_header_elt,
                        descriptor.out_header.get_type_name()
                    )

            if len(soap_header_elt) > 0:
                envelope.append(soap_header_elt)

            #
            # body
            #
            soap_body = etree.SubElement(envelope,
                                               '{%s}Body' % soaplib.ns_soap_env)

            # instantiate the result message
            result_message = descriptor.out_message()

            # assign raw result to its wrapper, result_message
            out_type = descriptor.out_message._type_info

            if len(out_type) > 0:
                if len(out_type) == 1:
                    attr_name = descriptor.out_message._type_info.keys()[0]
                    setattr(result_message, attr_name, result_raw)
                else:
                    for i in range(len(out_type)):
                        attr_name = descriptor.out_message._type_info.keys()[i]
                        setattr(result_message, attr_name, result_raw[i])

            # transform the results into an element
            descriptor.out_message.to_xml(result_message, self.get_tns(),
                                                                      soap_body)

            # implementation hook
            service.on_method_return(req_env, result_raw, soap_body,
                                                              http_resp_headers)

            #
            # misc
            #
            results_str = etree.tostring(envelope, xml_declaration=True,
                                                       encoding=string_encoding)

            if descriptor.mtom:
                http_resp_headers, results_str = apply_mtom(http_resp_headers,
                    results_str, descriptor.out_message._type_info,[result_raw])

            # implementation hook
            self.on_return(req_env, http_resp_headers, results_str)

            # initiate the response
            http_resp_headers['Content-Length'] = str(len(results_str))
            start_response(HTTP_200, http_resp_headers.items())

            if logger.level == logging.DEBUG:
                logger.debug('\033[91m'+ "Response" + '\033[0m')
                logger.debug(etree.tostring(envelope, xml_declaration=True,
                                                             pretty_print=True))

            # return the serialized results
            return [results_str]

        # The user issued a Fault, so handle it just like an exception!
        except Fault, e:
            return self.__handle_fault(req_env, start_response,
                                                http_resp_headers, service, e)

        except Exception, e:
            fault = Fault('Server', str(e))

            return self.__handle_fault(req_env, start_response,
                                              http_resp_headers, service, fault)

    def __handle_fault(self, req_env, start_response, http_resp_headers,
                                                                  service, exc):
        stacktrace=traceback.format_exc()
        logger.error(stacktrace)

        # implementation hook
        if not (service is None):
            service.on_method_exception_object(req_env, exc)
        self.on_exception_object(req_env, exc)

        # FIXME: There's no way to alter soap response headers for the user.
        envelope = etree.Element('{%s}Envelope' % soaplib.ns_soap_env)
        body = etree.SubElement(envelope, '{%s}Body' % soaplib.ns_soap_env,
                                                            nsmap=soaplib.nsmap)
        exc.__class__.to_xml(exc, self.get_tns(), body)

        if not (service is None):
            service.on_method_exception_xml(req_env, body)
        self.on_exception_xml(req_env, body)

        if logger.level == logging.DEBUG:
            logger.debug(etree.tostring(envelope, pretty_print=True))

        # initiate the response
        fault_str = etree.tostring(envelope)
        http_resp_headers['Content-Length'] = str(len(fault_str))
        start_response(HTTP_500, http_resp_headers.items())

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

    def on_wsdl_exception(self, environ, exc):
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

    def on_exception_object(self, environ, exc):
        '''
        Called when the app throws an exception. (might be inside or outside the
        service call.
        @param the wsgi environment
        @param the fault object
        '''
        pass

    def on_exception_xml(self, environ, fault_xml):
        '''
        Called when the app throws an exception. (might be inside or outside the
        service call.
        @param the wsgi environment
        @param the xml element containing the xml serialization of the fault
        '''
        pass

class ValidatingApplication(Application):
    def build_schema(self, types=None):
        """
        Build application schema specifically for xml validation purposes.
        """
        schema_nodes = Application.build_schema(self, types)

        if types is None:
            pref_tns = soaplib.get_namespace_prefix(self.get_tns())
            logger.debug("generating schema for targetNamespace=%r, prefix: %r"
                                                   % (self.get_tns(), pref_tns))

            tmp_dir_name = tempfile.mkdtemp()

            # serialize nodes to files
            for k,v in schema_nodes.items():
                file_name = '%s/%s.xsd' % (tmp_dir_name, k)
                f = open(file_name, 'w')
                etree.ElementTree(v).write(f, pretty_print=True)
                f.close()
                logger.debug("writing %r for ns %s" % (file_name,
                                                            soaplib.nsmap[k]))

            f = open('%s/%s.xsd' % (tmp_dir_name, pref_tns), 'r')

            logger.debug("building schema...")
            self.schema = etree.XMLSchema(etree.parse(f))

            logger.debug("schema %r built, cleaning up..." % self.schema)
            f.close()
            shutil.rmtree(tmp_dir_name)
            logger.debug("removed %r" % tmp_dir_name)

        return self.schema

    def validate_request(self, payload):
        schema = self.schema
        ret = schema.validate(payload)

        logger.debug("validation result: %s" % str(ret))
        if ret == False:
            err = schema.error_log.last_error

            fault_code = 'Client.SchemaValidation'

            raise ValidationError(fault_code, faultstring=str(err))
