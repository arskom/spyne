
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
        self.__classes = {}

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
            inst.add_schema(schema_entries)

        schema_nodes = self.__build_schema_nodes(schema_entries, types)

        self.__classes = schema_entries.classes

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
            raise Exception("You must set the 'transport' property")
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
