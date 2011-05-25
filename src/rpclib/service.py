
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
from rpclib.model.clazz import TypeInfo

class MethodDescriptor(object):
    '''This class represents the method signature of a soap method,
    and is returned by the rpc decorator.
    '''

    def __init__(self, name, public_name, in_message, out_message, doc,
                 is_callback=False, is_async=False, mtom=False, in_header=None,
                 out_header=None, faults=(),
                 port_type=None, no_ctx=False
                ):

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
        self.port_type = port_type
        self.no_ctx = no_ctx

def _produce_input_message(ns, f, params, kparams, no_ctx):
    if no_ctx is True:
        arg_start=0
    else:
        arg_start=1

    _in_message = kparams.get('_in_message', f.func_name)
    _in_variable_names = kparams.get('_in_variable_names', {})

    argcount = f.func_code.co_argcount
    param_names = f.func_code.co_varnames[arg_start:argcount]

    in_params = TypeInfo()

    try:
        for i in range(len(param_names)):
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

def _validate_body_style(kparams):
    _body_style = kparams.get('_body_style')
    _soap_body_style = kparams.get('_soap_body_style')

    if _body_style is None:
        _body_style = 'wrapped'
    elif not (_body_style in ('wrapped', 'bare')):
        raise ValueError("body_style must be one of ('wrapped', 'bare')")
    elif _soap_body_style == 'document':
        _body_style = 'bare'
    elif _soap_body_style == 'rpc':
        _body_style = 'wrapped'
    else:
        raise ValueError("soap_body_style must be one of ('rpc', 'document')")
    assert _body_style in ('wrapped','bare')

    return _body_style

def _produce_output_message(ns, f, params, kparams):
    """Generate an output message for "rpc"-style API methods.

    This message is a wrapper to the declared return type.
    """

    _returns = kparams.get('_returns')
    _body_style = _validate_body_style(kparams)

    _out_message = kparams.get('_out_message', '%sResponse' % f.func_name)
    out_params = TypeInfo()

    if _returns and _body_style == 'wrapped':
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

    if _body_style == 'wrapped':
        message = Message.produce(type_name=_out_message, namespace=ns,
                                                             members=out_params)
        message.__namespace__ = ns # FIXME: is this necessary?

    else:
        message = Message.alias(_out_message, ns, _returns)

    message.resolve_namespace(message, ns)

    return message

def srpc(*params, **kparams):
    kparams["_no_ctx"] = True
    return rpc(*params, **kparams)

def rpc(*params, **kparams):
    '''Method decorator to flag a method as a rpc-style operation.

    This is a method decorator to flag a method as a remote procedure call.  It
    will behave like a normal python method on a class, and will only behave
    differently when the keyword '_method_descriptor' is passed in, returning a
    'MethodDescriptor' object.  This decorator does none of the rpc
    serialization, only flags a method as a remotely callable procedure. This
    decorator should only be used on member methods of an instance of
    rpclib.service.DefinitionBase.
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
                _port_type = kparams.get('_soap_port_type', None)
                _no_ctx = kparams.get('_no_ctx', False)

                # the decorator function does not have a reference to the
                # class and needs to be passed in
                ns = kwargs['clazz'].get_tns()

                in_message = _produce_input_message(ns, f, params, kparams, _no_ctx)
                out_message = _produce_output_message(ns, f, params, kparams)
                _faults = kparams.get('_faults', [])

                if not (_in_header is None):
                    _in_header.resolve_namespace(_in_header, ns)
                if not (_out_header is None):
                    _out_header.resolve_namespace(_out_header, ns)

                doc = getattr(f, '__doc__')
                retval = MethodDescriptor(f.func_name, _public_name,
                        in_message, out_message, doc, _is_callback, _is_async,
                        _mtom, _in_header, _out_header, _faults,
                        port_type=_port_type, no_ctx=_no_ctx)

            return retval

        explain_method.__doc__ = f.__doc__
        explain_method._is_rpc = True
        explain_method.func_name = f.func_name

        return explain_method
    return explain

class DefinitionBaseMeta(type):
    def __init__(self, cls_name, cls_bases, cls_dict):
        super(DefinitionBaseMeta, self).__init__(cls_name, cls_bases, cls_dict)

        self.public_methods = []

        for func_name, func in cls_dict.iteritems():
            if callable(func) and hasattr(func, '_is_rpc'):
                descriptor = func(_method_descriptor=True, clazz=self)
                self.public_methods.append(descriptor)

                setattr(self, func_name, staticmethod(func))

class DefinitionBase(object):
    '''This class serves as the base for all service definitions.  Subclasses of
    this class will use the rpc decorator to flag methods to be exposed via soap.

    It is a natural abstract base class, because it's of no use without any
    method definitions, hence the 'Base' suffix in the name.
    '''
    __metaclass__ = DefinitionBaseMeta

    __tns__ = None
    __in_header__ = None
    __out_header__ = None
    __service_name__ = None
    __port_types__ = ()

    @classmethod
    def get_service_class_name(cls):
        return cls.__name__

    @classmethod
    def get_service_name(cls):
        return cls.__service_name__

    @classmethod
    def get_port_types(cls):
        return cls.__port_types__

    @classmethod
    def get_tns(cls):
        if not (cls.__tns__ is None):
            return cls.__tns__

        service_name = cls.get_service_class_name().split('.')[-1]

        retval = cls.__module__
        if cls.__module__ == '__main__':
            retval = '.'.join((service_name, service_name))

        return retval

    @classmethod
    def get_method(cls, name):
        '''Returns the method descriptor based on element name.'''

        for method in cls.public_methods:
            type_name = method.in_message.get_type_name()
            if '{%s}%s' % (cls.get_tns(), type_name) == name:
                return method

        for method in cls.public_methods:
            if method.public_name == name:
                return method

        raise Exception('Method "%s" not found' % name)

    @classmethod
    def _has_callbacks(cls):
        '''Determines if this object has callback methods or not.'''

        for method in cls.public_methods:
            if method.is_callback:
                return True

        return False

    @staticmethod
    def call_wrapper(ctx, call, params):
        '''Called in place of the original method call.

        @param the original method call
        @param the arguments to the call
        '''
        if ctx.descriptor.no_ctx:
            return call(*params)
        else:
            return call(ctx, *params)

    @staticmethod
    def on_method_call(ctx, py_params):
        '''Called BEFORE the service implementing the functionality is called

        @param the method name
        @param the tuple of python params being passed to the method
        '''

    @staticmethod
    def on_method_return_object(ctx, py_results):
        '''Called AFTER the service implementing the functionality is called,
        with native return object as argument

        @param the python results from the method
        '''

    @staticmethod
    def on_method_return_doc(ctx, doc_results):
        '''Called AFTER the service implementing the functionality is called,
        with native return object serialized to Element objects as argument.

        @param the xml element containing the return value(s) from the method
        '''

    @staticmethod
    def on_method_exception_object(ctx, exc):
        '''Called BEFORE the exception is serialized, when an error occurs
        during execution.

        @param the exception object
        '''

    @staticmethod
    def on_method_exception_doc(ctx, fault_doc):
        '''Called AFTER the exception is serialized, when an error occurs
        during execution.

        @param the xml element containing the exception object serialized to a
        fault
        '''
