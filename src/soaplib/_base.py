
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
logger = logging.getLogger("soaplib._base")

import warnings

import shutil
import tempfile
import traceback

from lxml import etree

import soaplib

from soaplib.type.exception import Fault
from soaplib.util.odict import odict

HTTP_500 = '500 Internal server error'
HTTP_200 = '200 OK'
HTTP_405 = '405 Method Not Allowed'

class ValidationError(Fault):
    pass

class _SchemaInfo(object):
    def __init__(self):
        self.elements = odict()
        self.types = odict()

class _SchemaEntries(object):
    def __init__(self, app):
        self.namespaces = odict()
        self.imports = {}
        self.tns = app.get_tns()
        self.app = app
        self.classes = {}

    def has_class(self, cls):
        retval = False
        ns_prefix = cls.get_namespace_prefix(self.app)

        if ns_prefix in soaplib.const_nsmap:
            retval = True

        else:
            type_name = cls.get_type_name()

            if (ns_prefix in self.namespaces) and \
                              (type_name in self.namespaces[ns_prefix].types):
                retval = True

        return retval

    def get_schema_info(self, prefix):
        if prefix in self.namespaces:
            schema = self.namespaces[prefix]
        else:
            schema = self.namespaces[prefix] = _SchemaInfo()

        return schema

    # FIXME: this is an ugly hack. we need proper dependency management
    def __check_imports(self, cls, node):
        pref_tns = cls.get_namespace_prefix(self.app)

        def is_valid_import(pref):
            return not (
                (pref in soaplib.const_nsmap) or (pref == pref_tns)
            )

        if not (pref_tns in self.imports):
            self.imports[pref_tns] = set()

        for c in node:
            if c.tag == "{%s}complexContent" % soaplib.ns_xsd:
                seq = c.getchildren()[0].getchildren()[0] # FIXME: ugly, isn't it?

                extension = c.getchildren()[0]
                if extension.tag == '{%s}extension' % soaplib.ns_xsd:
                    pref = extension.attrib['base'].split(':')[0]
                    if is_valid_import(pref):
                        self.imports[pref_tns].add(self.app.nsmap[pref])
            else:
                seq = c

            if seq.tag == '{%s}sequence' % soaplib.ns_xsd:
                for e in seq:
                    pref = e.attrib['type'].split(':')[0]
                    if is_valid_import(pref):
                        self.imports[pref_tns].add(self.app.nsmap[pref])

            elif seq.tag == '{%s}restriction' % soaplib.ns_xsd:
                pref = seq.attrib['base'].split(':')[0]
                if is_valid_import(pref):
                    self.imports[pref_tns].add(self.app.nsmap[pref])

            else:
                raise Exception("i guess you need to hack some more")

    def add_element(self, cls, node):
        schema_info = self.get_schema_info(cls.get_namespace_prefix(self.app))
        schema_info.elements[cls.get_type_name()] = node

    def add_simple_type(self, cls, node):
        ns = cls.get_namespace()
        tn = cls.get_type_name()
        pref = cls.get_namespace_prefix(self.app)

        self.__check_imports(cls, node)
        schema_info = self.get_schema_info(pref)
        schema_info.types[tn] = node

        self.classes['{%s}%s' % (ns,tn)] = cls
        if ns == self.app.get_tns():
            self.classes[tn] = cls

    def add_complex_type(self, cls, node):
        ns = cls.get_namespace()
        tn = cls.get_type_name()
        pref = cls.get_namespace_prefix(self.app)

        self.__check_imports(cls, node)
        schema_info = self.get_schema_info(pref)
        schema_info.types[tn] = node

        self.classes['{%s}%s' % (ns,tn)] = cls
        if ns == self.app.get_tns():
            self.classes[tn] = cls

class MethodContext(object):
    def __init__(self):
        self.service = None
        self.service_class = None

        self.in_error = None
        self.in_header_xml = None
        self.in_body_xml = None

        self.out_error = None
        self.out_header_xml = None
        self.out_body_xml = None

        self.method_name = None
        self.descriptor = None
        
class MethodDescriptor(object):
    '''
    This class represents the method signature of a soap method,
    and is returned by the soapdocument, or rpc decorators.
    '''

    def __init__(self, name, public_name, in_message, out_message, doc,
                 is_callback=False, is_async=False, mtom=False, in_header=None,
                 out_header=None):

        self.name = name
        self.public_name = public_name
        self.in_message = in_message
        self.out_message = out_message
        self.doc = doc
        self.is_callback = is_callback
        self.is_async = is_async
        self.mtom = mtom
        self.in_header = in_header
        self.out_header = out_header

def from_soap(xml_string, charset):
    '''
    Parses the xml string into the header and payload
    '''

    try:
        if charset is None: # hack
            raise ValueError(charset)

        root, xmlids = etree.XMLID(xml_string.decode(charset))
    except ValueError,e:
        logger.debug('%s -- falling back to str decoding.' % (e))
        root, xmlids = etree.XMLID(xml_string)

    if xmlids:
        resolve_hrefs(root, xmlids)

    if root.tag != '{%s}Envelope' % soaplib.ns_soap_env:
        raise Fault('Client.SoapError', 'No {%s}Envelope element was found!' %
                                                            soaplib.ns_soap_env)

    header_envelope = root.xpath('e:Header',
                                         namespaces={'e': soaplib.ns_soap_env})
    body_envelope = root.xpath('e:Body', namespaces={'e': soaplib.ns_soap_env})

    if len(header_envelope) == 0 and len(body_envelope) == 0:
        raise Fault('Client.SoapError', 'Soap envelope is empty!' %
                                                            soaplib.ns_soap_env)

    header=None
    if len(header_envelope) > 0 and len(header_envelope[0]) > 0:
        header = header_envelope[0].getchildren()[0]

    body=None
    if len(body_envelope) > 0 and len(body_envelope[0]) > 0:
        body = body_envelope[0].getchildren()[0]

    return header, body

# see http://www.w3.org/TR/2000/NOTE-SOAP-20000508/
# section 5.2.1 for an example of how the id and href attributes are used.
def resolve_hrefs(element, xmlids):
    for e in element:
        if e.get('id'):
            continue # don't need to resolve this element

        elif e.get('href'):
            resolved_element = xmlids[e.get('href').replace('#', '')]
            if resolved_element is None:
                continue
            resolve_hrefs(resolved_element, xmlids)

            # copies the attributes
            [e.set(k, v) for k, v in resolved_element.items()]

            # copies the children
            [e.append(child) for child in resolved_element.getchildren()]

            # copies the text
            e.text = resolved_element.text

        else:
            resolve_hrefs(e, xmlids)

    return element

class Application(object):
    transport = None

    class NO_WRAPPER:
        pass
    class IN_WRAPPER:
        pass
    class OUT_WRAPPER:
        pass

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
        self.__classes = {}

        self.__ns_counter = 0

        self.nsmap = dict(soaplib.const_nsmap)
        self.prefmap = dict(soaplib.const_prefmap)

        self.schema = self.build_schema()

    def get_class(self, key):
        return self.__classes[key]

    def get_class_instance(self, key):
        return self.__classes[key]()

    def decompose_incoming_envelope(self, ctx, envelope_string, charset=None):
        header, body = from_soap(envelope_string, charset)

        # FIXME: find a way to include soap env schema with soaplib package and
        # properly and always validate the whole request.

        if len(body) > 0 and body.tag == '{%s}Fault' % soaplib.ns_soap_env:
            ctx.in_body_xml = body

        elif not (body is None):
            try:
                self.validate(body)
                if (not (body is None)) and (ctx.method_name is None):
                    ctx.method_name = body.tag
                    logger.debug("\033[92mMethod name: %r\033[0m" %
                                                                ctx.method_name)

            finally:
                # for performance reasons, we don't want the following to run
                # in production even though we won't see the results.
                if logger.level == logging.DEBUG:
                    try:
                        logger.debug(etree.tostring(
                           etree.fromstring(envelope_string),pretty_print=True))
                    except etree.XMLSyntaxError, e:
                        logger.debug(body)
                        raise Fault('Client.Xml', 'Error at line: %d, '
                                    'col: %d' % e.position)
            try:
                if ctx.service_class is None: # i.e. if it's a server
                    ctx.service_class = self.get_service_class(ctx.method_name)

            except Exception,e:
                logger.debug(traceback.format_exc())
                raise ValidationError('Client', 'Method not found: %r' %
                                                                ctx.method_name)

            ctx.service = self.get_service(ctx.service_class)

            ctx.in_header_xml = header
            ctx.in_body_xml = body

    def deserialize_soap(self, ctx, envelope_string, wrapper, charset=None):
        """Takes a MethodContext instance and a string containing ONE soap
        message.
        Returns the corresponding native python object

        Not meant to be overridden.
        """

        assert wrapper in (Application.IN_WRAPPER,
                                                Application.OUT_WRAPPER),wrapper

        try:
            self.decompose_incoming_envelope(ctx, envelope_string, charset)
        except ValidationError, e:
            return e

        if ctx.in_body_xml.tag == "{%s}Fault" % soaplib.ns_soap_env:
            in_body = Fault.from_xml(ctx.in_body_xml)

        else:
            # retrieve the method descriptor
            if ctx.method_name is None:
                raise Exception("Could not extract method name from the request!")
            else:
                if ctx.descriptor is None:
                    descriptor = ctx.descriptor = ctx.service.get_method(
                                                                    ctx.method_name)
                else:
                    descriptor = ctx.descriptor

            if wrapper is Application.IN_WRAPPER:
                header_class = descriptor.in_header
                body_class = descriptor.in_message
            elif wrapper is Application.OUT_WRAPPER:
                header_class = descriptor.out_header
                body_class = descriptor.out_message

            # decode header object
            if ctx.in_header_xml is not None and len(ctx.in_header_xml) > 0:
                ctx.service.in_header = header_class.from_xml(ctx.in_header_xml)

            # decode method arguments
            if ctx.in_body_xml is not None and len(ctx.in_body_xml) > 0:
                in_body = body_class.from_xml(ctx.in_body_xml)
            else:
                in_body = [None] * len(body_class._type_info)

        return in_body

    def process_request(self, ctx, req_obj):
        """Takes a MethodContext instance and the native request object.
        Returns the response to the request as a native python object.

        Not meant to be overridden.
        """

        try:
            # implementation hook
            ctx.service.on_method_call(ctx.method_name,req_obj,ctx.in_body_xml)

            # retrieve the method
            func = getattr(ctx.service, ctx.descriptor.name)

            # call the method
            retval = ctx.service.call_wrapper(func, req_obj)

        except Fault, e:
            stacktrace=traceback.format_exc()
            logger.error(stacktrace)

            retval = e

        except Exception, e:
            stacktrace=traceback.format_exc()
            logger.error(stacktrace)

            retval = Fault('Server', str(e))

        # implementation hook
        if isinstance(retval, Fault):
            ctx.service.on_method_exception_object(retval)
            self.on_exception_object(retval)

        else:
            ctx.service.on_method_return_object(retval)

        return retval

    def serialize_soap(self, ctx, native_obj, wrapper):
        """Takes a MethodContext instance and the object to be serialied.
        Returns the corresponding xml structure as an lxml.etree._Element
        instance.

        Not meant to be overridden.
        """

        assert wrapper in (Application.IN_WRAPPER, Application.OUT_WRAPPER,
                                                 Application.NO_WRAPPER),wrapper

        # construct the soap response, and serialize it
        envelope = etree.Element('{%s}Envelope' % soaplib.ns_soap_env,
                                                               nsmap=self.nsmap)

        if isinstance(native_obj, Fault):
            # FIXME: There's no way to alter soap response headers for the user.
            ctx.out_body_xml = out_body_xml = etree.SubElement(envelope,
                            '{%s}Body' % soaplib.ns_soap_env, nsmap=self.nsmap)
            native_obj.__class__.to_xml(native_obj,self.get_tns(), out_body_xml)

            # implementation hook
            if not (ctx.service is None):
                ctx.service.on_method_exception_xml(out_body_xml)
            self.on_exception_xml(out_body_xml)

            if logger.level == logging.DEBUG:
                logger.debug(etree.tostring(envelope, pretty_print=True))

        elif isinstance(native_obj, Exception):
            raise Exception("Can't serialize native python exceptions")

        else:
            # header
            if ctx.service.out_header != None:
                if wrapper in (Application.NO_WRAPPER, Application.OUT_WRAPPER):
                    header_message_class = ctx.descriptor.in_header
                else:
                    header_message_class = ctx.descriptor.out_header

                if ctx.descriptor.out_header is None:
                    logger.warning(
                        "Skipping soap response header as %r method is not "
                        "published to have one." %
                                native_obj.get_type_name()[:-len('Response')])

                else:
                    ctx.out_header_xml = soap_header_elt = etree.SubElement(
                                   envelope, '{%s}Header' % soaplib.ns_soap_env)

                    header_message_class.to_xml(
                        ctx.service.out_header,
                        self.get_tns(),
                        soap_header_elt,
                        header_message_class.get_type_name()
                    )

            # body
            ctx.out_body_xml = out_body_xml = etree.SubElement(envelope,
                                               '{%s}Body' % soaplib.ns_soap_env)

            # instantiate the result message
            if wrapper is Application.NO_WRAPPER:
                result_message_class = ctx.descriptor.in_message
                result_message = native_obj

            else:
                if wrapper is Application.IN_WRAPPER:
                    result_message_class = ctx.descriptor.in_message
                elif wrapper is Application.OUT_WRAPPER:
                    result_message_class = ctx.descriptor.out_message

                result_message = result_message_class()

                # assign raw result to its wrapper, result_message
                out_type_info = result_message_class._type_info

                if len(out_type_info) > 0:
                     if len(out_type_info) == 1:
                         attr_name = result_message_class._type_info.keys()[0]
                         setattr(result_message, attr_name, native_obj)

                     else:
                         for i in range(len(out_type_info)):
                             attr_name=result_message_class._type_info.keys()[i]
                             setattr(result_message, attr_name, native_obj[i])

            # transform the results into an element
            result_message_class.to_xml(
                                  result_message, self.get_tns(), out_body_xml)

            if logger.level == logging.DEBUG:
                logger.debug('\033[91m'+ "Response" + '\033[0m')
                logger.debug(etree.tostring(envelope, xml_declaration=True,
                                                             pretty_print=True))

            #implementation hook
            if not (ctx.service is None):
                ctx.service.on_method_return_xml(envelope)

        return envelope

    def get_namespace_prefix(self, ns):
        """Returns the namespace prefix for the given namespace. Creates a new
        one automatically if it doesn't exist.

        Not meant to be overridden.
        """

        if ns == "__main__":
            warnings.warn("Namespace is '__main__'", Warning )

        assert ns != "soaplib.type.base"

        assert (isinstance(ns, str) or isinstance(ns, unicode)), ns

        if not (ns in self.prefmap):
            pref = "s%d" % self.__ns_counter
            while pref in self.nsmap:
                self.__ns_counter += 1
                pref = "s%d" % self.__ns_counter

            self.prefmap[ns] = pref
            self.nsmap[pref] = ns

            self.__ns_counter += 1

        else:
            pref = self.prefmap[ns]

        return pref

    def set_namespace_prefix(self, ns, pref):
        """Forces a namespace prefix on a namespace by either creating it or
        moving the existing namespace to a new prefix.

        Not meant to be overridden.
        """

        if pref in self.nsmap and self.nsmap[pref] != ns:
            ns_old = self.nsmap[pref]
            del self.prefmap[ns_old]
            self.get_namespace_prefix(ns_old)

        cpref = self.get_namespace_prefix(ns)
        del self.nsmap[cpref]

        self.prefmap[ns] = pref
        self.nsmap[pref] = ns

    def get_name(self):
        """Returns service name that is seen in the name attribute of the
        definitions tag.

        Not meant to be overridden.
        """
        retval = self.__name

        if retval is None:
            retval = self.__class__.__name__.split('.')[-1]

        return retval

    name = property(get_name)

    def get_tns(self):
        """Returns default namespace that is seen in the targetNamespace 
        attribute of the definitions tag.

        Not meant to be overridden.
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
        """Fill individual <schema> nodes for every service that are part of
        this app.
        """

        schema_nodes = {}

        for pref in schema_entries.namespaces:
            schema = self.__get_schema_node(pref, schema_nodes, types)

            # append import tags
            for namespace in schema_entries.imports[pref]:
                import_ = etree.SubElement(schema, "{%s}import"% soaplib.ns_xsd)
                import_.set("namespace", namespace)
                if types is None:
                    import_.set('schemaLocation', "%s.xsd" %
                                        self.get_namespace_prefix(namespace))

            # append element tags
            for node in schema_entries.namespaces[pref].elements.values():
                schema.append(node)

            # append simpleType and complexType tags
            for node in schema_entries.namespaces[pref].types.values():
                schema.append(node)

        return schema_nodes

    def build_schema(self, types=None):
        """Unify the <schema> nodes required for this app.

        This is a protected method.
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
        schema_entries = _SchemaEntries(self)
        for s in self.services:
            inst = self.get_service(s)
            inst.add_schema(schema_entries)

        schema_nodes = self.__build_schema_nodes(schema_entries, types)

        self.__classes = schema_entries.classes

        return schema_nodes

    def get_service_class(self, method_name):
        """This call maps method names to the services that will handle them.

        Override this function to alter the method mappings. Just try not to get
        too crazy with regular expressions :)
        """
        return self.call_routes[method_name]

    def get_service(self, service, http_req_env=None):
        """The function that maps service classes to service instances.
        Overriding this function is useful in case e.g. you need to pass
        additional parameters to service constructors.
        """
        return service(http_req_env)

    def get_schema(self):
        """Simple accessor method that caches application's xml schema, once
        generated.

        Not meant to be overridden.
        """
        if self.schema is None:
            return self.build_schema()
        else:
            return self.schema

    def get_wsdl(self, url):
        """Simple accessor method that caches the wsdl of the application, once
        generated.

        Not meant to be overridden.
        """
        if self.__wsdl is None:
            return self.__build_wsdl(url)
        else:
            return self.__wsdl

    def __get_schema_node(self, pref, schema_nodes, types):
        """Return schema node for the given namespace prefix.

        types == None means the call is for creating a standalone xml schema
                      file for one single namespace.
        types != None means the call is for creating the wsdl file.
        """

        # create schema node
        if not (pref in schema_nodes):
            if types is None:
                schema = etree.Element("{%s}schema" % soaplib.ns_xsd,
                                                        nsmap=self.nsmap)
            else:
                schema = etree.SubElement(types, "{%s}schema" % soaplib.ns_xsd)

            schema.set("targetNamespace", self.nsmap[pref])
            schema.set("elementFormDefault", "qualified")

            schema_nodes[pref] = schema

        else:
            schema = schema_nodes[pref]

        return schema

    def __build_wsdl(self, url):
        """Build the wsdl for the application.
        """
        ns_wsdl = soaplib.ns_wsdl
        ns_soap = soaplib.ns_soap
        ns_plink = soaplib.ns_plink

        ns_tns = self.get_tns()
        pref_tns = 'tns'
        self.set_namespace_prefix(ns_tns, pref_tns)

        # FIXME: doesn't look so robust
        url = url.replace('.wsdl', '')

        service_name = self.get_name()

        # create wsdl root node
        root = etree.Element("{%s}definitions" % ns_wsdl, nsmap=self.nsmap)
        root.set('targetNamespace', ns_tns)
        root.set('name', service_name)

        # create types node
        types = etree.SubElement(root, "{%s}types" % ns_wsdl)

        self.build_schema(types)
        messages = set()

        for s in self.services:
            s=self.get_service(s,None)

            s.add_messages_for_methods(self, root, messages)

        if self._with_plink:
            # create plink node
            plink = etree.SubElement(root, '{%s}partnerLinkType' % ns_plink)
            plink.set('name', service_name)
            self.__add_partner_link(root, service_name, types, url, plink)

        # create service node
        service = etree.SubElement(root, '{%s}service' % ns_wsdl)
        service.set('name', service_name)
        self.__add_service(root, service_name, types, url, service)

        # create portType node
        port_type = etree.SubElement(root, '{%s}portType' % ns_wsdl)
        port_type.set('name', service_name)

        # create binding nodes
        binding = etree.SubElement(root, '{%s}binding' % ns_wsdl)
        binding.set('name', service_name)
        binding.set('type', '%s:%s'% (pref_tns, service_name))

        soap_binding = etree.SubElement(binding, '{%s}binding' % ns_soap)
        soap_binding.set('style', 'document')

        if self.transport is None:
            raise Exception("You must set the class variable 'transport'")
        soap_binding.set('transport', self.transport)

        cb_binding = None

        for s in self.services:
            s=self.get_service(s)
            s.add_port_type(self, root, service_name, types, url, port_type)
            cb_binding = s.add_bindings_for_methods(self, root, service_name,
                                                types, url, binding, cb_binding)

        self.__wsdl = etree.tostring(root, xml_declaration=True,
                                                               encoding="UTF-8")

        return self.__wsdl

    def __add_partner_link(self, root, service_name, types, url, plink):
        """Add the partnerLinkType node to the wsdl.
        """
        ns_plink = soaplib.ns_plink
        ns_tns = self.get_tns()
        pref_tns = self.get_namespace_prefix(ns_tns)

        role = etree.SubElement(plink, '{%s}role' % ns_plink)
        role.set('name', service_name)

        plink_port_type = etree.SubElement(role, '{%s}portType' % ns_plink)
        plink_port_type.set('name', '%s:%s' % (pref_tns, service_name))

        if self._has_callbacks():
            role = etree.SubElement(plink, '{%s}role' % ns_plink)
            role.set('name', '%sCallback' % service_name)

            plink_port_type = etree.SubElement(role, '{%s}portType' % ns_plink)
            plink_port_type.set('name', '%s:%sCallback' %
                                                       (pref_tns, service_name))
    def __add_service(self, root, service_name, types, url, service):
        """Add service node to the wsdl.
        """
        pref_tns = self.get_namespace_prefix(self.get_tns())

        wsdl_port = etree.SubElement(service, '{%s}port' % soaplib.ns_wsdl)
        wsdl_port.set('name', service_name)
        wsdl_port.set('binding', '%s:%s' % (pref_tns, service_name))

        addr = etree.SubElement(wsdl_port, '{%s}address' % soaplib.ns_soap)
        addr.set('location', url)

    def _has_callbacks(self):
        retval = False

        for s in self.services:
            if self.get_service(s)._has_callbacks():
                return True

        return retval

    def validate(self, payload):
        """Method to be overriden to perform any sort of custom input
        validation.
        """

    def on_exception_object(self, exc):
        '''Called when the app throws an exception. (might be inside or outside
        the service call.

        @param the wsgi environment
        @param the fault object
        '''

    def on_exception_xml(self, fault_xml):
        '''Called when the app throws an exception. (might be inside or outside
        the service call.

        @param the wsgi environment
        @param the xml element containing the xml serialization of the fault
        '''

class ValidatingApplication(Application):
    def build_schema(self, types=None):
        """Build application schema specifically for xml validation purposes.
        """
        schema_nodes = Application.build_schema(self, types)

        if types is None:
            pref_tns = self.get_namespace_prefix(self.get_tns())
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
                                                            self.nsmap[k]))

            f = open('%s/%s.xsd' % (tmp_dir_name, pref_tns), 'r')

            logger.debug("building schema...")
            self.schema = etree.XMLSchema(etree.parse(f))

            logger.debug("schema %r built, cleaning up..." % self.schema)
            f.close()
            shutil.rmtree(tmp_dir_name)
            logger.debug("removed %r" % tmp_dir_name)

        return self.schema

    def validate(self, payload):
        schema = self.schema
        ret = schema.validate(payload)

        logger.debug("validation result: %s" % str(ret))
        if ret == False:
            err = schema.error_log.last_error

            fault_code = 'Client.SchemaValidation'

            raise ValidationError(fault_code, faultstring=str(err))
