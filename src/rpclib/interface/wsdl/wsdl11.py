
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

"""This module contains the Wsdl 1.1 document standard implementation and
its helper methods."""

import logging
logger = logging.getLogger(__name__)

import rpclib.const.xml_ns

from lxml import etree

from rpclib.interface.xml_schema import XmlSchema

_ns_plink = rpclib.const.xml_ns.plink
_ns_xsd = rpclib.const.xml_ns.xsd
_ns_wsa = rpclib.const.xml_ns.wsa
_ns_wsdl = rpclib.const.xml_ns.wsdl
_ns_soap = rpclib.const.xml_ns.soap
_pref_wsa = rpclib.const.xml_ns.const_prefmap[_ns_wsa]

_in_header_msg_suffix = 'InHeaderMsg'
_out_header_msg_suffix = 'OutHeaderMsg'

def check_method_port(service, method):
    if len(service.__port_types__) != 0 and method.port_type is None:
        raise ValueError("""
            A port must be declared in the RPC decorator if the service
            class declares a list of ports

            Method: %r
            """ % method.name)

    if (not method.port_type is None) and len(service.__port_types__) == 0:
        raise ValueError("""
            The rpc decorator has declared a port while the service class
            has not.  Remove the port declaration from the rpc decorator
            or add a list of ports to the service class
            """)
    try:
        if (not method.port_type is None):
            index = service.__port_types__.index(method.port_type)

    except ValueError, e:
        raise ValueError("""
            The port specified in the rpc decorator does not match any of
            the ports defined by the service class
            """)

# FIXME: I don't think this is working.
def _add_callbacks(service, root, types, service_name, url):
    ns_tns = service.get_tns()
    pref_tns = 'tns'

    cb_port_type = None

    # add necessary async headers
    # WS-Addressing -> RelatesTo ReplyTo MessageID
    # callback porttype
    if service._has_callbacks():
        wsa_schema = etree.SubElement(types, "{%s}schema" % _ns_xsd)
        wsa_schema.set("targetNamespace", '%sCallback'  % ns_tns)
        wsa_schema.set("elementFormDefault", "qualified")

        import_ = etree.SubElement(wsa_schema, "{%s}import" % _ns_xsd)
        import_.set("namespace", _ns_wsa)
        import_.set("schemaLocation", _ns_wsa)

        relt_message = etree.SubElement(root, '{%s}message' % _ns_wsdl)
        relt_message.set('name', 'RelatesToHeader')
        relt_part = etree.SubElement(relt_message, '{%s}part' % _ns_wsdl)
        relt_part.set('name', 'RelatesTo')
        relt_part.set('element', '%s:RelatesTo' % _pref_wsa)

        reply_message = etree.SubElement(root, '{%s}message' % _ns_wsdl)
        reply_message.set('name', 'ReplyToHeader')
        reply_part = etree.SubElement(reply_message, '{%s}part' % _ns_wsdl)
        reply_part.set('name', 'ReplyTo')
        reply_part.set('element', '%s:ReplyTo' % _pref_wsa)

        id_header = etree.SubElement(root, '{%s}message' % _ns_wsdl)
        id_header.set('name', 'MessageIDHeader')
        id_part = etree.SubElement(id_header, '{%s}part' % _ns_wsdl)
        id_part.set('name', 'MessageID')
        id_part.set('element', '%s:MessageID' % _pref_wsa)

        # make portTypes
        cb_port_type = etree.SubElement(root, '{%s}portType' % _ns_wsdl)
        cb_port_type.set('name', '%sCallback' % service_name)

        cb_service_name = '%sCallback' % service_name

        cb_service = etree.SubElement(root, '{%s}service' % _ns_wsdl)
        cb_service.set('name', cb_service_name)

        cb_wsdl_port = etree.SubElement(cb_service, '{%s}port' % _ns_wsdl)
        cb_wsdl_port.set('name', cb_service_name)
        cb_wsdl_port.set('binding', '%s:%s' % (pref_tns, cb_service_name))

        cb_address = etree.SubElement(cb_wsdl_port, '{%s}address' % _ns_soap)
        cb_address.set('location', url)

    return cb_port_type

class Wsdl11(XmlSchema):
    """The implementation of the Wsdl 1.1 interface definition document standard."""

    def __init__(self, app=None, import_base_namespaces=False,
                                                       _with_partnerlink=False):
        '''Constructor.

        :param app: The parent application.
        :param import_base_namespaces: Include imports for base namespaces like
                                       xsd, xsi, wsdl, etc.
        :param _with_partnerlink: Include the partnerLink tag in the wsdl.
        '''
        XmlSchema.__init__(self, app, import_base_namespaces)

        self._with_plink = _with_partnerlink

        self.port_type_dict = {}
        self.service_elt_dict = {}

        self.root_elt = None
        self.service_elt = None

        self.__wsdl = None
        self.validation_schema = None

    def _get_binding_name(self, port_type_name):
        return port_type_name # subclasses override to control port names.

    def _get_or_create_port_type(self, pt_name):
        """ Creates a wsdl:portType element. """

        pt = None

        if not pt_name in self.port_type_dict:
            pt = etree.SubElement(self.root_elt, '{%s}portType' % _ns_wsdl)
            pt.set('name', pt_name)
            self.port_type_dict[pt_name] = pt

        else:
            pt = self.port_type_dict[pt_name]

        return pt

    def _get_or_create_service_node(self, service_name):
        ''' Builds a wsdl:service element. '''

        ser = None
        if not service_name in self.service_elt_dict:
            ser = etree.SubElement(self.root_elt, '{%s}service' % _ns_wsdl)
            ser.set('name', service_name)
            self.service_elt_dict[service_name] = ser

        else:
            ser = self.service_elt_dict[service_name]

        return ser

    def get_interface_document(self):
        return self.__wsdl

    def build_interface_document(self, url):
        """Build the wsdl for the application."""

        pref_tns = self.get_namespace_prefix(self.tns)

        self.url = url.replace('.wsdl', '') # FIXME: doesn't look so robust

        service_name = self.get_name()

        # create wsdl root node
        self.root_elt = root = etree.Element("{%s}definitions" % _ns_wsdl,
                                                               nsmap=self.nsmap)

        root.set('targetNamespace', self.tns)
        root.set('name', service_name)

        # create types node
        types = etree.SubElement(root, "{%s}types" % _ns_wsdl)
        self.build_schema_nodes()
        for s in self.schema_dict.values():
            types.append(s)

        messages = set()
        for s in self.services:
            self.add_messages_for_methods(s, root, messages)

        if self._with_plink:
            plink = etree.SubElement(root, '{%s}partnerLinkType' % _ns_plink)
            plink.set('name', service_name)
            self.__add_partner_link(service_name, plink)

        # create service nodes in advance. they're to be filled in subsequent
        # add_port_type calls.
        for s in self.services:
            self._get_or_create_service_node(self._get_applied_service_name(s))

        # create portType nodes
        for s in self.services:
            self.add_port_type(s, root, service_name, types, self.url)

        cb_binding = None
        for s in self.services:
            cb_binding = self.add_bindings_for_methods(s, root, service_name,
                                                       cb_binding)

        if self.app.transport is None:
            raise Exception("You must set the 'transport' property of the "
                            "parent 'Application' instance")

        self.__wsdl = etree.tostring(root, xml_declaration=True,
                                                               encoding="UTF-8")

    def __add_partner_link(self, service_name, plink):
        """Add the partnerLinkType node to the wsdl."""

        ns_tns = self.get_tns()
        pref_tns = self.get_namespace_prefix(ns_tns)

        role = etree.SubElement(plink, '{%s}role' % _ns_plink)
        role.set('name', service_name)

        plink_port_type = etree.SubElement(role, '{%s}portType' % _ns_plink)
        plink_port_type.set('name', '%s:%s' % (pref_tns, service_name))

        if self._has_callbacks():
            role = etree.SubElement(plink, '{%s}role' % _ns_plink)
            role.set('name', '%sCallback' % service_name)

            plink_port_type = etree.SubElement(role, '{%s}portType' % _ns_plink)
            plink_port_type.set('name', '%s:%sCallback' %
                                                       (pref_tns, service_name))

    def _add_port_to_service(self, service, port_name, binding_name):
        """ Builds a wsdl:port for a service and binding"""

        pref_tns = self.get_namespace_prefix(
            self.get_tns()
        )

        wsdl_port = etree.SubElement(service, '{%s}port' % _ns_wsdl)
        wsdl_port.set('name', port_name)
        wsdl_port.set('binding', '%s:%s' % (pref_tns, binding_name))

        addr = etree.SubElement(wsdl_port, '{%s}address' % _ns_soap)
        addr.set('location', self.url)

    def _has_callbacks(self):
        for s in self.services:
            if s._has_callbacks():
                return True

        return False

    def _get_applied_service_name(self, service):
        if service.get_service_name() is None:
            # This is the default behavior. i.e. no service interface is
            # defined in the service heading
            if len(self.services) == 1:
                retval = self.get_name()
            else:
                retval = service.get_service_class_name()
        else:
            retval = service.get_service_name()

        return retval

    def add_port_type(self, service, root, service_name, types, url):
        # FIXME: I don't think this call is working.
        cb_port_type = _add_callbacks(service, root, types, service_name, url)
        applied_service_name = self._get_applied_service_name(service)

        port_binding_names = []
        port_type_list = service.get_port_types()
        if len(port_type_list) > 0:
            for port_type_name in port_type_list:
                port_type = self._get_or_create_port_type(port_type_name)
                port_type.set('name', port_type_name)

                binding_name = self._get_binding_name(port_type_name)
                port_binding_names.append((port_type_name, binding_name))

        else:
            port_type = self._get_or_create_port_type(service_name)
            port_type.set('name', service_name)

            binding_name = self._get_binding_name(service_name)
            port_binding_names.append((service_name, binding_name))

        port_name = port_type.get('name')

        for method in service.public_methods.values():
            check_method_port(service, method)

            if method.is_callback:
                operation = etree.SubElement(cb_port_type, '{%s}operation'
                                                                    % _ns_wsdl)
            else:
                operation = etree.SubElement(port_type, '{%s}operation'
                                                                    % _ns_wsdl)

            operation.set('name', method.name)

            if method.doc is not None:
                documentation = etree.SubElement(operation, '{%s}documentation'
                                                                    % _ns_wsdl)
                documentation.text = method.doc

            operation.set('parameterOrder', method.in_message.get_type_name())

            op_input = etree.SubElement(operation, '{%s}input' % _ns_wsdl)
            op_input.set('name', method.in_message.get_type_name())
            op_input.set('message', method.in_message.get_type_name_ns(self))

            if (not method.is_callback) and (not method.is_async):
                op_output = etree.SubElement(operation, '{%s}output' % _ns_wsdl)
                op_output.set('name', method.out_message.get_type_name())
                op_output.set('message', method.out_message.get_type_name_ns(self))

                if not (method.faults is None):
                    for f in method.faults:
                        fault = etree.SubElement(operation, '{%s}fault' %
                                                                       _ns_wsdl)
                        fault.set('name', f.get_type_name())
                        fault.set('message', '%s:%s' % (
                                                f.get_namespace_prefix(self),
                                                f.get_type_name()))

        ser = self._get_or_create_service_node(applied_service_name)
        for port_name, binding_name in port_binding_names:
            self._add_port_to_service(ser, port_name, binding_name)

    def _add_message_for_object(self, root, messages, obj, message_name):
        if obj is not None and not (message_name in messages):
            messages.add(message_name)

            message = etree.SubElement(root, '{%s}message' % _ns_wsdl)
            message.set('name', message_name)

            if isinstance(obj, (list, tuple)):
                objs = obj
            else:
                objs = (obj,)
            for obj in objs:
                part = etree.SubElement(message, '{%s}part' % _ns_wsdl)
                part.set('name', obj.get_type_name())
                part.set('element', obj.get_type_name_ns(self))

    def add_messages_for_methods(self, service, root, messages):
        for method in service.public_methods.values():
            self._add_message_for_object(root, messages, method.in_message,
                                    method.in_message.get_type_name())
            self._add_message_for_object(root, messages, method.out_message,
                                    method.out_message.get_type_name())

            if method.in_header is not None:
                if isinstance(method.in_header, (list, tuple)):
                    in_header_message_name = ''.join((method.name,
                                                      _in_header_msg_suffix))
                else:
                    in_header_message_name = method.in_header.get_type_name()
                self._add_message_for_object(root, messages,
                                    method.in_header, in_header_message_name)

            if method.out_header is not None:
                if isinstance(method.out_header, (list, tuple)):
                    out_header_message_name = ''.join((method.name,
                                                       _out_header_msg_suffix))
                else:
                    out_header_message_name = method.out_header.get_type_name()
                self._add_message_for_object(root, messages,
                                    method.out_header, out_header_message_name)

            for fault in method.faults:
                self._add_message_for_object(root, messages, fault,
                                        fault.get_type_name())

    def add_bindings_for_methods(self, service, root, service_name,
                                     cb_binding):

        pref_tns = self.get_namespace_prefix(service.get_tns())
        
        def inner(binding):
            for method in service.public_methods.values():
                operation = etree.Element('{%s}operation' % _ns_wsdl)
                operation.set('name', method.name)

                soap_operation = etree.SubElement(operation, '{%s}operation'
                                                                        % _ns_soap)
                soap_operation.set('soapAction', method.name)
                soap_operation.set('style', 'document')

                # get input
                input = etree.SubElement(operation, '{%s}input' % _ns_wsdl)
                input.set('name', method.in_message.get_type_name())

                soap_body = etree.SubElement(input, '{%s}body' % _ns_soap)
                soap_body.set('use', 'literal')

                # get input soap header
                in_header = method.in_header
                if in_header is None:
                    in_header = service.__in_header__

                if not (in_header is None):
                    if isinstance(in_header, (list, tuple)):
                        in_headers = in_header
                        in_header_message_name = ''.join((method.name,
                                                          _in_header_msg_suffix))
                    else:
                        in_headers = (in_header,)
                        in_header_message_name = in_header.get_type_name()

                    for header in in_headers:
                        soap_header = etree.SubElement(input, '{%s}header' % _ns_soap)
                        soap_header.set('use', 'literal')
                        soap_header.set('message', '%s:%s' % (
                                                header.get_namespace_prefix(self),
                                                in_header_message_name))
                        soap_header.set('part', header.get_type_name())

                if not (method.is_async or method.is_callback):
                    output = etree.SubElement(operation, '{%s}output' % _ns_wsdl)
                    output.set('name', method.out_message.get_type_name())

                    soap_body = etree.SubElement(output, '{%s}body' % _ns_soap)
                    soap_body.set('use', 'literal')

                    # get output soap header
                    out_header = method.out_header
                    if out_header is None:
                        out_header = service.__out_header__

                    if not (out_header is None):
                        if isinstance(out_header, (list, tuple)):
                            out_headers = out_header
                            out_header_message_name = ''.join((method.name,
                                                            _out_header_msg_suffix))
                        else:
                            out_headers = (out_header,)
                            out_header_message_name = out_header.get_type_name()

                        for header in out_headers:
                            soap_header = etree.SubElement(output, '{%s}header'
                                                                        % _ns_soap)
                            soap_header.set('use', 'literal')
                            soap_header.set('message', '%s:%s' % (
                                                header.get_namespace_prefix(self),
                                                out_header_message_name))
                            soap_header.set('part', header.get_type_name())

                    if not (method.faults is None):
                        for f in method.faults:
                            wsdl_fault = etree.SubElement(operation, '{%s}fault' %
                                                                        _ns_wsdl)
                            wsdl_fault.set('name', f.get_type_name())

                            soap_fault = etree.SubElement(wsdl_fault, '{%s}fault' %
                                                                        _ns_soap)
                            soap_fault.set('name', f.get_type_name())
                            soap_fault.set('use', 'literal')

                if method.is_callback:
                    relates_to = etree.SubElement(input, '{%s}header' % _ns_soap)

                    relates_to.set('message', '%s:RelatesToHeader' % pref_tns)
                    relates_to.set('part', 'RelatesTo')
                    relates_to.set('use', 'literal')

                    cb_binding.append(operation)

                else:
                    if method.is_async:
                        rt_header = etree.SubElement(input, '{%s}header' % _ns_soap)
                        rt_header.set('message', '%s:ReplyToHeader' % pref_tns)
                        rt_header.set('part', 'ReplyTo')
                        rt_header.set('use', 'literal')

                        mid_header = etree.SubElement(input, '{%s}header'% _ns_soap)
                        mid_header.set('message', '%s:MessageIDHeader' % pref_tns)
                        mid_header.set('part', 'MessageID')
                        mid_header.set('use', 'literal')

                    binding.append(operation)
        
        port_type_list = service.get_port_types()
        if len(port_type_list) > 0:
            for port_type_name in port_type_list:
                
                # create binding nodes
                binding = etree.SubElement(root, '{%s}binding' % _ns_wsdl)
                binding.set('name', port_type_name)
                binding.set('type', '%s:%s'% (pref_tns, port_type_name))

                transport = etree.SubElement(binding, '{%s}binding' % _ns_soap)
                transport.set('style', 'document')
                
                inner(binding)

        else:
            # here is the default port.
            if cb_binding is None:
                cb_binding = etree.SubElement(root, '{%s}binding' % _ns_wsdl)
                cb_binding.set('name', service_name)
                cb_binding.set('type', '%s:%s'% (pref_tns, service_name))

                transport = etree.SubElement(cb_binding, '{%s}binding' % _ns_soap)
                transport.set('style', 'document')
                transport.set('transport', self.app.transport)
            
            inner(cb_binding)

        return cb_binding