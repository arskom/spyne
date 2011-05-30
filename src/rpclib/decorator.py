
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

from rpclib._base import MethodDescriptor
from rpclib.model.clazz import ClassSerializer as Message
from rpclib.model.clazz import TypeInfo
from rpclib.const.xml_ns import DEFAULT_NS

def _produce_input_message(f, params, kparams, no_ctx):
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

    message=Message.produce(type_name=_in_message, namespace=DEFAULT_NS,
                                            members=in_params)
    message.__namespace__ = DEFAULT_NS

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

def _produce_output_message(f, params, kparams):
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
        message = Message.produce(type_name=_out_message, namespace=DEFAULT_NS,
                                                             members=out_params)
        message.__namespace__ = DEFAULT_NS # FIXME: is this necessary?

    else:
        message = Message.alias(_out_message, DEFAULT_NS, _returns)

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

                in_message = _produce_input_message(f, params, kparams, _no_ctx)
                out_message = _produce_output_message(f, params, kparams)
                _faults = kparams.get('_faults', [])

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
