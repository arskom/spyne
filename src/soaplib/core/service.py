
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


from lxml import etree

from soaplib.core import namespaces, styles
from soaplib.core import MethodDescriptor
from soaplib.core.model.clazz import ClassModel as Message
from soaplib.core.model.clazz import ClassModelMeta as MessageMeta
from soaplib.core.model.clazz import TypeInfo
from soaplib.core.model.primitive import Any

_pref_wsa = namespaces.const_prefmap[namespaces.ns_wsa]

def _produce_input_message(ns, f, params, kparams):
    _in_message = kparams.get('_in_message', f.func_name)
    _in_variable_names = kparams.get('_in_variable_names', {})

    arg_count = f.func_code.co_argcount
    param_names = f.func_code.co_varnames[1:arg_count]

    try:
        in_params = TypeInfo()

        for i in range(len(params)):
            e0 = _in_variable_names.get(param_names[i], param_names[i])
            e1 = params[i]

            in_params[e0] = e1

    except IndexError, e:
        raise Exception("%s has parameter numbers mismatching" % f.func_name)

    message=Message.produce(type_name=_in_message, namespace=ns,
                                            members=in_params)
    message.__namespace__ = ns
    message.resolve_namespace(message, ns)

    return message

def _produce_rpc_output_message(ns, f, params, kparams):
    _returns = kparams.get('_returns')

    _out_message = kparams.get('_out_message', '%sResponse' % f.func_name)

    out_params = TypeInfo()

    if _returns:
        if isinstance(_returns, (list, tuple)):
            default_names = ['%sResult%d' % (f.func_name, i) for i in
                                                           range(len(_returns))]

            _out_variable_names = kparams.get('_out_variable_names',
                                                                default_names)

            assert (len(_returns) == len(_out_variable_names))

            var_pair = zip(_out_variable_names,_returns)
            out_params = TypeInfo(var_pair)

        else:
            _out_variable_name = kparams.get('_out_variable_name',
                                                       '%sResult' % f.func_name)

            out_params[_out_variable_name] = _returns

    message=Message.produce(type_name=_out_message, namespace=ns,
                                                             members=out_params)
    message.__namespace__ = ns
    message.resolve_namespace(message, ns)

    return message


class Alias(Message):
    """New type_name, same type_info.
    """
    @classmethod
    def add_to_schema(cls, schema_dict):
        if not schema_dict.has_class(cls._target):
            cls._target.add_to_schema(schema_dict)
        element = etree.Element('{%s}element' % namespaces.ns_xsd)
        element.set('name',cls.get_type_name())
        element.set('type',cls._target.get_type_name_ns(schema_dict.app))

        schema_dict.add_element(cls, element)

def _makeAlias(type_name, namespace, target):
    """ Return an alias class for the given target class.

    This function is a variation on 'ClassModel.produce'.

    The alias will borrow the target's typeinfo.
    """
    cls_dict = {}

    cls_dict['__namespace__'] = namespace
    cls_dict['__type_name__'] = type_name
    cls_dict['_type_info'] = getattr(target, '_type_info', ())
    cls_dict['_target'] = target

    return MessageMeta(type_name, (Alias,), cls_dict)

def _produce_document_output_message(ns, f, params, kparams):
    """Generate an output message for "document"-style API methods.

    This message is just an alias for the declared return type.
    """
    _returns = kparams.get('_returns', Any)
    _out_message = kparams.get('_out_message', '%sResponse' % f.func_name)

    message = _makeAlias(_out_message, ns, _returns)
    message.resolve_namespace(message, ns)

    return message

def soap(*params, **kparams):
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
            retval = None

            if '_method_descriptor' not in kwargs :
                retval = f(*args, **kwargs)

            else:
                _is_callback = kparams.get('_is_callback', False)
                _public_name = kparams.get('_public_name', f.func_name)
                _is_async = kparams.get('_is_async', False)
                _mtom = kparams.get('_mtom', False)
                _in_header = kparams.get('_in_header', None)
                _out_header = kparams.get('_out_header', None)
                _port_type = kparams.get('_port_type', None)
                _style = kparams.get('_style', styles.RPC_STYLE)

                # the decorator function does not have a reference to the
                # class and needs to be passed in
                ns = kwargs['clazz'].get_tns()


                in_message = _produce_input_message(ns, f, params, kparams)

                if _style == styles.RPC_STYLE or _style is None:
                    out_message = _produce_rpc_output_message(
                            ns,
                            f,
                            params,
                            kparams
                    )

                elif _style == styles.DOC_STYLE:
                    out_message = _produce_document_output_message(ns, f, params, kparams)

                else:
                    raise ValueError(
                        """Invalid style: valid values are
                        soaplib.core.styles.RPC_STYLE or
                        soaplib.core.styles.DOC_STYLE
                        """
                    )




                _faults = kparams.get('_faults', [])

                if _in_header :
                    _in_header.resolve_namespace(_in_header, ns)
                if _out_header :
                    _out_header.resolve_namespace(_out_header, ns)

                doc = getattr(f, '__doc__')
                retval = MethodDescriptor(f.func_name,
                                          _public_name,
                                          in_message,
                                          out_message,
                                          doc,
                                          _is_callback,
                                          _is_async,
                                          _mtom,
                                          _in_header,
                                          _out_header,
                                          _faults,
                                          _style,
                                          _port_type,
                                         )
            return retval

        explain_method.__doc__ = f.__doc__
        explain_method._is_rpc = True
        explain_method.func_name = f.func_name

        return explain_method

    return explain


def rpc(*params, **kparams):
    """This is a method decorator to flag a method as a remote procedure call.
    It will behave like a normal python method on a class, and will only behave
    differently when the keyword '_method_descriptor' is passed in, returning a
    'MethodDescriptor' object.  This decorator does none of the soap/xml
    serialization, only flags a method as a soap method.  This decorator should
    only be used on member methods of an instance of ServiceBase.

    Moving forward, this method is being depricated in favor of @soap
    Presently it simply calls @soap after checking for the _style keyword
    argument.  If the _style argument is not supplied it defaults to
    soaplib.core.styles.RPC_STYLE
    """

    if not kparams.has_key("_style"):
        kparams["_style"] = styles.RPC_STYLE

    return soap(*params, **kparams)





def document(*params, **kparams):
    """Method decorator to flag a method as a document-style operation.

    It will behave like a normal python method on a class, and will only
    behave differently when the keyword '_method_descriptor' is passed in,
    returning a 'MethodDescriptor' object.

    This decorator does none of the soap/xml serialization, only flags a
    method as a soap method.  This decorator should only be used on member
    methods of an instance of a class derived from 'ServiceBase'.

    Moving forward, this method is being depricated in favor of @soap
    Presently it simply calls @soap after setting _style keyword
    argument to  soaplib.core.DOC_STYLE
    """

    kparams["_style"] = styles.DOC_STYLE

    return soap(*params, **kparams)



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
    __service_interface__ = None
    __port_types__ = ()

    def __init__(self, environ=None):
        self.in_header = None
        self.out_header = None

        cls = self.__class__
        if not (cls in _public_methods_cache):
            _public_methods_cache[cls] = self.build_public_methods()

        self.public_methods = _public_methods_cache[cls]
        self.service_interface = cls.__service_interface__
        self.port_types = cls.__port_types__
        self.environ = environ

    @classmethod
    def get_service_class_name(cls):
        return cls.__name__

    @classmethod
    def get_service_interface(cls):
        return cls.__service_interface__

    @classmethod
    def get_port_types(cls):
        return cls.__port_types__

    def on_method_call(self, method_name, py_params, soap_params):
        '''Called BEFORE the service implementing the functionality is called

        @param the method name
        @param the tuple of python params being passed to the method
        @param the soap elements for each argument
        '''

    def on_method_return_object(self, py_results):
        '''Called AFTER the service implementing the functionality is called,
        with native return object as argument

        @param the python results from the method
        '''

    def on_method_return_xml(self, soap_results):
        '''Called AFTER the service implementing the functionality is called,
        with native return object serialized to Element objects as argument.

        @param the xml element containing the return value(s) from the method
        '''

    def on_method_exception_object(self, exc):
        '''Called BEFORE the exception is serialized, when an error occurs
        during execution.

        @param the exception object
        '''

    def on_method_exception_xml(self, fault_xml):
        '''Called AFTER the exception is serialized, when an error occurs
        during execution.

        @param the xml element containing the exception object serialized to a
        soap fault
        '''

    def call_wrapper(self, call, params):
        '''Called in place of the original method call.

        @param the original method call
        @param the arguments to the call
        '''
        return call(*params)

    @classmethod
    def get_tns(cls):
        if cls.__tns__ :
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
        '''Returns the metod descriptor based on element name or soap action.'''

        for method in self.public_methods:
            type_name = method.in_message.get_type_name()
            if '{%s}%s' % (self.get_tns(), type_name) == name:
                return method

        for method in self.public_methods:
            if method.public_name == name:
                return method

        raise Exception('Method "%s" not found' % name)

    def _has_callbacks(self):
        '''Determines if this object has callback methods or not.'''

        for method in self.public_methods:
            if method.is_callback:
                return True

        return False

    def header_objects(self):
        return []

    def get_service_names(self):
        '''Returns the service name(s) for this service. If this
        object has callbacks, then a second service is declared in
        the wsdl for those callbacks.
        '''

        service_name = self.__class__.__name__.split('.')[-1]

        if self._hasCallbacks():
            return [service_name, '%sCallback' % service_name]

        return [service_name]

    def add_port_type(self, app, root, service_name, types, url, port_type):
        ns_wsdl = namespaces.ns_wsdl

        # FIXME: I don't think this call is working.
        cb_port_type = self.__add_callbacks(root, types, service_name, url)

        port_name = port_type.get('name')
        method_port_type = None

        for method in self.public_methods:

            if len(self.port_types) is 0 and method_port_type is None:
                method_port_type = port_name
            else:
                method_port_type = method.port_type

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

                for f in method.faults:
                    fault = etree.SubElement(operation, '{%s}fault' %  ns_wsdl)
                    fault.set('name', f.get_type_name())
                    fault.set('message', f.get_type_name())

    # FIXME: I don't think this is working.
    def __add_callbacks(self, root, types, service_name, url):
        ns_xsd = namespaces.ns_xsd
        ns_wsa = namespaces.ns_wsa
        ns_wsdl = namespaces.ns_wsdl
        ns_soap = namespaces.ns_soap

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
        '''
        A method for adding the appropriate entries
        to the schema for the types in the specified methods.

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

            for fault in method.faults:
                fault.add_to_schema(schema_entries)

            if method.in_header is None:
                method.in_header = self.__in_header__
            else:
                method.in_header.add_to_schema(schema_entries)

            if method.out_header is None:
                method.out_header = self.__out_header__
            else:
                method.out_header.add_to_schema(schema_entries)

    def __add_message_for_object(self, app, root, messages, obj):
        if obj != None and not (obj.get_type_name() in messages):
            messages.add(obj.get_type_name())

            message = etree.SubElement(root, '{%s}message' % namespaces.ns_wsdl)
            message.set('name', obj.get_type_name())

            part = etree.SubElement(message, '{%s}part' % namespaces.ns_wsdl)
            part.set('name', obj.get_type_name())
            part.set('element', obj.get_type_name_ns(app))

    def add_messages_for_methods(self, app, root, messages):
        '''
        A private method for adding message elements to the wsdl
        @param the the root element of the wsdl
        '''

        for method in self.public_methods:
            self.__add_message_for_object(app,root,messages,method.in_message)
            self.__add_message_for_object(app,root,messages,method.out_message)
            self.__add_message_for_object(app,root,messages,method.in_header)
            self.__add_message_for_object(app,root,messages,method.out_header)
            for fault in method.faults:
                self.__add_message_for_object(app,root,messages,fault)


    def check_method_port(self, method):

        if len(self.port_types) != 0 and method.port_type is None:
            raise ValueError(
                """
                A port must be declared in the RPC decorator if the service
                class declares a list of ports

                Method:    %r
                """ % method.name
            )

        if (not method.port_type is None) and len(self.port_types) == 0:
            raise ValueError(
                """
                The rpc decorator has decared a port while the service class
                has not.  Remove the port declaration from the rpc decorator
                or add a list of ports to the service class
                """
            )
        try:
            if (not method.port_type is None):
                index = self.port_types.index(method.port_type)
        except ValueError, e:
            raise ValueError(
                """
                The port specified in the rpc decorator does not match any of
                the ports defined by the service class
                """
            )



    def add_bindings_for_methods(self, app, root, service_name, types, url,
                                        binding, transport, cb_binding=None):
        '''
        A private method for adding bindings to the wsdl

        @param the root element of the wsdl
        @param the name of this service
        '''

        ns_wsdl = namespaces.ns_wsdl
        ns_soap = namespaces.ns_soap
        pref_tns = app.get_namespace_prefix(self.get_tns())

        if self._has_callbacks():
            if cb_binding is None:
                cb_binding = etree.SubElement(root, '{%s}binding' % ns_wsdl)
                cb_binding.set('name', '%sCallback' % service_name)
                cb_binding.set('type', 'typens:%sCallback' % service_name)

            soap_binding = etree.SubElement(cb_binding, '{%s}binding' % ns_soap)
            soap_binding.set('transport', transport)

        for method in self.public_methods:

            self.check_method_port(method)

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

            if in_header :
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
                    out_header = self.__in_header__

                if out_header:
                    soap_header = etree.SubElement(output, '{%s}header' %
                                                                        ns_soap)
                    soap_header.set('use', 'literal')
                    soap_header.set('message', out_header.get_type_name_ns(app))
                    soap_header.set('part', out_header.get_type_name())

                for f in method.faults:
                    fault = etree.SubElement(operation, '{%s}fault' % ns_wsdl)
                    fault.set('name', f.get_type_name())

                    soap_fault = etree.SubElement(fault, '{%s}fault' % ns_soap)
                    soap_fault.set('name', f.get_type_name())
                    soap_fault.set('use', 'literal')

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
