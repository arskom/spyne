
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

import soaplib
from lxml import etree

from soaplib.soap import Message
from soaplib.soap import MethodDescriptor

_ns_xs = soaplib.nsmap['xs']
_ns_wsdl = soaplib.nsmap['wsdl']
_ns_soap = soaplib.nsmap['soap']
_ns_plink = soaplib.nsmap['plink']
_ns_wsa = soaplib.nsmap['wsa']
_pref_wsa = soaplib.prefmap['http://schemas.xmlsoap.org/ws/2003/03/addressing']

def rpc(*params, **kparams):
    '''
    This is a method decorator to flag a method as a remote procedure call.  It
    will behave like a normal python method on a class, and will only behave
    differently when the keyword '_method_descriptor' is passed in, returning
    a 'MethodDescriptor' object.  This decorator does none of the soap/xml
    serialization, only flags a method as a soap method.  This decorator
    should only be used on member methods of an instance of SoapServiceBase.
    '''

    def explain(f):
        def explain_method(*args, **kwargs):
            if '_method_descriptor' in kwargs:
                # input message
                def get_input_message(ns):
                    _in_message = kparams.get('_in_message', f.func_name)
                    _in_variable_names = kparams.get('_in_variable_names', {})
                    param_names = f.func_code.co_varnames[1:f.func_code.co_argcount]

                    try:
                        in_params = {}

                        for i in range(len(params)):
                            e0 = _in_variable_names.get(param_names[i],
                                                                 param_names[i])
                            e1 = params[i]

                            in_params[e0] = e1

                    except IndexError, e:
                        raise Exception("%s has parameter numbers mismatching" %
                            f.func_name)

                    return Message(type_name=_in_message, namespace=ns,
                                                            members=in_params)

                def get_output_message(ns):
                    _returns = kparams.get('_returns')
                    _out_variable_names = kparams.get('_out_variable_names',
                            kparams.get('_out_variable_name', '%sResult' % f.func_name))
                    _out_message = kparams.get('_out_message', '%sResponse' % f.func_name)

                    out_params = {}

                    if _returns:
                        if isinstance(_returns, (list, tuple)):
                            returns = zip(_out_variable_names, _returns)
                            for key, value in returns:
                                out_params[key] = value
                        else:
                            out_params[_out_variable_names] = _returns
                    else:
                        out_params = []

                    return Message(type_name=_out_message, namespace=ns,
                                                            members=out_params)


                _is_callback = kparams.get('_is_callback', False)
                _public_name = kparams.get('_public_name', f.func_name)
                _is_async = kparams.get('_is_async', False)
                _mtom = kparams.get('_mtom', False)

                # the decorator function does not have a reference to the
                # class and needs to be passed in
                ns = kwargs['clazz'].get_tns()

                in_message = get_input_message(ns)
                out_message = get_output_message(ns)

                doc = getattr(f, '__doc__')
                descriptor = MethodDescriptor(f.func_name, _public_name,
                    in_message, out_message, doc, _is_callback, _is_async,
                    _mtom)

                return descriptor

            return f(*args, **kwargs)

        explain_method.__doc__ = f.__doc__
        explain_method._is_rpc = True
        explain_method.func_name = f.func_name

        return explain_method

    return explain


class _SchemaInfo(object):
    def __init__(self):
        self.simple = {}
        self.complex = {}

class _SchemaEntries(object):
    def __init__(self):
        self.namespaces = {}
        self.imports = {}

    def has_class(self, cls):
        retval = False

        if cls.get_namespace_prefix() == 'xs':
            retval = True

        else:
            ns_prefix = cls.get_namespace_prefix()
            type_name = cls.get_type_name()

            if ns_prefix in self.namespaces and \
                                type_name in self.namespaces[ns_prefix].complex:
                retval = True

        return retval

    def get_schema_info(self, prefix):
        if prefix in self.namespaces:
            schema = self.namespaces[prefix]
        else:
            schema = self.namespaces[prefix] = _SchemaInfo()

        return schema

    def __check_imports(self, cls, node): # TODO: incomplete
        ns = cls.get_namespace_prefix()
        if not (ns in self.imports):
            self.imports[ns] = set()

        for seq in node:
            for e in seq:
                pref = e.attrib['type'].split(':')[0]
                if not (pref in ('xs')):
                    try:
                        self.imports[ns].add(soaplib.nsmap[pref])
                    except:
                        print soaplib.nsmap
                        raise

    def add_simple_node(self, cls, node):
        schema_info = self.get_schema_info(cls.get_namespace_prefix())
        schema_info.simple[cls.get_type_name()] = node

    def add_complex_node(self, cls, node):
        self.__check_imports(cls, node)
        schema_info = self.get_schema_info(cls.get_namespace_prefix())
        schema_info.complex[cls.get_type_name()] = node

class SoapServiceBase(object):
    '''
    This class serves as the base for all soap services.  Subclasses of this
    class will use the rpc decorator to flag methods to be exposed via soap.
    This class is responsible for generating the wsdl for this object.
    '''

    __tns__ = None

    def __init__(self):
        self._soap_methods = []
        self.__wsdl = None
        self._soap_methods = self._get_soap_methods()

    @classmethod
    def get_tns(cls):
        '''
        Utility function to get the namespace of a given service class
        @param the service in question
        @return the namespace
        '''

        if not (cls.__tns__ is None):
            return cls.__tns__

        service_name = cls.__name__.split('.')[-1]

        if cls.__module__ == '__main__':
            return '.'.join((service_name, service_name))

        return '.'.join((cls.__module__, service_name))

    def _get_soap_methods(self):
        '''Returns a list of method descriptors for this object'''
        soap_methods = []

        for funcName in dir(self):
            func = getattr(self, funcName)
            if callable(func) and hasattr(func, '_is_rpc'):
                descriptor = func(_method_descriptor=True, clazz=self.__class__)
                soap_methods.append(descriptor)

        return soap_methods

    def methods(self):
        '''
        returns the soap methods for this object
        @return method descriptor list
        '''
        return self._soap_methods

    def get_method(self, name):
        '''
        Returns the metod descriptor based on element name or soap action
        '''

        for method in self.methods():
            if '{%s}%s' % (self.__tns__, method.in_message.name) == name:
                return method

        for method in self.methods():
            if method.soap_action == name:
                return method

        raise Exception('Method "%s" not found' % name)

    def _has_callbacks(self):
        '''Determines if this object has callback methods or not'''

        for method in self.methods():
            if method.is_callback:
                return True

        return False

    def header_objects(self):
        return []

    def get_service_names(self):
        '''
        Returns the service name(s) for this service. If this
        object has callbacks, then a second service is declared in
        the wsdl for those callbacks
        '''

        service_name = self.__class__.__name__.split('.')[-1]

        if self._hasCallbacks():
            return [service_name, '%sCallback' % service_name]

        return [service_name]

    def sort_xml(self, root):
        # lxml SubElement objects can only have one parent, contrary to other
        # ElementTree apis. Once a SubElement is attached to another parent, it
        # is detached from its previous parent. That's why re-appending the
        # SubElements in sorted order works.

        children = root.getchildren()
        children.sort(key=lambda x: x.tag)

        for c in children:
            root.append(c)
            self.sort_xml(c)

    def wsdl(self, url):
        '''
        This method generates and caches the wsdl for this object based
        on the soap methods designated by the rpc decorator.

        @param url the url that this service can be found at.  This must be
        passed in by the caller because this object has no notion of the
        server environment in which it runs.

        @returns the string of the wsdl
        '''
        if not self.__wsdl == None:
            # return the cached __wsdl
            return self.__wsdl

        url = url.replace('.wsdl', '')

        # otherwise build it
        # FIXME: we may want to customize service_name.
        service_name = self.__class__.__name__.split('.')[-1]

        # set the targetNamespace prefix as tns
        _ns_tns = self.get_tns()
        _pref_tns = 'tns'

        soaplib.nsmap[_pref_tns] = _ns_tns
        soaplib.prefmap[_ns_tns] = _pref_tns

        # get the methods
        methods = self.methods()
        has_callbacks = self._has_callbacks()

        types = etree.Element("{%s}types" % _ns_wsdl)
        self.__add_schema(types, methods)

        root = etree.Element("{%s}definitions" % _ns_wsdl, nsmap=soaplib.nsmap)
        root.append(types)

        root.set('targetNamespace', _ns_tns)
        root.set('name', service_name)

        self.__add_messages_for_methods(root, methods)

        # add necessary async headers
        # WS-Addressing -> RelatesTo ReplyTo MessageID
        # callback porttype
        if has_callbacks:
            wsa_schema = etree.SubElement(types, "{%s}schema" % _ns_xs)
            wsa_schema.set("targetNamespace", '%sCallback'  % _ns_tns)
            wsa_schema.set("elementFormDefault", "qualified")

            import_ = etree.SubElement(wsa_schema, "{%s}import" % _ns_xs)
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
            cb_wsdl_port.set('binding', '%s:%s' % (_pref_tns, cb_service_name))

            cb_address = etree.SubElement(cb_wsdl_port, '{%s}address' % _ns_soap)
            cb_address.set('location', url)

        port_type = etree.SubElement(root, '{%s}portType' % _ns_wsdl)
        port_type.set('name', service_name)
        for method in methods:
            if method.is_callback:
                operation = etree.SubElement(cb_port_type, '{%s}operation' % _ns_wsdl)
            else:
                operation = etree.SubElement(port_type, '{%s}operation' % _ns_wsdl)

            operation.set('name', method.name)

            if method.doc is not None:
                documentation = etree.SubElement(operation, '{%s}documentation' % _ns_wsdl)
                documentation.text = method.doc

            operation.set('parameterOrder', method.in_message.get_type_name())

            op_input = etree.SubElement(operation, '{%s}input' % _ns_wsdl)
            op_input.set('name', method.in_message.get_type_name())
            op_input.set('message', '%s:%s' % (_pref_tns, method.in_message.get_type_name()))

            if (not method.is_callback) and (not method.is_async):
                op_output = etree.SubElement(operation, '{%s}output' %  _ns_wsdl)
                op_output.set('name', method.out_message.get_type_name())
                op_output.set('message', '%s:%s' % (_pref_tns, method.out_message.get_type_name()))

        # make partner link
        plink = etree.SubElement(root, '{%s}partnerLinkType' % _ns_plink)
        plink.set('name', service_name)

        role = etree.SubElement(plink, '{%s}role' % _ns_plink)
        role.set('name', service_name)

        plink_port_type = etree.SubElement(role, '{%s}portType' % _ns_plink)
        plink_port_type.set('name', '%s:%s' % (_pref_tns,service_name))

        if has_callbacks: # adds the same elements twice. is that intended?
            role = etree.SubElement(plink, '{%s}role' % _ns_plink)
            role.set('name', '%sCallback' % service_name)

            plink_port_type = etree.SubElement(role, '{%s}portType' % _ns_plink)
            plink_port_type.set('name', '%s:%sCallback' % (_pref_tns,service_name))

        self.__add_bindings_for_methods(root, service_name, methods)

        service = etree.SubElement(root, '{%s}service' % _ns_wsdl)
        service.set('name', service_name)

        wsdl_port = etree.SubElement(service, '{%s}port' % _ns_wsdl)
        wsdl_port.set('name', service_name)
        wsdl_port.set('binding', '%s:%s' % (_pref_tns, service_name))

        addr = etree.SubElement(wsdl_port, '{%s}address' % _ns_soap)
        addr.set('location', url)

        self.sort_xml(root) # useful for debugging.
        wsdl = etree.tostring(root, xml_declaration=True, encoding="UTF-8")

        #cache the wsdl for next time
        self.__wsdl = wsdl
        return self.__wsdl

    def __add_schema(self, types, methods):
        '''
        A private method for adding the appropriate entries
        to the schema for the types in the specified methods.

        @param the schema node to add the schema elements to
        @param the list of methods.
        '''

        schema_entries = _SchemaEntries()

        for method in methods:
            method.in_message.add_to_schema(schema_entries)
            method.out_message.add_to_schema(schema_entries)

        schema_nodes = {}

        for ns in schema_entries.namespaces:
            if not (ns in schema_nodes):
                schema = etree.SubElement(types, "{%s}schema" % _ns_xs)
                schema.set("targetNamespace", soaplib.nsmap[ns])
                schema.set("elementFormDefault", "qualified")

                schema_nodes[ns] = schema

            else:
                schema = schema_nodes[ns]

            for node in schema_entries.namespaces[ns].simple.values():
                schema.append(node)

            for node in schema_entries.namespaces[ns].complex.values():
                schema.append(node)

            for namespace in schema_entries.imports[ns]:
                import_ = etree.SubElement(schema, "{%s}import" % _ns_xs)
                import_.set("namespace", namespace)

    def __add_messages_for_methods(self, root, methods):
        '''
        A private method for adding message elements to the wsdl
        @param the the root element of the wsdl
        @param the list of methods.
        '''

        _pref_tns = soaplib.get_namespace_prefix(self.get_tns())

        #make messages
        for method in methods:
            # making in part
            in_message = etree.SubElement(root, '{%s}message' % _ns_wsdl)
            in_message.set('name', method.in_message.get_type_name())

            in_part = etree.SubElement(in_message, '{%s}part' % _ns_wsdl)
            in_part.set('name', method.in_message.get_type_name())
            in_part.set('element', method.in_message.get_type_name())

            out_message = etree.SubElement(root, '{%s}message' % _ns_wsdl)
            out_message.set('name', method.out_message.get_type_name())

            out_part = etree.SubElement(out_message, '{%s}part' % _ns_wsdl)
            out_part.set('name', method.out_message.get_type_name())
            out_part.set('element', '%s:%s' % (_pref_tns, method.out_message.get_type_name()))

    def __add_bindings_for_methods(self, root, service_name, methods):
        '''
        A private method for adding bindings to the wsdl

        @param the root element of the wsdl
        @param the name of this service
        @param the methods to be add to the binding node
        '''

        has_callbacks = self._has_callbacks()
        _pref_tns = soaplib.get_namespace_prefix(self.get_tns())

        # make binding
        binding = etree.SubElement(root, '{%s}binding' % _ns_wsdl)
        binding.set('name', service_name)
        binding.set('type', '%s:%s'% (_pref_tns, service_name))

        soap_binding = etree.SubElement(binding, '{%s}binding' % _ns_soap)
        soap_binding.set('style', 'document')
        soap_binding.set('transport', 'http://schemas.xmlsoap.org/soap/http')

        if has_callbacks:
            cb_binding = etree.SubElement(root, '{%s}binding' % _ns_wsdl)
            cb_binding.set('name', '%sCallback' % service_name)
            cb_binding.set('type', 'typens:%sCallback' % service_name)

            soap_binding = etree.SubElement(cb_binding, '{%s}binding' % _ns_soap)
            soap_binding.set('transport', 'http://schemas.xmlsoap.org/soap/http')

        for method in methods:
            operation = etree.Element('{%s}operation' % _ns_wsdl)
            operation.set('name', method.name)

            soap_operation = etree.SubElement(operation, '{%s}operation' % _ns_soap)
            soap_operation.set('soapAction', method.public_name)
            soap_operation.set('style', 'document')

            input = etree.SubElement(operation, '{%s}input' % _ns_wsdl)
            input.set('name', method.in_message.get_type_name())

            soap_body = etree.SubElement(input, '{%s}body' % _ns_soap)
            soap_body.set('use', 'literal')

            if (not method.is_async) and (not method.is_callback):
                output = etree.SubElement(operation, '{%s}output' % _ns_wsdl)
                output.set('name', method.out_message.get_type_name())

                soap_body = etree.SubElement(output, '{%s}body' % _ns_soap)
                soap_body.set('use', 'literal')

            if method.is_callback:
                relates_to = etree.SubElement(input, '{%s}header' % _ns_soap)

                relates_to.set('message', '%s:RelatesToHeader' % _pref_tns)
                relates_to.set('part', 'RelatesTo')
                relates_to.set('use', 'literal')

                cb_binding.append(operation)

            else:
                if method.is_async:
                    rt_header = etree.SubElement(input,'{%s}header' % _ns_soap)
                    rt_header.set('message', '%s:ReplyToHeader' % _pref_tns)
                    rt_header.set('part', 'ReplyTo')
                    rt_header.set('use', 'literal')

                    mid_header = etree.SubElement(input, '{%s}header' % _ns_soap)
                    mid_header.set('message', '%s:MessageIDHeader' % _pref_tns)
                    mid_header.set('part', 'MessageID')
                    mid_header.set('use', 'literal')

                binding.append(operation)
