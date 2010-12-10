
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

from rpclib.model.clazz import ClassSerializer as Message
from rpclib.model.clazz import ClassSerializerMeta as MessageMeta
from rpclib.model.clazz import TypeInfo
from rpclib.model.primitive import Any

class MethodDescriptor(object):
    '''This class represents the method signature of a soap method,
    and is returned by the rpc decorator.
    '''

    def __init__(self, name, public_name, in_message, out_message, doc,
                 is_callback=False, is_async=False, mtom=False, in_header=None,
                 out_header=None, faults=(), body_style='rpc'):

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
        self.faults = faults
        self.body_style = body_style

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

def rpc(*params, **kparams):
    '''This is a method decorator to flag a method as a remote procedure call.  It
    will behave like a normal python method on a class, and will only behave
    differently when the keyword '_method_descriptor' is passed in, returning a
    'MethodDescriptor' object.  This decorator does none of the rpc
    serialization, only flags a method as a remotely callable procedure.  This
    decorator should only be used on member methods of an instance of
    ServiceBase.
    '''

    def explain(f):
        def explain_method(*args, **kwargs):
            retval = None

            if not ('_method_descriptor' in kwargs):
                retval = f(*args, **kwargs)

            else:
                _is_callback = kparams.get('_is_callback', False)
                _public_name = kparams.get('_public_name', f.func_name)
                _is_async = kparams.get('_is_async', False)
                _mtom = kparams.get('_mtom', False)
                _in_header = kparams.get('_in_header', None)
                _out_header = kparams.get('_out_header', None)

                # the decorator function does not have a reference to the
                # class and needs to be passed in
                ns = kwargs['clazz'].get_tns()

                in_message = _produce_input_message(ns, f, params, kparams)
                out_message = _produce_rpc_output_message(ns, f, params, kparams)
                _faults = kparams.get('_faults', [])

                if not (_in_header is None):
                    _in_header.resolve_namespace(_in_header, ns)
                if not (_out_header is None):
                    _out_header.resolve_namespace(_out_header, ns)

                doc = getattr(f, '__doc__')
                retval = MethodDescriptor(f.func_name, _public_name,
                        in_message, out_message, doc, _is_callback, _is_async,
                        _mtom, _in_header, _out_header)

            return retval

        explain_method.__doc__ = f.__doc__
        explain_method._is_rpc = True
        explain_method.func_name = f.func_name

        return explain_method

    return explain

class Alias(Message):
    """New type_name, same type_info.
"""
    @classmethod
    def add_to_schema(cls, schema_dict):
        if not schema_dict.has_class(cls._target):
            cls._target.add_to_schema(schema_dict)
        element = etree.Element('{%s}element' % soaplib.ns_xsd)
        element.set('name',cls.get_type_name())
        element.set('type',cls._target.get_type_name_ns(schema_dict.app))

        schema_dict.add_element(cls, element)

def _makeAlias(type_name, namespace, target):
    """ Return an alias class for the given target class.

This function is a variation on 'ClassSerializer.produce'.

The alias will borrow the target's typeinfo.
"""
    cls_dict = {}

    cls_dict['__namespace__'] = namespace
    cls_dict['__type_name__'] = type_name
    cls_dict['_type_info'] = target._type_info
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

def document(*params, **kparams):
    """Method decorator to flag a method as a document-style operation.

It will behave like a normal python method on a class, and will only
behave differently when the keyword '_method_descriptor' is passed in,
returning a 'MethodDescriptor' object.
This decorator does none of the soap/xml serialization, only flags a
method as a soap method. This decorator should only be used on member
methods of an instance of a class derived from 'ServiceBase'.
"""

    def explain(f):
        def explain_method(*args, **kwargs):
            retval = None

            if not ('_method_descriptor' in kwargs):
                retval = f(*args, **kwargs)

            else:
                _is_callback = kparams.get('_is_callback', False)
                _public_name = kparams.get('_public_name', f.func_name)
                _is_async = kparams.get('_is_async', False)
                _mtom = kparams.get('_mtom', False)
                _in_header = kparams.get('_in_header', None)
                _out_header = kparams.get('_out_header', None)

                # the decorator function does not have a reference to the
                # class and needs to be passed in
                ns = kwargs['clazz'].get_tns()

                in_message = _produce_input_message(ns, f, params, kparams)
                out_message = _produce_document_output_message(ns, f,
                                                               params, kparams)
                _faults = kparams.get('_faults', [])

                if not (_in_header is None):
                    _in_header.resolve_namespace(_in_header, ns)
                if not (_out_header is None):
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
                                          'document',
                                         )
            return retval

        explain_method.__doc__ = f.__doc__
        explain_method._is_rpc = True
        explain_method.func_name = f.func_name

        return explain_method

    return explain

_public_methods_cache = {}

class DefinitionBase(object):
    '''This class serves as the base for all service definitions.  Subclasses of
    this class will use the rpc decorator to flag methods to be exposed via soap.
    This class is responsible for generating the wsdl for this service
    definition.

    It is a natural abstract base class, because it's of no use without any
    method definitions, hence the 'Base' suffix in the name.
    '''

    __tns__ = None
    __in_header__ = None
    __out_header__ = None

    def __init__(self, environ=None):
        self.in_header = None
        self.out_header = None

        cls = self.__class__
        if not (cls in _public_methods_cache):
            _public_methods_cache[cls] = self.build_public_methods()

        self.public_methods = _public_methods_cache[cls]

    def on_method_call(self, method_name, py_params, doc_params):
        '''Called BEFORE the service implementing the functionality is called

        @param the method name
        @param the tuple of python params being passed to the method
        @param the document structures of each argument
        '''

    def on_method_return_object(self, py_results):
        '''Called AFTER the service implementing the functionality is called,
        with native return object as argument

        @param the python results from the method
        '''

    def on_method_return_doc(self, doc_results):
        '''Called AFTER the service implementing the functionality is called,
        with native return object serialized to Element objects as argument.

        @param the xml element containing the return value(s) from the method
        '''

    def on_method_exception_object(self, exc):
        '''Called BEFORE the exception is serialized, when an error occurs
        during execution.

        @param the exception object
        '''

    def on_method_exception_doc(self, fault_doc):
        '''Called AFTER the exception is serialized, when an error occurs
        during execution.

        @param the xml element containing the exception object serialized to a
        fault
        '''

    def call_wrapper(self, call, params):
        '''Called in place of the original method call.

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
        '''Returns the metod descriptor based on element name.'''

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
        '''Returns the service name(s) for this service. If this object has
        callbacks, then a second service is declared in the wsdl for those
        callbacks.
        '''

        service_name = self.__class__.__name__.split('.')[-1]

        if self._hasCallbacks():
            return [service_name, '%sCallback' % service_name]

        return [service_name]
