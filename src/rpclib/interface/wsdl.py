
#
# rpclib - Copyright (C) Rpclib contributors.
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

import warnings
import shutil
import tempfile

from lxml import etree

import rpclib
from rpclib.model.exception import Fault
from rpclib.interface.base import Base
from rpclib.interface.base import SchemaEntries

class ValidationError(Fault):
    pass

def add_port_type(service, app, root, service_name, types, url, port_type):
    ns_wsdl = rpclib.ns_wsdl

    # FIXME: I don't think this call is working.
    cb_port_type = _add_callbacks(service, root, types, service_name, url)

    for method in service.public_methods:
        if method.is_callback:
            operation = etree.SubElement(cb_port_type, '{%s}operation'
                                                        % ns_wsdl)
        else:
            operation = etree.SubElement(port_type,'{%s}operation'% ns_wsdl)

        operation.set('name', method.name)

        if method.doc is not None:
            documentation = etree.SubElement(operation, '{%s}documentation'
                                                            % ns_wsdl)
            documentation.text = method.doc

        operation.set('parameterOrder', method.in_message.get_type_name())

        op_input = etree.SubElement(operation, '{%s}input' % ns_wsdl)
        op_input.set('name', method.in_message.get_type_name())
        op_input.set('message', method.in_message.get_type_name_ns(app))

        if (not method.is_callback) and (not method.is_async):
            op_output = etree.SubElement(operation, '{%s}output' %  ns_wsdl)
            op_output.set('name', method.out_message.get_type_name())
            op_output.set('message', method.out_message.get_type_name_ns(
                                                                       app))

# FIXME: I don't think this is working.
def _add_callbacks(self, root, types, service_name, url):
    ns_xsd = rpclib.ns_xsd
    ns_wsa = rpclib.ns_wsa
    ns_wsdl = rpclib.ns_wsdl
    ns_soap = rpclib.ns_soap

    ns_tns = self.get_tns()
    pref_tns = 'tns'

    cb_port_type = None

    # add necessary async headers
    # WS-Addressing -> RelatesTo ReplyTo MessageID
    # callback porttype
    if self._has_callbacks():
        wsa_schema = etree.SubElement(types, "{%s}schema" % ns_xsd)
        wsa_schema.set("targetNamespace", '%sCallback'  % ns_tns)
        wsa_schema.set("elementFormDefault", "qualified")

        import_ = etree.SubElement(wsa_schema, "{%s}import" % ns_xsd)
        import_.set("namespace", ns_wsa)
        import_.set("schemaLocation", ns_wsa)

        relt_message = etree.SubElement(root, '{%s}message' % ns_wsdl)
        relt_message.set('name', 'RelatesToHeader')
        relt_part = etree.SubElement(relt_message, '{%s}part' % ns_wsdl)
        relt_part.set('name', 'RelatesTo')
        relt_part.set('element', '%s:RelatesTo' % _pref_wsa)

        reply_message = etree.SubElement(root, '{%s}message' % ns_wsdl)
        reply_message.set('name', 'ReplyToHeader')
        reply_part = etree.SubElement(reply_message, '{%s}part' % ns_wsdl)
        reply_part.set('name', 'ReplyTo')
        reply_part.set('element', '%s:ReplyTo' % _pref_wsa)

        id_header = etree.SubElement(root, '{%s}message' % ns_wsdl)
        id_header.set('name', 'MessageIDHeader')
        id_part = etree.SubElement(id_header, '{%s}part' % ns_wsdl)
        id_part.set('name', 'MessageID')
        id_part.set('element', '%s:MessageID' % _pref_wsa)

        # make portTypes
        cb_port_type = etree.SubElement(root, '{%s}portType' % ns_wsdl)
        cb_port_type.set('name', '%sCallback' % service_name)

        cb_service_name = '%sCallback' % service_name

        cb_service = etree.SubElement(root, '{%s}service' % ns_wsdl)
        cb_service.set('name', cb_service_name)

        cb_wsdl_port = etree.SubElement(cb_service, '{%s}port' % ns_wsdl)
        cb_wsdl_port.set('name', cb_service_name)
        cb_wsdl_port.set('binding', '%s:%s' % (pref_tns, cb_service_name))

        cb_address = etree.SubElement(cb_wsdl_port, '{%s}address'
                                                          % ns_soap)
        cb_address.set('location', url)

    return cb_port_type

def add_schema(self, schema_entries):
    '''Adds the appropriate entries to the schema for the types in the specified
    methods.

    @param the schema node to add the schema elements to. if it is None,
           the schema nodes are returned inside a dictionary
    @param the schema node dictinary, where keys are prefixes of the schema
           stored schema node
    '''

    if self.__in_header__ != None:
        self.__in_header__.resolve_namespace(self.__in_header__,
                                                            self.get_tns())
        self.__in_header__.add_to_schema(schema_entries)

    if self.__out_header__ != None:
        self.__out_header__.resolve_namespace(self.__out_header__,
                                                            self.get_tns())
        self.__out_header__.add_to_schema(schema_entries)

    for method in self.public_methods:
        method.in_message.add_to_schema(schema_entries)
        method.out_message.add_to_schema(schema_entries)

        if method.in_header is None:
            method.in_header = self.__in_header__
        else:
            method.in_header.add_to_schema(schema_entries)

        if method.out_header is None:
            method.out_header = self.__out_header__
        else:
            method.out_header.add_to_schema(schema_entries)

def _add_message_for_object(self, app, root, messages, obj):
    if obj != None and not (obj.get_type_name() in messages):
        messages.add(obj.get_type_name())

        message = etree.SubElement(root, '{%s}message' % rpclib.ns_wsdl)
        message.set('name', obj.get_type_name())

        part = etree.SubElement(message, '{%s}part' % rpclib.ns_wsdl)
        part.set('name', obj.get_type_name())
        part.set('element', obj.get_type_name_ns(app))

def add_messages_for_methods(service, app, root, messages):
    '''Adds message elements to the wsdl
    @param the the root element of the wsdl
    '''

    for method in service.public_methods:
        _add_message_for_object(service, app,root,messages,method.in_message)
        _add_message_for_object(service, app,root,messages,method.out_message)
        _add_message_for_object(service, app,root,messages,method.in_header)
        _add_message_for_object(service, app,root,messages,method.out_header)

def add_bindings_for_methods(service, app, root, service_name, types, url,
                                    binding, transport, cb_binding=None):
    '''Adds bindings to the wsdl

    @param the root element of the wsdl
    @param the name of this service
    '''

    ns_wsdl = rpclib.ns_wsdl
    ns_soap = rpclib.ns_soap
    pref_tns = app.get_namespace_prefix(service.get_tns())

    if service._has_callbacks():
        if cb_binding is None:
            cb_binding = etree.SubElement(root, '{%s}binding' % ns_wsdl)
            cb_binding.set('name', '%sCallback' % service_name)
            cb_binding.set('type', 'typens:%sCallback' % service_name)

        soap_binding = etree.SubElement(cb_binding, '{%s}binding' % ns_soap)
        soap_binding.set('transport', transport)

    for method in service.public_methods:
        operation = etree.Element('{%s}operation' % ns_wsdl)
        operation.set('name', method.name)

        soap_operation = etree.SubElement(operation, '{%s}operation' %
                                                                   ns_soap)
        soap_operation.set('soapAction', method.public_name)
        soap_operation.set('style', 'document')

        # get input
        input = etree.SubElement(operation, '{%s}input' % ns_wsdl)
        input.set('name', method.in_message.get_type_name())

        soap_body = etree.SubElement(input, '{%s}body' % ns_soap)
        soap_body.set('use', 'literal')

        # get input soap header
        in_header = method.in_header
        if in_header is None:
            in_header = service.__in_header__

        if not (in_header is None):
            soap_header = etree.SubElement(input, '{%s}header' % ns_soap)
            soap_header.set('use', 'literal')
            soap_header.set('message', in_header.get_type_name_ns(app))
            soap_header.set('part', in_header.get_type_name())

        if not (method.is_async or method.is_callback):
            output = etree.SubElement(operation, '{%s}output' % ns_wsdl)
            output.set('name', method.out_message.get_type_name())

            soap_body = etree.SubElement(output, '{%s}body' % ns_soap)
            soap_body.set('use', 'literal')

            # get input soap header
            out_header = method.in_header
            if out_header is None:
                out_header = service.__in_header__

            if not (out_header is None):
                soap_header = etree.SubElement(output, '{%s}header' %
                                                                    ns_soap)
                soap_header.set('use', 'literal')
                soap_header.set('message', out_header.get_type_name_ns(app))
                soap_header.set('part', out_header.get_type_name())


        if method.is_callback:
            relates_to = etree.SubElement(input, '{%s}header' % ns_soap)

            relates_to.set('message', '%s:RelatesToHeader' % pref_tns)
            relates_to.set('part', 'RelatesTo')
            relates_to.set('use', 'literal')

            cb_binding.append(operation)

        else:
            if method.is_async:
                rt_header = etree.SubElement(input,'{%s}header' % ns_soap)
                rt_header.set('message', '%s:ReplyToHeader' % pref_tns)
                rt_header.set('part', 'ReplyTo')
                rt_header.set('use', 'literal')

                mid_header = etree.SubElement(input, '{%s}header'% ns_soap)
                mid_header.set('message', '%s:MessageIDHeader' % pref_tns)
                mid_header.set('part', 'MessageID')
                mid_header.set('use', 'literal')

            binding.append(operation)

    return cb_binding

class Wsdl11(Base):
    def __init__(self, parent, services, tns, name=None, _with_partnerlink=False):
        '''Constructor.

        @param An iterable of ServiceBase subclasses that define the exposed
               services.
        @param The targetNamespace attribute of the exposed service.
        @param The name attribute of the exposed service.
        @param Flag to indicate whether to generate partnerlink node in wsdl.
        '''
        self.parent = parent
        self.services = services
        self.__tns = tns
        self.__name = name
        self._with_plink = _with_partnerlink

        self.call_routes = {}
        self.__wsdl = None
        self.classes = {}

        self.__ns_counter = 0

        self.nsmap = dict(rpclib.const_nsmap)
        self.prefmap = dict(rpclib.const_prefmap)

        self.schema = self.build_schema()

    def get_namespace_prefix(self, ns):
        """Returns the namespace prefix for the given namespace. Creates a new
        one automatically if it doesn't exist.

        Not meant to be overridden.
        """

        if ns == "__main__":
            warnings.warn("Namespace is '__main__'", Warning )

        assert ns != "rpclib.model.base"

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

            if retval.startswith('rpclib'):
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
                import_ = etree.SubElement(schema, "{%s}import"% rpclib.ns_xsd)
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
                inst = self.parent.get_service(s)

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
        schema_entries = SchemaEntries(self)
        for s in self.services:
            inst = self.parent.get_service(s)
            add_schema(inst, schema_entries)

        schema_nodes = self.__build_schema_nodes(schema_entries, types)

        self.classes = schema_entries.classes

        return schema_nodes

    def get_schema_document(self):
        """Simple accessor method that caches application's xml schema, once
        generated.

        Not meant to be overridden.
        """
        if self.schema is None:
            return self.build_schema()
        else:
            return self.schema

    def get_interface_document(self, url):
        """Simple accessor method that caches the wsdl of the application, once
        generated.

        Not meant to be overridden.
        """
        if self.__wsdl is None:
            return self.__build_wsdl(url)
        else:
            return self.__wsdl
    get_wsdl = get_interface_document

    def __get_schema_node(self, pref, schema_nodes, types):
        """Return schema node for the given namespace prefix.

        types == None means the call is for creating a standalone xml schema
                      file for one single namespace.
        types != None means the call is for creating the wsdl file.
        """

        # create schema node
        if not (pref in schema_nodes):
            if types is None:
                schema = etree.Element("{%s}schema" % rpclib.ns_xsd,
                                                        nsmap=self.nsmap)
            else:
                schema = etree.SubElement(types, "{%s}schema" % rpclib.ns_xsd)

            schema.set("targetNamespace", self.nsmap[pref])
            schema.set("elementFormDefault", "qualified")

            schema_nodes[pref] = schema

        else:
            schema = schema_nodes[pref]

        return schema

    def __build_wsdl(self, url):
        """Build the wsdl for the application.
        """
        ns_wsdl = rpclib.ns_wsdl
        ns_soap = rpclib.ns_soap
        ns_plink = rpclib.ns_plink

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
            s=self.parent.get_service(s,None)

            add_messages_for_methods(s, self, root, messages)

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

        if self.parent.transport is None:
            raise Exception("You must set the 'transport' property")
        soap_binding.set('transport', self.parent.transport)

        cb_binding = None

        for s in self.services:
            s=self.parent.get_service(s)
            add_port_type(s, self, root, service_name, types, url, port_type)
            cb_binding = add_bindings_for_methods(s, self, root, service_name,
                                                types, url, binding, cb_binding)

        self.__wsdl = etree.tostring(root, xml_declaration=True,
                                                               encoding="UTF-8")

        return self.__wsdl

    def __add_partner_link(self, root, service_name, types, url, plink):
        """Add the partnerLinkType node to the wsdl.
        """
        ns_plink = rpclib.ns_plink
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

        wsdl_port = etree.SubElement(service, '{%s}port' % rpclib.ns_wsdl)
        wsdl_port.set('name', service_name)
        wsdl_port.set('binding', '%s:%s' % (pref_tns, service_name))

        addr = etree.SubElement(wsdl_port, '{%s}address' % rpclib.ns_soap)
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

    def on_exception_doc(self, fault_doc):
        '''Called when the app throws an exception. (might be inside or outside
        the service call.

        @param the wsgi environment
        @param the xml element containing the xml serialization of the fault
        '''

class Wsdl11Strict(Wsdl11):
    def build_schema(self, types=None):
        """Build application schema specifically for xml validation purposes.
        """
        schema_nodes = Wsdl11.build_schema(self, types)

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
