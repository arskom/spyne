
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
from soaplib.serializers.clazz import TypeInfo
from soaplib.util.odict import odict

import logging
logger = logging.getLogger(__name__)

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
                    message.resolve_namespace(message, ns)
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
                    message.resolve_namespace(message, ns)
                    return message

                _is_callback = kparams.get('_is_callback', False)
                _public_name = kparams.get('_public_name', f.func_name)
                _is_async = kparams.get('_is_async', False)
                _mtom = kparams.get('_mtom', False)
                _in_header = kparams.get('_in_header', None)
                _out_header = kparams.get('_out_header', None)

                # the decorator function does not have a reference to the
                # class and needs to be passed in
                ns = kwargs['clazz'].get_tns()

                in_message = get_input_message(ns)
                out_message = get_output_message(ns)

                if not (_in_header is None):
                    _in_header.resolve_namespace(_in_header, ns)
                if not (_out_header is None):
                    _out_header.resolve_namespace(_out_header, ns)

                doc = getattr(f, '__doc__')
                descriptor = MethodDescriptor(f.func_name, _public_name,
                        in_message, out_message, doc, _is_callback, _is_async,
                        _mtom, _in_header, _out_header)

                return descriptor

            return f(*args, **kwargs)

        explain_method.__doc__ = f.__doc__
        explain_method._is_rpc = True
        explain_method.func_name = f.func_name

        return explain_method

    return explain

class _SchemaInfo(object):
    def __init__(self):
        self.elements = odict()
        self.types = odict()

class _SchemaEntries(object):
    def __init__(self, tns):
        self.namespaces = odict()
        self.imports = {}
        self.tns = tns

    def has_class(self, cls):
        retval = False
        ns_prefix = cls.get_namespace_prefix()

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
        pref_tns = cls.get_namespace_prefix()

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
                        self.imports[pref_tns].add(soaplib.nsmap[pref])
            else:
                seq = c

            if seq.tag == '{%s}sequence' % soaplib.ns_xsd:
                for e in seq:
                    pref = e.attrib['type'].split(':')[0]
                    if is_valid_import(pref):
                        self.imports[pref_tns].add(soaplib.nsmap[pref])

            elif seq.tag == '{%s}restriction' % soaplib.ns_xsd:
                pref = seq.attrib['base'].split(':')[0]
                if is_valid_import(pref):
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


_public_methods_cache = {}

class DefinitionBase(object):
    '''
    This class serves as the base for all soap services.  Subclasses of this
    class will use the rpc decorator to flag methods to be exposed via soap.
    This class is responsible for generating the wsdl for this service
    definition.

    It is a natural abstract base class, because it's of no use without any
    method definitions, hence the 'Base' suffix in the name.
    '''

    __tns__ = None
    __in_header__ = None
    __out_header__ = None

    def __init__(self, environ=None):
        self.soap_in_header = None
        self.soap_out_header = None

        cls = self.__class__
        if not (cls in _public_methods_cache):
            _public_methods_cache[cls] = self.build_public_methods()

        self.public_methods = _public_methods_cache[cls]

    def on_method_call(self, environ, method_name, py_params, soap_params):
        '''
        Called BEFORE the service implementing the functionality is called
        @param the wsgi environment
        @param the method name
        @param the body element of the soap request
        @param the tuple of python params being passed to the method
        @param the soap elements for each params
        '''
        pass

    def on_method_return(self, environ, py_results, soap_results,
                                                             http_resp_headers):
        '''
        Called AFTER the service implementing the functionality is called
        @param the wsgi environment
        @param the python results from the method
        @param the xml element containing the return value(s) from the method
        @param http response headers as a dict of strings
        '''
        pass

    def on_method_exception_object(self, environ, exc):
        '''
        Called BEFORE the exception is serialized, when an error occurs durring
        execution
        @param the wsgi environment
        @param the exception object
        '''
        pass

    def on_method_exception_xml(self, environ, fault_xml):
        '''
        Called AFTER the exception is serialized, when an error occurs durring
        execution
        @param the wsgi environment
        @param the xml element containing the exception object serialized to a
        soap fault
        '''
        pass

    def call_wrapper(self, call, params):
        '''
        Called in place of the original method call.
        @param the original method call
        @param the arguments to the call
        '''
        return call(*params)

    @classmethod
    def get_tns(cls):
        if not (cls.__tns__ is None):
            return cls.__tns__

        service_name = cls.__name__.split('.')[-1]

        retval = '.'.join((cls.__module__, service_name))
        if cls.__module__ == '__main__':
            retval = '.'.join((service_name, service_name))

        return retval

    def build_public_methods(self):
        '''Returns a list of method descriptors for this object'''

        logger.debug('building public methods')
        public_methods = []

        for func_name in dir(self):
            if func_name == 'public_methods':
                continue
            func = getattr(self, func_name)
            if callable(func) and hasattr(func, '_is_rpc'):
                descriptor = func(_method_descriptor=True, clazz=self.__class__)
                public_methods.append(descriptor)

        return public_methods

    def get_method(self, name):
        '''
        Returns the metod descriptor based on element name or soap action
        '''

        for method in self.public_methods:
            type_name = method.in_message.get_type_name()
            if '{%s}%s' % (self.get_tns(), type_name) == name:
                return method

        for method in self.public_methods:
            if method.public_name == name:
                return method

        raise Exception('Method "%s" not found' % name)

    def _has_callbacks(self):
        '''Determines if this object has callback methods or not'''

        for method in self.public_methods:
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

    def add_port_type(self, root, service_name, types, url, port_type):
        ns_wsdl = soaplib.ns_wsdl

        # FIXME: I don't think this call is working.
        cb_port_type = self.__add_callbacks(root, types, service_name, url)

        for method in self.public_methods:
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
            op_input.set('message', method.in_message.get_type_name_ns())

            if (not method.is_callback) and (not method.is_async):
                op_output = etree.SubElement(operation, '{%s}output' %  ns_wsdl)
                op_output.set('name', method.out_message.get_type_name())
                op_output.set('message', method.out_message.get_type_name_ns())

    # FIXME: I don't think this is working.
    def __add_callbacks(self, root, types, service_name, url):
        ns_xsd = soaplib.ns_xsd
        ns_wsa = soaplib.ns_wsa
        ns_wsdl = soaplib.ns_wsdl
        ns_soap = soaplib.ns_soap

        ns_tns = self.get_tns()
        pref_tns = soaplib.get_namespace_prefix(ns_tns)

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
        '''
        A private method for adding the appropriate entries
        to the schema for the types in the specified methods.

        @param the schema node to add the schema elements to. if it is None,
               the schema nodes are returned inside a dictionary
        @param the schema node dictinary, where keys are prefixes of the schema
               stored schema node
        '''

        if schema_entries is None:
            schema_entries = _SchemaEntries(self.get_tns())

        if self.__in_header__ != None:
            self.__in_header__.resolve_namespace(self.__in_header__, self.get_tns())
            self.__in_header__.add_to_schema(schema_entries)

        if self.__out_header__ != None:
            self.__out_header__.resolve_namespace(self.__out_header__, self.get_tns())
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

        return schema_entries

    def __add_message_for_object(self, root, messages, obj):
        if obj != None and not (obj.get_type_name() in messages):
            messages.add(obj.get_type_name())

            message = etree.SubElement(root, '{%s}message' % soaplib.ns_wsdl)
            message.set('name', obj.get_type_name())

            part = etree.SubElement(message, '{%s}part' % soaplib.ns_wsdl)
            part.set('name', obj.get_type_name())
            part.set('element', obj.get_type_name_ns())

    def add_messages_for_methods(self, root, messages):
        '''
        A private method for adding message elements to the wsdl
        @param the the root element of the wsdl
        '''

        for method in self.public_methods:
            self.__add_message_for_object(root, messages, method.in_message)
            self.__add_message_for_object(root, messages, method.out_message)
            self.__add_message_for_object(root, messages, method.in_header)
            self.__add_message_for_object(root, messages, method.out_header)


    def add_bindings_for_methods(self, root, service_name, types, url, binding, cb_binding=None):
        '''
        A private method for adding bindings to the wsdl

        @param the root element of the wsdl
        @param the name of this service
        '''

        ns_wsdl = soaplib.ns_wsdl
        ns_soap = soaplib.ns_soap
        pref_tns = soaplib.get_namespace_prefix(self.get_tns())

        if self._has_callbacks():
            if cb_binding is None:
                cb_binding = etree.SubElement(root, '{%s}binding' % ns_wsdl)
                cb_binding.set('name', '%sCallback' % service_name)
                cb_binding.set('type', 'typens:%sCallback' % service_name)

            soap_binding = etree.SubElement(cb_binding, '{%s}binding' % ns_soap)
            soap_binding.set('transport', 'http://schemas.xmlsoap.org/soap/http')

        for method in self.public_methods:
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
                in_header = self.__in_header__

            if not (in_header is None):
                soap_header = etree.SubElement(input, '{%s}header' % ns_soap)
                soap_header.set('use', 'literal')
                soap_header.set('message', in_header.get_type_name_ns())
                soap_header.set('part', in_header.get_type_name())

            if not (method.is_async or method.is_callback):
                output = etree.SubElement(operation, '{%s}output' % ns_wsdl)
                output.set('name', method.out_message.get_type_name())

                soap_body = etree.SubElement(output, '{%s}body' % ns_soap)
                soap_body.set('use', 'literal')

                # get input soap header
                out_header = method.in_header
                if out_header is None:
                    out_header = self.__in_header__

                if not (out_header is None):
                    soap_header = etree.SubElement(output, '{%s}header' % ns_soap)
                    soap_header.set('use', 'literal')
                    soap_header.set('message', out_header.get_type_name_ns())
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
