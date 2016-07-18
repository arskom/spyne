
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

"""The ``spyne.decorator`` module contains the the @srpc decorator and its
helper methods. The @srpc decorator is responsible for tagging methods as remote
procedure calls extracting method's input and output types.

It's possible to create custom decorators that wrap the @srpc decorator in order
to have a more elegant way of passing frequently-used parameter values. The @rpc
decorator is a simple example of this.
"""

import spyne.const.xml_ns

from copy import copy
from inspect import isclass

from spyne import MethodDescriptor

# Empty means empty input, bare output. Doesn't say anything about response
# being empty
from spyne._base import BODY_STYLE_EMPTY
from spyne._base import BODY_STYLE_WRAPPED
from spyne._base import BODY_STYLE_BARE
from spyne._base import BODY_STYLE_OUT_BARE

from spyne.model import ModelBase, ComplexModel
from spyne.model.complex import TypeInfo

from spyne.const import add_request_suffix


def _produce_input_message(f, params, in_message_name,
                      in_variable_names, no_ctx, no_self, args, body_style_str):
    arg_start = 0
    if no_ctx is False:
        arg_start += 1
    if no_self is False:
        arg_start += 1

    if args is None:
        try:
            argcount = f.__code__.co_argcount
            args = f.__code__.co_varnames[arg_start:argcount]

        except AttributeError:
            raise TypeError(
                "It's not possible to instrospect builtins. You must pass a "
                "sequence of argument names as the '_args' argument to the "
                "rpc decorator to manually denote the arguments that this "
                "function accepts."
            )

        if len(params) != len(args):
            raise Exception("%r function has %d argument(s) but its decorator "
                            "has %d." % (f.__name__, len(args), len(params)))

    else:
        args = copy(args)
        if len(params) != len(args):
            raise Exception("%r function has %d argument(s) but the _args "
                            "argument has %d." % (
                            f.__name__, len(args), len(params)))

    in_params = TypeInfo()
    for k, v in zip(args, params):
        k = in_variable_names.get(k, k)
        in_params[k] = v

    ns = spyne.const.xml_ns.DEFAULT_NS
    if in_message_name.startswith("{"):
        ns, _, in_message_name = in_message_name[1:].partition("}")

    message = None
    if body_style_str == 'bare':
        if len(in_params) > 1:
            raise Exception("body_style='bare' can handle at most one function "
                            "argument.")

        if len(in_params) == 0:
            message = ComplexModel.produce(type_name=in_message_name,
                                           namespace=ns, members=in_params)
        else:
            message, = in_params.values()
            message = message.customize(sub_name=in_message_name, sub_ns=ns)

            from spyne.model import ComplexModelBase
            if issubclass(message, ComplexModelBase) and not message._type_info:
                raise Exception("body_style='bare' does not allow empty "
                                "model as param")

            # there can't be multiple arguments here.
            if message.__type_name__ is ModelBase.Empty:
                message._fill_empty_type_name(ns, in_message_name,
                                                    "%s_arg0" % in_message_name)

    else:
        message = ComplexModel.produce(type_name=in_message_name,
                                       namespace=ns, members=in_params)
        message.__namespace__ = ns

    return message


def _validate_body_style(kparams):
    _body_style = kparams.pop('_body_style', None)
    _soap_body_style = kparams.pop('_soap_body_style', None)

    allowed_body_styles = ('wrapped', 'bare', 'out_bare')
    if _body_style is None:
        _body_style = 'wrapped'
    elif not (_body_style in allowed_body_styles):
        raise ValueError("body_style must be one of %r" % allowed_body_styles)
    elif _soap_body_style == 'document':
        _body_style = 'wrapped'
    elif _soap_body_style == 'rpc':
        _body_style = 'bare'
    elif _soap_body_style is None:
        pass
    else:
        raise ValueError("soap_body_style must be one of ('rpc', 'document')")

    assert _body_style in ('wrapped', 'bare', 'out_bare')

    return _body_style


def _produce_output_message(func_name, body_style_str, kparams):
    """Generate an output message for "rpc"-style API methods.

    This message is a wrapper to the declared return type.
    """

    _returns = kparams.pop('_returns', None)

    _out_message_name = kparams.pop('_out_message_name', '%s%s' %
                                       (func_name, spyne.const.RESPONSE_SUFFIX))

    out_params = TypeInfo()

    if _returns and body_style_str == 'wrapped':
        if isinstance(_returns, (list, tuple)):
            default_names = ['%s%s%d'% (func_name, spyne.const.RESULT_SUFFIX, i)
                                                  for i in range(len(_returns))]

            _out_variable_names = kparams.pop('_out_variable_names',
                                                                  default_names)

            assert (len(_returns) == len(_out_variable_names))

            var_pair = zip(_out_variable_names, _returns)
            out_params = TypeInfo(var_pair)

        else:
            _out_variable_name = kparams.pop('_out_variable_name',
                                '%s%s' % (func_name, spyne.const.RESULT_SUFFIX))

            out_params[_out_variable_name] = _returns

    ns = spyne.const.xml_ns.DEFAULT_NS
    if _out_message_name.startswith("{"):
        ns = _out_message_name[1:].partition("}")[0]

    if body_style_str.endswith('bare') and _returns is not None:
        message = _returns.customize(sub_name=_out_message_name, sub_ns=ns)
        if message.__type_name__ is ModelBase.Empty:
            message.__type_name__ = _out_message_name

    else:
        message = ComplexModel.produce(type_name=_out_message_name,
                                               namespace=ns, members=out_params)

        message.Attributes._wrapper = True
        message.__namespace__ = ns  # FIXME: is this necessary?

    return message


def _substitute_self_reference(params, kparams, kwargs, _no_self):
    from spyne.model import SelfReference

    for i, v in enumerate(params):
        if isclass(v) and issubclass(v, SelfReference):
            if _no_self:
                raise ValueError("SelfReference can't be used in @rpc")
            else:
                params[i] = kwargs['_self_ref_replacement']
        else:
            params[i] = v

    for k, v in kparams.items():
        if isclass(v) and issubclass(v, SelfReference):
            if _no_self:
                raise ValueError("SelfReference can't be used in @rpc")
            else:
                kparams[k] = kwargs['_self_ref_replacement']
        else:
            kparams[k] = v


def rpc(*params, **kparams_original):
    """Method decorator to tag a method as a remote procedure call in a
    :class:`spyne.service.ServiceBase` subclass.

    You should use the :class:`spyne.server.null.NullServer` transport if you
    want to call the methods directly. You can also use the 'function' attribute
    of the returned object to call the function itself.

    ``_operation_name`` vs ``_in_message_name``:
    Soap clients(SoapUI, Savon, suds) will use the operation name as the
    function name. The name of the input message(_in_message_name) is irrelevant
    when interfacing in this manner; this is because the clients mostly wrap
    around it. However, the soap xml request only uses the input message when
    posting with the soap server; the other protocols only use the input message
    as well. ``_operation_name`` cannot be used with ``_in_message_name``.

    :param _returns: Denotes The return type of the function. It can be a
        type or a sequence of types for functions that have multiple return
        values.
    :param _in_header: A type or an iterable of types that that this method
        accepts as incoming header.
    :param _out_header: A type or an iterable of types that that this method
        sends as outgoing header.
    :param _operation_name: The function's soap operation name. The operation
        and SoapAction names will be equal to the value of ``_operation_name``.
        Default is the function name.
    :param _in_message_name: The public name of the function's input message.
        Default is: ``_operation_name + REQUEST_SUFFIX``.
    :param _out_message_name: The public name of the function's output message.
        Default is: ``_operation_name + RESPONSE_SUFFIX``.
    :param _in_variable_names: The public names of the function arguments. It's
        a dict that maps argument names in the code to public ones.
    :param _out_variable_name: The public name of the function response object.
        It's a string. Ignored when ``_body_style != 'wrapped'`` or ``_returns``
        is a sequence.
    :param _out_variable_names: The public name of the function response object.
        It's a sequence of strings. Ignored when ``_body_style != 'wrapped'`` or
        or ``_returns`` is not a sequence. Must be the same length as
        ``_returns``.
    :param _body_style: One of ``('bare', 'wrapped')``. Default: ``'wrapped'``.
        In wrapped mode, wraps response objects in an additional class.
    :param _soap_body_style: One of ('rpc', 'document'). Default ``'document'``.
        ``_soap_body_style='document'`` is an alias for
        ``_body_style='wrapped'``. ``_soap_body_style='rpc'`` is an alias for
        ``_body_style='bare'``.
    :param _port_type: Soap port type string.
    :param _no_ctx: Don't pass implicit ctx object to the user method.
    :param _no_self: This method does not get an implicit 'self' argument
        (before any other argument, including ctx).
    :param _udp: Short for UserDefinedProperties, you can use this to mark the
        method with arbitrary metadata.
    :param _aux: The auxiliary backend to run this method. ``None`` if primary.
    :param _throws: A sequence of exceptions that this function can throw. This
        has no real functionality besides publishing this information in
        interface documents.
    :param _args: the name of the arguments to expose.
    :param _service_class: A :class:`ServiceBase` subclass, if you feel like
        overriding it.
    """

    params = list(params)

    def explain(f):
        def explain_method(**kwargs):
            kparams = dict(kparams_original)
            function_name = kwargs['_default_function_name']

            # this block is passed straight to the descriptor
            _is_callback = kparams.pop('_is_callback', False)
            _is_async = kparams.pop('_is_async', False)
            _mtom = kparams.pop('_mtom', False)
            _in_header = kparams.pop('_in_header', None)
            _out_header = kparams.pop('_out_header', None)
            _port_type = kparams.pop('_soap_port_type', None)
            _no_ctx = kparams.pop('_no_ctx', False)
            _no_self = kparams.pop('_no_self', True)
            _udp = kparams.pop('_udp', None)
            _aux = kparams.pop('_aux', None)
            _pattern = kparams.pop("_pattern", None)
            _patterns = kparams.pop("_patterns", [])
            _args = kparams.pop("_args", None)
            _translations = kparams.pop("_translations", None)
            _when = kparams.pop("_when", None)
            _service_class = kparams.pop("_service_class", None)
            _href = kparams.pop("_href", None)

            _substitute_self_reference(params, kparams, kwargs, _no_self)

            _faults = None
            if ('_faults' in kparams) and ('_throws' in kparams):
                raise ValueError("only one of '_throws ' or '_faults' arguments"
                                 "must be given -- they're synonyms.")

            elif '_faults' in kparams:
                _faults = kparams.pop('_faults')

            elif '_throws' in kparams:
                _faults = kparams.pop('_throws')

            _in_message_name_override = not ('_in_message_name' in kparams)
            _in_message_name = kparams.pop('_in_message_name', function_name)

            _operation_name = kparams.pop('_operation_name', function_name)

            if _operation_name != function_name and \
                                              _in_message_name != function_name:
                raise ValueError(
                    "only one of '_operation_name' and '_in_message_name' "
                    "arguments should be given")

            if _in_message_name == function_name:
                _in_message_name = add_request_suffix(_operation_name)

            _in_variable_names = kparams.pop('_in_variable_names', {})

            body_style = BODY_STYLE_WRAPPED
            body_style_str = _validate_body_style(kparams)
            if body_style_str.endswith('bare'):
                if body_style_str == 'out_bare':
                    body_style = BODY_STYLE_OUT_BARE
                else:
                    body_style = BODY_STYLE_BARE

            in_message = _produce_input_message(f, params,
                                           _in_message_name, _in_variable_names,
                                       _no_ctx, _no_self, _args, body_style_str)

            _out_message_name_override = not ('_out_message_name' in kparams)
            out_message = _produce_output_message(function_name, body_style_str,
                                                                        kparams)

            doc = getattr(f, '__doc__')

            if _pattern is not None and _patterns != []:
                raise ValueError("only one of '_pattern' and '_patterns' "
                                 "arguments should be given")

            if _pattern is not None:
                _patterns = [_pattern]

            if body_style_str.endswith('bare'):
                from spyne.model import ComplexModelBase

                t = in_message
                if issubclass(t, ComplexModelBase) and len(t._type_info) == 0:
                    body_style = BODY_STYLE_EMPTY

            retval = MethodDescriptor(f,
                in_message, out_message, doc, _is_callback, _is_async,
                _mtom, _in_header, _out_header, _faults,
                port_type=_port_type, no_ctx=_no_ctx, udp=_udp,
                class_key=function_name, aux=_aux, patterns=_patterns,
                body_style=body_style, args=_args,
                operation_name=_operation_name, no_self=_no_self,
                translations=_translations, when=_when,
                in_message_name_override=_in_message_name_override,
                out_message_name_override=_out_message_name_override,
                service_class=_service_class, href=_href,
            )

            if _patterns is not None and _no_self:
                for p in _patterns:
                    p.hello(retval)

            if len(kparams) > 0:
                raise Exception("Unknown kwarg(s) %r passed.", kparams)
            return retval

        explain_method.__doc__ = f.__doc__
        explain_method._is_rpc = True

        return explain_method

    return explain


def srpc(*params, **kparams):
    """Method decorator to tag a method as a remote procedure call. See
    :func:`spyne.decorator.rpc` for detailed information.

    The initial "s" stands for "static". In Spyne terms, that means no implicit
    first argument is passed to the user callable, which really means the
    method is "stateless" rather than static. It's meant to be used for
    existing functions that can't be changed.
    """

    kparams["_no_ctx"] = True
    return rpc(*params, **kparams)


def mrpc(*params, **kparams):
    kparams["_no_self"] = False
    return rpc(*params, **kparams)
