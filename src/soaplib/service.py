
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

import tempfile
import shutil

import soaplib
from lxml import etree

from soaplib.soap import Message
from soaplib.soap import MethodDescriptor
from soaplib.serializers.clazz import TypeInfo

_pref_wsa = soaplib.prefmap[soaplib.ns_wsa]

def rpc(*params, **kparams):
    '''
    This is a method decorator to flag a method as a remote procedure call.  It
    will behave like a normal python method on a class, and will only behave
    differently when the keyword '_method_descriptor' is passed in, returning a
    'MethodDescriptor' object.  This decorator does none of the soap/xml
    serialization, only flags a method as a soap method.  This decorator should
    only be used on member methods of an instance of ServiceBase.
    '''

    def explain(f):
        def explain_method(*args, **kwargs):
            if '_method_descriptor' in kwargs:
                # input message
                def get_input_message(ns):
                    _in_message = kparams.get('_in_message', f.func_name)
                    _in_variable_names = kparams.get('_in_variable_names', {})

                    arg_count = f.func_code.co_argcount
                    param_names = f.func_code.co_varnames[1:arg_count]

                    try:
                        in_params = TypeInfo()

                        for i in range(len(params)):
                            e0 = _in_variable_names.get(param_names[i],
                                                                 param_names[i])
                            e1 = params[i]

                            in_params[e0] = e1

                    except IndexError, e:
                        raise Exception("%s has parameter numbers mismatching" %
                                                                    f.func_name)

                    message=Message.produce(type_name=_in_message, namespace=ns,
                                                            members=in_params)
                    message.resolve_namespace(ns)
                    return message

                def get_output_message(ns):
                    _returns = kparams.get('_returns')

                    _out_message = kparams.get('_out_message', '%sResponse' %
                                                                    f.func_name)

                    kparams.get('_out_variable_name')
                    out_params = TypeInfo()

                    if _returns:
                        if isinstance(_returns, (list, tuple)):
                            default_names = ['%sResult%d' % (f.func_name, i)
                                                  for i in range(len(_returns))]

                            _out_variable_names = kparams.get(
                                        '_out_variable_names', default_names)

                            assert (len(_returns) == len(_out_variable_names))

                            var_pair = zip(_out_variable_names,_returns)
                            out_params = TypeInfo(var_pair)

                        else:
                            _out_variable_name = kparams.get(
                                 '_out_variable_name', '%sResult' % f.func_name)

                            out_params[_out_variable_name] = _returns

                    message=Message.produce(type_name=_out_message,namespace=ns,
                                                             members=out_params)
                    message.resolve_namespace(ns)
                    return message

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
        self.elements = {}
        self.types = {}

class _SchemaEntries(object):
    def __init__(self, tns):
        self.namespaces = {}
        self.imports = {}
        self.tns = tns

    def has_class(self, cls):
        retval = False
        ns_prefix = cls.get_namespace_prefix()

        if ns_prefix == 'xs':
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
        pref_tns = cls.get_namespace_prefix()
        if not (pref_tns in self.imports):
            self.imports[pref_tns] = set()

        for c in node:
            if c.tag == "{%s}complexContent" % soaplib.ns_xsd:
                seq = c.getchildren()[0].getchildren()[0] # FIXME: ugly, isn't it?
            else:
                seq = c

            if seq.tag == '{%s}sequence' % soaplib.ns_xsd:
                for e in seq:
                    pref = e.attrib['type'].split(':')[0]
                    if not ((pref in soaplib.const_prefmap) or (pref == pref_tns)):
                        self.imports[pref_tns].add(soaplib.nsmap[pref])

            elif seq.tag == '{%s}restriction' % soaplib.ns_xsd:
                pref = seq.attrib['base'].split(':')[0]
                if not ((pref in soaplib.const_prefmap) or (pref == pref_tns)):
                    self.imports[pref_tns].add(soaplib.nsmap[pref])

            else:
                raise Exception("i guess you need to hack some more")


    def add_element(self, cls, node):
        schema_info = self.get_schema_info(cls.get_namespace_prefix())
        schema_info.elements[cls.get_type_name()] = node

    def add_simple_type(self, cls, node):
        self.__check_imports(cls, node)
        schema_info = self.get_schema_info(cls.get_namespace_prefix())
        schema_info.types[cls.get_type_name()] = node

    def add_complex_type(self, cls, node):
        self.__check_imports(cls, node)
        schema_info = self.get_schema_info(cls.get_namespace_prefix())
        schema_info.types[cls.get_type_name()] = node

class Definition(object):
    '''
    This class serves as the base for all soap services.  Subclasses of this
    class will use the rpc decorator to flag methods to be exposed via soap.
    This class is responsible for generating the wsdl for this service
    definition.
    '''

    __tns__ = None

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

    def on_method_exec(self, environ, method_name, py_params, soap_params):
        '''
        Called BEFORE the service implementing the functionality is called
        @param the wsgi environment
        @param the method name
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

    def __init__(self, environ):
        self._remote_methods = self._get_remote_methods()

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

    def _get_remote_methods(self):
        '''Returns a list of method descriptors for this object'''
        remote_methods = []

        for funcName in dir(self):
            func = getattr(self, funcName)
            if callable(func) and hasattr(func, '_is_rpc'):
                descriptor = func(_method_descriptor=True, clazz=self.__class__)
                remote_methods.append(descriptor)

        return remote_methods

    def methods(self):
        '''
        returns the soap methods for this object
        @return method descriptor list
        '''
        return self._remote_methods

    def get_method(self, name):
        '''
        Returns the metod descriptor based on element name or soap action
        '''

        for method in self.methods():
            type_name = method.in_message.get_type_name()
            if '{%s}%s' % (self.get_tns(), type_name) == name:
                return method

        for method in self.methods():
            if method.public_name == name:
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

    def get_wsdl(self, url):
        '''
        This method generates and caches the wsdl for this object based
        on the soap methods designated by the rpc decorator.

        @param url the url that this service can be found at.  This must be
        passed in by the caller because this object has no notion of the
        server environment in which it runs.

        @returns the string of the wsdl
        '''

        url = url.replace('.wsdl', '')

        ns_wsdl = soaplib.ns_wsdl
        ns_soap = soaplib.ns_soap
        ns_plink = soaplib.ns_plink
        ns_xsd = soaplib.ns_xsd
        ns_wsa = soaplib.ns_wsa

        # otherwise build it
        # TODO: we may want to customize service_name.
        service_name = self.__class__.__name__.split('.')[-1]

        _ns_tns = self.get_tns()
        _pref_tns = soaplib.get_namespace_prefix(_ns_tns)

        # get the methods
        methods = self.methods()
        has_callbacks = self._has_callbacks()

        types = etree.Element("{%s}types" % ns_wsdl)
        self.add_schema(types, methods, for_validation=False)

        root = etree.Element("{%s}definitions" % ns_wsdl, nsmap=soaplib.nsmap)
        root.append(types)

        root.set('targetNamespace', _ns_tns)
        root.set('name', service_name)

        self.__add_messages_for_methods(root, methods)

        # add necessary async headers
        # WS-Addressing -> RelatesTo ReplyTo MessageID
        # callback porttype
        if has_callbacks:
            wsa_schema = etree.SubElement(types, "{%s}schema" % ns_xsd)
            wsa_schema.set("targetNamespace", '%sCallback'  % _ns_tns)
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
            cb_wsdl_port.set('binding', '%s:%s' % (_pref_tns, cb_service_name))

            cb_address = etree.SubElement(cb_wsdl_port, '{%s}address'
                                                              % ns_soap)
            cb_address.set('location', url)

        port_type = etree.SubElement(root, '{%s}portType' % ns_wsdl)
        port_type.set('name', service_name)
        for method in methods:
            if method.is_callback:
                operation = etree.SubElement(cb_port_type, '{%s}operation'
                                                            % ns_wsdl)
            else:
                operation = etree.SubElement(port_type,'{%s}operation' % ns_wsdl)

            operation.set('name', method.name)

            if method.doc is not None:
                documentation = etree.SubElement(operation, '{%s}documentation'
                                                                % ns_wsdl)
                documentation.text = method.doc

            operation.set('parameterOrder', method.in_message.get_type_name())

            op_input = etree.SubElement(operation, '{%s}input' % ns_wsdl)
            op_input.set('name', method.in_message.get_type_name())
            op_input.set('message', '%s:%s' % (_pref_tns,
                                             method.in_message.get_type_name()))

            if (not method.is_callback) and (not method.is_async):
                op_output = etree.SubElement(operation, '{%s}output' %  ns_wsdl)
                op_output.set('name', method.out_message.get_type_name())
                op_output.set('message', '%s:%s' % (_pref_tns,
                                            method.out_message.get_type_name()))

        # make partner link
        plink = etree.SubElement(root, '{%s}partnerLinkType' % ns_plink)
        plink.set('name', service_name)

        role = etree.SubElement(plink, '{%s}role' % ns_plink)
        role.set('name', service_name)

        plink_port_type = etree.SubElement(role, '{%s}portType' % ns_plink)
        plink_port_type.set('name', '%s:%s' % (_pref_tns,service_name))

        if has_callbacks: # adds the same elements twice. is that intended?
            role = etree.SubElement(plink, '{%s}role' % ns_plink)
            role.set('name', '%sCallback' % service_name)

            plink_port_type = etree.SubElement(role, '{%s}portType' % ns_plink)
            plink_port_type.set('name', '%s:%sCallback' %
                                                       (_pref_tns,service_name))

        self.__add_bindings_for_methods(root, service_name, methods)

        service = etree.SubElement(root, '{%s}service' % ns_wsdl)
        service.set('name', service_name)

        wsdl_port = etree.SubElement(service, '{%s}port' % ns_wsdl)
        wsdl_port.set('name', service_name)
        wsdl_port.set('binding', '%s:%s' % (_pref_tns, service_name))

        addr = etree.SubElement(wsdl_port, '{%s}address' % ns_soap)
        addr.set('location', url)

        wsdl = etree.tostring(root, xml_declaration=True, encoding="UTF-8")

        #cache the wsdl for next time
        return wsdl

    def add_schema(self, types, methods, for_validation):
        '''
        A private method for adding the appropriate entries
        to the schema for the types in the specified methods.

        @param the schema node to add the schema elements to
        @param the list of methods.
        '''

        schema_nodes = {}
        schema_entries = _SchemaEntries(self.get_tns())
        _pref_tns = soaplib.get_namespace_prefix(self.get_tns())

        for method in methods:
            method.in_message.add_to_schema(schema_entries)
            method.out_message.add_to_schema(schema_entries)

        for pref in schema_entries.namespaces:
            if not (pref in schema_nodes):
                if for_validation:
                    schema = etree.Element("{%s}schema" % soaplib.ns_xsd,
                                                            nsmap=soaplib.nsmap)
                else:
                    schema = etree.SubElement(types, "{%s}schema" % soaplib.ns_xsd)

                schema.set("targetNamespace", soaplib.nsmap[pref])
                schema.set("elementFormDefault", "qualified")

                schema_nodes[pref] = schema

            else:
                schema = schema_nodes[pref]

            for namespace in schema_entries.imports[pref]:
                import_ = etree.SubElement(schema, "{%s}import" % soaplib.ns_xsd)
                import_.set("namespace", namespace)
                if for_validation:
                    import_.set('schemaLocation', "%s.xsd" %
                                        soaplib.get_namespace_prefix(namespace))

            for node in schema_entries.namespaces[pref].elements.values():
                schema.append(node)

            for node in schema_entries.namespaces[pref].types.values():
                schema.append(node)

        return schema_nodes

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
            in_message = etree.SubElement(root, '{%s}message' % soaplib.ns_wsdl)
            in_message.set('name', method.in_message.get_type_name())

            in_part = etree.SubElement(in_message, '{%s}part' % soaplib.ns_wsdl)
            in_part.set('name', method.in_message.get_type_name())
            in_part.set('element', method.in_message.get_type_name())

            out_message = etree.SubElement(root, '{%s}message' % soaplib.ns_wsdl)
            out_message.set('name', method.out_message.get_type_name())

            out_part = etree.SubElement(out_message, '{%s}part' % soaplib.ns_wsdl)
            out_part.set('name', method.out_message.get_type_name())
            out_part.set('element', '%s:%s' % (_pref_tns,
                                            method.out_message.get_type_name()))

    def __add_bindings_for_methods(self, root, service_name, methods):
        '''
        A private method for adding bindings to the wsdl

        @param the root element of the wsdl
        @param the name of this service
        @param the methods to be add to the binding node
        '''

        ns_wsdl = soaplib.ns_wsdl
        ns_soap = soaplib.ns_soap

        has_callbacks = self._has_callbacks()
        _pref_tns = soaplib.get_namespace_prefix(self.get_tns())

        # make binding
        binding = etree.SubElement(root, '{%s}binding' % ns_wsdl)
        binding.set('name', service_name)
        binding.set('type', '%s:%s'% (_pref_tns, service_name))

        soap_binding = etree.SubElement(binding, '{%s}binding' % ns_soap)
        soap_binding.set('style', 'document')
        soap_binding.set('transport', 'http://schemas.xmlsoap.org/soap/http')

        if has_callbacks:
            cb_binding = etree.SubElement(root, '{%s}binding' % ns_wsdl)
            cb_binding.set('name', '%sCallback' % service_name)
            cb_binding.set('type', 'typens:%sCallback' % service_name)

            soap_binding = etree.SubElement(cb_binding, '{%s}binding' % ns_soap)
            soap_binding.set('transport', 'http://schemas.xmlsoap.org/soap/http')

        for method in methods:
            operation = etree.Element('{%s}operation' % ns_wsdl)
            operation.set('name', method.name)

            soap_operation = etree.SubElement(operation, '{%s}operation' %
                                                                       ns_soap)
            soap_operation.set('soapAction', method.public_name)
            soap_operation.set('style', 'document')

            input = etree.SubElement(operation, '{%s}input' % ns_wsdl)
            input.set('name', method.in_message.get_type_name())

            soap_body = etree.SubElement(input, '{%s}body' % ns_soap)
            soap_body.set('use', 'literal')

            if (not method.is_async) and (not method.is_callback):
                output = etree.SubElement(operation, '{%s}output' % ns_wsdl)
                output.set('name', method.out_message.get_type_name())

                soap_body = etree.SubElement(output, '{%s}body' % ns_soap)
                soap_body.set('use', 'literal')

            if method.is_callback:
                relates_to = etree.SubElement(input, '{%s}header' % ns_soap)

                relates_to.set('message', '%s:RelatesToHeader' % _pref_tns)
                relates_to.set('part', 'RelatesTo')
                relates_to.set('use', 'literal')

                cb_binding.append(operation)

            else:
                if method.is_async:
                    rt_header = etree.SubElement(input,'{%s}header' % ns_soap)
                    rt_header.set('message', '%s:ReplyToHeader' % _pref_tns)
                    rt_header.set('part', 'ReplyTo')
                    rt_header.set('use', 'literal')

                    mid_header = etree.SubElement(input, '{%s}header'% ns_soap)
                    mid_header.set('message', '%s:MessageIDHeader' % _pref_tns)
                    mid_header.set('part', 'MessageID')
                    mid_header.set('use', 'literal')

                binding.append(operation)

    def get_schema(self):
        pass

class ValidatingDefinition(Definition):
    def get_schema(self):
        methods = self.methods()

        schema_nodes = self.add_schema(None, methods, for_validation=True)

        tmp_dir_name = tempfile.mkdtemp()

        # serialize nodes to files
        for k,v in schema_nodes.items():
            f = open('%s/%s.xsd' % (tmp_dir_name, k), 'w')
            etree.ElementTree(v).write(f, pretty_print=True)
            f.close()

        pref_tns = soaplib.get_namespace_prefix(self.get_tns())
        f = open('%s/%s.xsd' % (tmp_dir_name, pref_tns), 'r')

        retval = etree.XMLSchema(etree.parse(f))

        f.close()
        shutil.rmtree(tmp_dir_name)

        return retval
