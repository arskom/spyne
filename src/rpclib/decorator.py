
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

"""This module contains the the @srpc decorator and its helper methods. The
@srpc decorator is responsible for tagging methods as remote procedure calls,
and also for dynamically defining complex objects that carry the method's input
parameters and output value(s).

It's possible to create custom decorators that wrap the @srpc decorator in order
to have a more elegant way of passing frequently-used parameter values. The @rpc
decorator is a simple example of this.
"""

from rpclib._base import MethodDescriptor
from rpclib.model.complex import ComplexModel
from rpclib.model.complex import TypeInfo
from rpclib.const.xml_ns import DEFAULT_NS

def _produce_input_message(f, params, _in_message_name, _in_variable_names, no_ctx):
    if no_ctx is True:
        arg_start=0
    else:
        arg_start=1

    argcount = f.func_code.co_argcount
    param_names = f.func_code.co_varnames[arg_start:argcount]

    in_params = TypeInfo()

    try:
        for i in range(len(param_names)):
            e0 = _in_variable_names.get(param_names[i], param_names[i])
            e1 = params[i]

            in_params[e0] = e1

    except IndexError, e:
        raise Exception("The parameter numbers of the %r function and its "
                        "decorator mismatch." % f.func_name)

    ns = DEFAULT_NS
    if _in_message_name.startswith("{"):
        ns = _in_message_name[1:].partition("}")[0]

    message=ComplexModel.produce(type_name=_in_message_name, namespace=ns,
                                            members=in_params)
    message.__namespace__ = ns

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

    assert _body_style in ('wrapped', 'bare')

    return _body_style

def _produce_output_message(f, func_name, kparams):
    """Generate an output message for "rpc"-style API methods.

    This message is a wrapper to the declared return type.
    """

    _returns = kparams.get('_returns')
    _body_style = _validate_body_style(kparams)

    _out_message_name = kparams.get('_out_message', '%sResponse' % func_name)
    out_params = TypeInfo()

    if _returns and _body_style == 'wrapped':
        if isinstance(_returns, (list, tuple)):
            default_names = ['%sResult%d' % (func_name, i) for i in
                                                           range(len(_returns))]

            _out_variable_names = kparams.get('_out_variable_names',
                                                                  default_names)

            assert (len(_returns) == len(_out_variable_names))

            var_pair = zip(_out_variable_names, _returns)
            out_params = TypeInfo(var_pair)

        else:
            _out_variable_name = kparams.get('_out_variable_name',
                                                       '%sResult' % func_name)

            out_params[_out_variable_name] = _returns

    ns = DEFAULT_NS
    if _out_message_name.startswith("{"):
        ns = _out_message_name[1:].partition("}")[0]

    if _body_style == 'wrapped':
        message = ComplexModel.produce(type_name=_out_message_name,
                                        namespace=ns,
                                        members=out_params)
        message.__namespace__ = ns # FIXME: is this necessary?

    else:
        message = ComplexModel.alias(_out_message_name, ns, _returns)

    return message

def rpc(*params, **kparams):
    kparams["_no_ctx"] = False
    return srpc(*params, **kparams)

def srpc(*params, **kparams):
    '''Method decorator to tag a method as a remote procedure call.

    The methods tagged with this decorator do not behave like a normal python
    method but return 'MethodDescriptor' object when called.

    You should use the :class:`rpclib.server.null.NullServer` transport if you
    want to call the methods directly. You can also use the 'function' attribute
    of the returned object to call the function itself.
    '''

    def explain(f):
        def explain_method(*args, **kwargs):
            retval = None
            function_name = kwargs['_default_function_name']

            _is_callback = kparams.get('_is_callback', False)
            _is_async = kparams.get('_is_async', False)
            _mtom = kparams.get('_mtom', False)
            _in_header = kparams.get('_in_header', None)
            _out_header = kparams.get('_out_header', None)
            _port_type = kparams.get('_soap_port_type', None)
            _no_ctx = kparams.get('_no_ctx', True)
            _udp = kparams.get('_udp', None)

            _faults = None
            if ('_faults' in kparams) and ('_throws' in kparams):
                raise ValueError("only one of '_throws ' and '_faults' arguments"
                                 "should be given, as they're synonyms.")
            elif '_faults' in kparams:
                _faults = kparams.get('_faults', None)
            elif '_throws' in kparams:
                _faults = kparams.get('_throws', None)

            _in_message_name = kparams.get('_in_message_name', function_name)
            _in_variable_names = kparams.get('_in_variable_names', {})
            in_message = _produce_input_message(f, params, _in_message_name,
                                                    _in_variable_names, _no_ctx)

            out_message = _produce_output_message(f, function_name, kparams)

            doc = getattr(f, '__doc__')

            retval = MethodDescriptor(f,
                    in_message, out_message, doc, _is_callback, _is_async,
                    _mtom, _in_header, _out_header, _faults,
                    port_type=_port_type, no_ctx=_no_ctx, udp=_udp,
                    class_key=function_name)

            return retval

        explain_method.__doc__ = f.__doc__
        explain_method._is_rpc = True

        return explain_method
    return explain
