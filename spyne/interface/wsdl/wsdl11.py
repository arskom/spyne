
#
# spyne - Copyright (C) Spyne contributors.
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

"""The ``spyne.interface.wsdl.wsdl11`` module contains an implementation of a
subset of the Wsdl 1.1 document standard and its helper methods.
"""

import logging
logger = logging.getLogger(__name__)

import re

import spyne.const.xml as ns

from spyne.util import six

from lxml import etree
from lxml.builder import E
from lxml.etree import SubElement

from spyne.const.xml import WSDL11, XSD, NS_WSA, PLINK
from spyne.interface.xml_schema import XmlSchema

REGEX_WSDL = re.compile('[.?]wsdl$')
PREF_WSA = ns.PREFMAP[NS_WSA]

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

    except ValueError as e:
        raise ValueError("""
            The port specified in the rpc decorator does not match any of
            the ports defined by the service class
            """)


class Wsdl11(XmlSchema):
    """The implementation of the Wsdl 1.1 interface definition document
    standard which is avaible here: http://www.w3.org/TR/wsdl

    :param app: The parent application.
    :param _with_partnerlink: Include the partnerLink tag in the wsdl.

    Supported events:
        * document_built:
            Called right after the document is built. The handler gets the
            ``Wsdl11`` instance as the only argument. Also called by XmlSchema
            class.

        * wsdl_document_built:
            Called right after the document is built. The handler gets the
            ``Wsdl11`` instance as the only argument. Only called from this
            class.
    """

    #:param import_base_namespaces: Include imports for base namespaces like
    #    xsd, xsi, wsdl, etc.

    def __init__(self, interface=None, xsl_href=None, _with_partnerlink=False,
                                              element_form_default='qualified'):
        super(Wsdl11, self).__init__(
                           interface, element_form_default=element_form_default)

        self._with_plink = _with_partnerlink
        self.xsl_href = xsl_href

        self.port_type_dict = {}
        self.service_elt_dict = {}

        self.root_elt = None
        self.service_elt = None

        self.__wsdl = None
        self.validation_schema = None

    def _get_binding_name(self, port_type_name):
        return port_type_name # subclasses override to control port names.

    def _get_or_create_port_type(self, pt_name):
        """Creates a wsdl:portType element."""

        pt = None

        if not pt_name in self.port_type_dict:
            pt = SubElement(self.root_elt, WSDL11("portType"))
            pt.set('name', pt_name)
            self.port_type_dict[pt_name] = pt

        else:
            pt = self.port_type_dict[pt_name]

        return pt

    def _get_or_create_service_node(self, service_name):
        """Builds a wsdl:service element."""

        ser = None
        if not service_name in self.service_elt_dict:
            ser = SubElement(self.root_elt, WSDL11("service"))
            ser.set('name', service_name)
            self.service_elt_dict[service_name] = ser

        else:
            ser = self.service_elt_dict[service_name]

        return ser

    def get_interface_document(self):
        return self.__wsdl

    def build_interface_document(self, url):
        """Build the wsdl for the application."""

        self.build_schema_nodes()

        self.url = REGEX_WSDL.sub('', url)

        service_name = self.interface.get_name()

        # create wsdl root node
        self.root_elt = root = etree.Element(WSDL11("definitions"),
                                                     nsmap=self.interface.nsmap)
        if self.xsl_href is not None:
            # example:
            # <?xml-stylesheet type="text/xsl" href="wsdl-viewer.xsl"?>"

            # pi.attrib.__setitem__ is ignored, so we get a proper list of
            # attributes to pass with the following hack.
            pitext = etree.tostring(etree.Element("dummy",
               dict(type='text/xsl', href=self.xsl_href)), encoding='unicode') \
                                                         .split(" ", 1)[-1][:-2]

            pi = etree.ProcessingInstruction("xml-stylesheet", pitext)
            self.root_elt.addprevious(pi)

        self.root_tree = root.getroottree()

        root.set('targetNamespace', self.interface.tns)
        root.set('name', service_name)

        # create types node
        types = SubElement(root, WSDL11("types"))
        for s in self.schema_dict.values():
            types.append(s)

        messages = set()
        for s in self.interface.services:
            self.add_messages_for_methods(s, root, messages)

        if self._with_plink:
            plink = SubElement(root, PLINK("partnerLinkType"))
            plink.set('name', service_name)
            self.__add_partner_link(service_name, plink)

        # create service nodes in advance. they're to be filled in subsequent
        # add_port_type calls.
        for s in self.interface.services:
            if not s.is_auxiliary():
                self._get_or_create_service_node(self._get_applied_service_name(s))

        # create portType nodes
        for s in self.interface.services:
            if not s.is_auxiliary():
                self.add_port_type(s, root, service_name, types, self.url)

        cb_binding = None
        for s in self.interface.services:
            if not s.is_auxiliary():
                cb_binding = self.add_bindings_for_methods(s, root,
                                                   service_name, cb_binding)

        if self.interface.app.transport is None:
            raise Exception("You must set the 'transport' property of the "
                            "parent 'Application' instance")

        self.event_manager.fire_event('document_built', self)
        self.event_manager.fire_event('wsdl_document_built', self)

        self.__wsdl = etree.tostring(self.root_tree, xml_declaration=True,
                                                               encoding="UTF-8")

    def __add_partner_link(self, service_name, plink):
        """Add the partnerLinkType node to the wsdl."""

        ns_tns = self.interface.tns
        pref_tns = self.interface.get_namespace_prefix(ns_tns)

        role = SubElement(plink, PLINK("role"))
        role.set('name', service_name)

        plink_port_type = SubElement(role, PLINK("portType"))
        plink_port_type.set('name', '%s:%s' % (pref_tns, service_name))

        if self._has_callbacks():
            role = SubElement(plink, PLINK("role"))
            role.set('name', '%sCallback' % service_name)

            plink_port_type = SubElement(role, PLINK("portType"))
            plink_port_type.set('name', '%s:%sCallback' %
                                                       (pref_tns, service_name))

    def _add_port_to_service(self, service, port_name, binding_name):
        """ Builds a wsdl:port for a service and binding"""

        pref_tns = self.interface.get_namespace_prefix(self.interface.tns)

        wsdl_port = SubElement(service, WSDL11("port"))
        wsdl_port.set('name', port_name)
        wsdl_port.set('binding', '%s:%s' % (pref_tns, binding_name))

        addr = SubElement(wsdl_port,
              ns.get_binding_ns(self.interface.app.in_protocol.type)("address"))

        addr.set('location', self.url)

    def _has_callbacks(self):
        for s in self.interface.services:
            if s._has_callbacks():
                return True

        return False

    def _get_applied_service_name(self, service):
        if service.get_service_name() is None:
            # This is the default behavior. i.e. no service interface is
            # defined in the service heading
            if len(self.interface.services) == 1:
                retval = self.get_name()
            else:
                retval = service.get_service_class_name()
        else:
            retval = service.get_service_name()

        return retval

    def add_port_type(self, service, root, service_name, types, url):
        # FIXME: I don't think this call is working.
        cb_port_type = self._add_callbacks(service, root, types,
                                                              service_name, url)
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

        for method in service.public_methods.values():
            check_method_port(service, method)

            if method.is_callback:
                operation = SubElement(cb_port_type, WSDL11("operation"))
            else:
                operation = SubElement(port_type, WSDL11("operation"))

            operation.set('name', method.operation_name)

            if method.doc is not None:
                operation.append(E(WSDL11("documentation"), method.doc))

            operation.set('parameterOrder', method.in_message.get_element_name())

            op_input = SubElement(operation, WSDL11("input"))
            op_input.set('name', method.in_message.get_element_name())
            op_input.set('message',
                          method.in_message.get_element_name_ns(self.interface))

            if (not method.is_callback) and (not method.is_async):
                op_output = SubElement(operation, WSDL11("output"))
                op_output.set('name', method.out_message.get_element_name())
                op_output.set('message', method.out_message.get_element_name_ns(
                                                                self.interface))

                if not (method.faults is None):
                    for f in method.faults:
                        fault = SubElement(operation, WSDL11("fault"))
                        fault.set('name', f.get_type_name())
                        fault.set('message', '%s:%s' % (
                                        f.get_namespace_prefix(self.interface),
                                        f.get_type_name()))

        ser = self.service_elt_dict[applied_service_name]
        for port_name, binding_name in port_binding_names:
            self._add_port_to_service(ser, port_name, binding_name)

    def _add_message_for_object(self, root, messages, obj, message_name):
        if obj is not None and not (message_name in messages):
            messages.add(message_name)

            message = SubElement(root, WSDL11("message"))
            message.set('name', message_name)

            if isinstance(obj, (list, tuple)):
                objs = obj
            else:
                objs = (obj,)

            for obj in objs:
                part = SubElement(message, WSDL11("part"))
                part.set('name', obj.get_wsdl_part_name())
                part.set('element', obj.get_element_name_ns(self.interface))

    def add_messages_for_methods(self, service, root, messages):
        for method in service.public_methods.values():
            self._add_message_for_object(root, messages, method.in_message,
                                    method.in_message.get_element_name())
            self._add_message_for_object(root, messages, method.out_message,
                                    method.out_message.get_element_name())

            if method.in_header is not None:
                if len(method.in_header) > 1:
                    in_header_message_name = ''.join((method.name,
                                                      _in_header_msg_suffix))
                else:
                    in_header_message_name = method.in_header[0].get_type_name()
                self._add_message_for_object(root, messages,
                                    method.in_header, in_header_message_name)

            if method.out_header is not None:
                if len(method.out_header) > 1:
                    out_header_message_name = ''.join((method.name,
                                                       _out_header_msg_suffix))
                else:
                    out_header_message_name = method.out_header[0].get_type_name()
                self._add_message_for_object(root, messages,
                                    method.out_header, out_header_message_name)

            for fault in method.faults:
                self._add_message_for_object(root, messages, fault,
                                        fault.get_type_name())

    def add_bindings_for_methods(self, service, root, service_name,
                                     cb_binding):

        pref_tns = self.interface.get_namespace_prefix(self.interface.get_tns())
        input_binding_ns = ns.get_binding_ns(self.interface.app.in_protocol.type)
        output_binding_ns = ns.get_binding_ns(self.interface.app.out_protocol.type)

        def inner(method, binding):
            operation = etree.Element(WSDL11("operation"))
            operation.set('name', method.operation_name)

            soap_operation = SubElement(operation, input_binding_ns("operation"))
            soap_operation.set('soapAction', method.operation_name)
            soap_operation.set('style', 'document')

            # get input
            input = SubElement(operation, WSDL11("input"))
            input.set('name', method.in_message.get_element_name())

            soap_body = SubElement(input, input_binding_ns("body"))
            soap_body.set('use', 'literal')

            # get input soap header
            in_header = method.in_header
            if in_header is None:
                in_header = service.__in_header__

            if not (in_header is None):
                if isinstance(in_header, (list, tuple)):
                    in_headers = in_header
                else:
                    in_headers = (in_header,)

                if len(in_headers) > 1:
                    in_header_message_name = ''.join((method.name,
                                                      _in_header_msg_suffix))
                else:
                    in_header_message_name = in_headers[0].get_type_name()

                for header in in_headers:
                    soap_header = SubElement(input, input_binding_ns('header'))
                    soap_header.set('use', 'literal')
                    soap_header.set('message', '%s:%s' % (
                                header.get_namespace_prefix(self.interface),
                                in_header_message_name))
                    soap_header.set('part', header.get_type_name())

            if not (method.is_async or method.is_callback):
                output = SubElement(operation, WSDL11("output"))
                output.set('name', method.out_message.get_element_name())

                soap_body = SubElement(output, output_binding_ns("body"))
                soap_body.set('use', 'literal')

                # get output soap header
                out_header = method.out_header
                if out_header is None:
                    out_header = service.__out_header__

                if not (out_header is None):
                    if isinstance(out_header, (list, tuple)):
                        out_headers = out_header
                    else:
                        out_headers = (out_header,)

                    if len(out_headers) > 1:
                        out_header_message_name = ''.join((method.name,
                                                        _out_header_msg_suffix))
                    else:
                        out_header_message_name = out_headers[0].get_type_name()

                    for header in out_headers:
                        soap_header = SubElement(output, output_binding_ns("header"))
                        soap_header.set('use', 'literal')
                        soap_header.set('message', '%s:%s' % (
                                header.get_namespace_prefix(self.interface),
                                out_header_message_name))
                        soap_header.set('part', header.get_type_name())

                if not (method.faults is None):
                    for f in method.faults:
                        wsdl_fault = SubElement(operation, WSDL11("fault"))
                        wsdl_fault.set('name', f.get_type_name())

                        soap_fault = SubElement(wsdl_fault, input_binding_ns("fault"))
                        soap_fault.set('name', f.get_type_name())
                        soap_fault.set('use', 'literal')

            if method.is_callback:
                relates_to = SubElement(input, input_binding_ns("header"))

                relates_to.set('message', '%s:RelatesToHeader' % pref_tns)
                relates_to.set('part', 'RelatesTo')
                relates_to.set('use', 'literal')

                cb_binding.append(operation)

            else:
                if method.is_async:
                    rt_header = SubElement(input, input_binding_ns("header"))
                    rt_header.set('message', '%s:ReplyToHeader' % pref_tns)
                    rt_header.set('part', 'ReplyTo')
                    rt_header.set('use', 'literal')

                    mid_header = SubElement(input, input_binding_ns("header"))
                    mid_header.set('message', '%s:MessageIDHeader' % pref_tns)
                    mid_header.set('part', 'MessageID')
                    mid_header.set('use', 'literal')

                binding.append(operation)

        port_type_list = service.get_port_types()
        if len(port_type_list) > 0:
            for port_type_name in port_type_list:

                # create binding nodes
                binding = SubElement(root, WSDL11("binding"))
                binding.set('name', self._get_binding_name(port_type_name))
                binding.set('type', '%s:%s'% (pref_tns, port_type_name))

                transport = SubElement(binding, input_binding_ns("binding"))
                transport.set('style', 'document')
                transport.set('transport', self.interface.app.transport)

                for m in service.public_methods.values():
                    if m.port_type == port_type_name:
                        inner(m, binding)

        else:
            # here is the default port.
            if cb_binding is None:
                cb_binding = SubElement(root, WSDL11("binding"))
                cb_binding.set('name', service_name)
                cb_binding.set('type', '%s:%s'% (pref_tns, service_name))

                transport = SubElement(cb_binding, input_binding_ns("binding"))
                transport.set('style', 'document')
                transport.set('transport', self.interface.app.transport)

            for m in service.public_methods.values():
                inner(m, cb_binding)

        return cb_binding

    # FIXME: I don't think this is working.
    def _add_callbacks(self, service, root, types, service_name, url):
        ns_tns = self.interface.get_tns()
        pref_tns = 'tns'
        input_binding_ns = ns.get_binding_ns(self.interface.app.in_protocol.type)

        cb_port_type = None

        # add necessary async headers
        # WS-Addressing -> RelatesTo ReplyTo MessageID
        # callback porttype
        if service._has_callbacks():
            wsa_schema = SubElement(types, XSD("schema"))
            wsa_schema.set("targetNamespace", '%sCallback'  % ns_tns)
            wsa_schema.set("elementFormDefault", "qualified")

            import_ = SubElement(wsa_schema, XSD("import"))
            import_.set("namespace", NS_WSA)
            import_.set("schemaLocation", NS_WSA)

            relt_message = SubElement(root, WSDL11("message"))
            relt_message.set('name', 'RelatesToHeader')
            relt_part = SubElement(relt_message, WSDL11("part"))
            relt_part.set('name', 'RelatesTo')
            relt_part.set('element', '%s:RelatesTo' % PREF_WSA)

            reply_message = SubElement(root, WSDL11("message"))
            reply_message.set('name', 'ReplyToHeader')
            reply_part = SubElement(reply_message, WSDL11("part"))
            reply_part.set('name', 'ReplyTo')
            reply_part.set('element', '%s:ReplyTo' % PREF_WSA)

            id_header = SubElement(root, WSDL11("message"))
            id_header.set('name', 'MessageIDHeader')
            id_part = SubElement(id_header, WSDL11("part"))
            id_part.set('name', 'MessageID')
            id_part.set('element', '%s:MessageID' % PREF_WSA)

            # make portTypes
            cb_port_type = SubElement(root, WSDL11("portType"))
            cb_port_type.set('name', '%sCallback' % service_name)

            cb_service_name = '%sCallback' % service_name

            cb_service = SubElement(root, WSDL11("service"))
            cb_service.set('name', cb_service_name)

            cb_wsdl_port = SubElement(cb_service, WSDL11("port"))
            cb_wsdl_port.set('name', cb_service_name)
            cb_wsdl_port.set('binding', '%s:%s' % (pref_tns, cb_service_name))

            cb_address = SubElement(cb_wsdl_port, input_binding_ns("address"))
            cb_address.set('location', url)

        return cb_port_type
