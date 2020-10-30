
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

import spyne.const.xml

from copy import copy
from inspect import isclass

from spyne import MethodDescriptor

# Empty means empty input, bare output. Doesn't say anything about response
# being empty
from spyne import LogicError
from spyne import BODY_STYLE_EMPTY
from spyne import BODY_STYLE_WRAPPED
from spyne import BODY_STYLE_BARE
from spyne import BODY_STYLE_OUT_BARE
from spyne import BODY_STYLE_EMPTY_OUT_BARE

from spyne.model import ModelBase, ComplexModel, ComplexModelBase
from spyne.model.complex import TypeInfo, recust_selfref, SelfReference

from spyne.const import add_request_suffix


def _produce_input_message(f, params, in_message_name, in_variable_names,
                       no_ctx, no_self, argnames, body_style_str, self_ref_cls,
                       in_wsdl_part_name):
    arg_start = 0
    if no_ctx is False:
        arg_start += 1
    if no_self is False:
        arg_start += 1

    if argnames is None:
        try:
            argcount = f.__code__.co_argcount
            argnames = f.__code__.co_varnames[arg_start:argcount]

        except AttributeError:
            raise TypeError(
                "It's not possible to instrospect builtins. You must pass a "
                "sequence of argument names as the '_args' argument to the "
                "rpc decorator to manually denote the arguments that this "
                "function accepts."
            )

        if no_self is False:
            params = [self_ref_cls.novalidate_freq()] + params
            argnames = ('self',) + argnames

        if len(params) != len(argnames):
            raise LogicError("%r function has %d argument(s) but its decorator "
                           "has %d." % (f.__name__, len(argnames), len(params)))

    else:
        argnames = copy(argnames)
        if len(params) != len(argnames):
            raise LogicError("%r function has %d argument(s) but the _args "
                            "argument has %d." % (
                                f.__name__, len(argnames), len(params)))

    in_params = TypeInfo()
    from spyne import SelfReference
    for k, v in zip(argnames, params):
        try:
            is_self_ref = issubclass(v, SelfReference)
        except TypeError:
            is_self_ref = False

        if is_self_ref:
            if no_self is False:
                raise LogicError("SelfReference can't be used in @rpc")
            v = recust_selfref(v, self_ref_cls)

        k = in_variable_names.get(k, k)
        in_params[k] = v

    ns = spyne.const.xml.DEFAULT_NS
    if in_message_name.startswith("{"):
        ns, _, in_message_name = in_message_name[1:].partition("}")

    message = None
    if body_style_str == 'bare':
        if len(in_params) > 1:
            # The soap Body elt contains 1 elt (called "body entry" in the soap
            # standard) per method call. If bare methods were allowed to have >1
            # argument, it would have to be serialized as multiple body entries,
            # which would violate the standard. It's easy to work around this
            # restriction by creating a ComplexModel that contains all the
            # required parameters.
            raise LogicError("body_style='bare' can handle at most one "
                                                           "function argument.")

        if len(in_params) == 0:
            message = ComplexModel.produce(type_name=in_message_name,
                                           namespace=ns, members=in_params)
        else:
            message, = in_params.values()
            message = message.customize(sub_name=in_message_name, sub_ns=ns)

            if issubclass(message, ComplexModelBase) and not message._type_info:
                raise LogicError("body_style='bare' does not allow empty "
                                                               "model as param")

            # there can't be multiple arguments here.
            if message.__type_name__ is ModelBase.Empty:
                message._fill_empty_type_name(ns, in_message_name,
                                                    "%s_arg0" % in_message_name)

    else:
        message = ComplexModel.produce(type_name=in_message_name,
                                       namespace=ns, members=in_params)
        message.__namespace__ = ns

    if in_wsdl_part_name:
        message = message.customize(wsdl_part_name=in_wsdl_part_name)

    return message


def _validate_body_style(kparams):
    _body_style = kparams.pop('_body_style', None)
    _soap_body_style = kparams.pop('_soap_body_style', None)

    allowed_body_styles = ('wrapped', 'bare', 'out_bare')
    if _body_style is None:
        _body_style = 'wrapped'

    elif not (_body_style in allowed_body_styles):
        raise ValueError("body_style must be one of %r" %
                                                         (allowed_body_styles,))

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


def _produce_output_message(func_name, body_style_str, self_ref_cls,
                                                              no_self, kparams):
    """Generate an output message for "rpc"-style API methods.

    This message is a wrapper to the declared return type.
    """

    _returns = kparams.pop('_returns', None)

    try:
        is_self_ref = issubclass(_returns, SelfReference)
    except TypeError:
        is_self_ref = False

    if is_self_ref:
        if no_self is False:
            raise LogicError("SelfReference can't be used in @rpc")

        _returns = recust_selfref(_returns, self_ref_cls)

    _is_out_message_name_overridden = not ('_out_message_name' in kparams)
    _out_message_name = kparams.pop('_out_message_name', '%s%s' %
                                       (func_name, spyne.const.RESPONSE_SUFFIX))

    if no_self is False and \
               (body_style_str == 'wrapped' or _is_out_message_name_overridden):
        _out_message_name = '%s.%s' % \
                               (self_ref_cls.get_type_name(), _out_message_name)

    _out_wsdl_part_name = kparams.pop('_wsdl_part_name', None)

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

    ns = spyne.const.xml.DEFAULT_NS
    if _out_message_name.startswith("{"):
        _out_message_name_parts = _out_message_name[1:].partition("}")
        ns = _out_message_name_parts[0]  # skip index 1, it is the closing '}'
        _out_message_name = _out_message_name_parts[2]

    if body_style_str.endswith('bare') and _returns is not None:
        message = _returns.customize(sub_name=_out_message_name, sub_ns=ns)
        if message.__type_name__ is ModelBase.Empty:
            message.__type_name__ = _out_message_name

    else:
        message = ComplexModel.produce(type_name=_out_message_name,
                                               namespace=ns, members=out_params)

        message.Attributes._wrapper = True
        message.__namespace__ = ns  # FIXME: is this necessary?

    if _out_wsdl_part_name:
        message = message.customize(wsdl_part_name=_out_wsdl_part_name)

    return message


def _substitute_self_reference(params, kparams, self_ref_replacement, _no_self):
    from spyne.model import SelfReference

    for i, v in enumerate(params):
        if isclass(v) and issubclass(v, SelfReference):
            if _no_self:
                raise LogicError("SelfReference can't be used in @rpc")
            params[i] = recust_selfref(v, self_ref_replacement)
        else:
            params[i] = v

    for k, v in kparams.items():
        if isclass(v) and issubclass(v, SelfReference):
            if _no_self:
                raise LogicError("SelfReference can't be used in @rpc")
            kparams[k] = recust_selfref(v, self_ref_replacement)
        else:
            kparams[k] = v


def _get_event_managers(kparams):
    _evmgr = kparams.pop("_evmgr", None)
    _evmgrs = kparams.pop("_evmgrs", None)

    if _evmgr is not None and _evmgrs is not None:
        raise LogicError("Pass one of _evmgr or _evmgrs but not both")

    if _evmgr is not None:
        _evmgrs = [_evmgr]

    _event_manager = kparams.pop("_event_manager", None)
    _event_managers = kparams.pop("_event_managers", None)

    if _event_manager is not None and _event_managers is not None:
        raise LogicError("Pass one of _event_manager or "
                         "_event_managers but not both")

    if _event_manager is not None:
        _event_managers = [_event_manager]

    if _evmgrs is not None and _event_managers is not None:
        raise LogicError("You must pass at most one of _evmgr* "
                         "arguments or _event_manager* arguments")
    elif _evmgrs is not None:
        _event_managers = _evmgrs

    return _event_managers if _event_managers is not None else []


def rpc(*params, **kparams):
    """Method decorator to tag a method as a remote procedure call in a
    :class:`spyne.service.Service` subclass.

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
    :param _in_arg_names: The public names of the function arguments. It's
        a dict that maps argument names in the code to public ones.
    :param _in_variable_names: **DEPRECATED** Same as _in_arg_names, kept for
        backwards compatibility.
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
    :param _udd: Short for User Defined Data, you can use this to mark the
        method with arbitrary metadata.
    :param _udp: **DEPRECATED** synonym of ``_udd``.
    :param _aux: The auxiliary backend to run this method. ``None`` if primary.
    :param _throws: A sequence of exceptions that this function can throw. This
        has no real functionality besides publishing this information in
        interface documents.
    :param _args: the name of the arguments to expose.
    :param _event_managers: An iterable of :class:`spyne.EventManager`
        instances. This is useful for adding additional event handlers to
        individual functions.
    :param _event_manager: An instance of :class:`spyne.EventManager` class.
    :param _logged: May be the string '...' to denote that the rpc arguments
        will not be logged.
    :param _evmgrs: Same as ``_event_managers``.
    :param _evmgr: Same as ``_event_manager``.
    :param _service_class: A :class:`Service` subclass. It's generally not a
        good idea to override it for ``@rpc`` methods. It could be necessary to
        override it for ``@mrpc`` methods to add events and other goodies.
    :param _service: Same as ``_service``.
    :param _wsdl_part_name: Overrides the part name attribute within wsdl
        input/output messages eg "parameters"
    """

    params = list(params)

    def explain(f):
        def explain_method(**kwargs):
            # params and kparams are passed by the user to the @rpc family
            # of decorators.

            # kwargs is passed by spyne while sanitizing methods. it mainly
            # contains information about the method context like the service
            # class that contains the method at hand.

            function_name = kwargs['_default_function_name']
            _service_class = kwargs.pop("_service_class", None)
            _self_ref_replacement = None

            # this block is passed straight to the descriptor
            _is_callback = kparams.pop('_is_callback', False)
            _is_async = kparams.pop('_is_async', False)
            _mtom = kparams.pop('_mtom', False)
            _in_header = kparams.pop('_in_header', None)
            _out_header = kparams.pop('_out_header', None)
            _port_type = kparams.pop('_port_type', None)
            _no_ctx = kparams.pop('_no_ctx', False)
            _aux = kparams.pop('_aux', None)
            _pattern = kparams.pop("_pattern", None)
            _patterns = kparams.pop("_patterns", [])
            _args = kparams.pop("_args", None)
            _translations = kparams.pop("_translations", None)
            _when = kparams.pop("_when", None)
            _static_when = kparams.pop("_static_when", None)
            _href = kparams.pop("_href", None)
            _logged = kparams.pop("_logged", True)
            _internal_key_suffix = kparams.pop('_internal_key_suffix', '')
            if '_service' in kparams and '_service_class' in kparams:
                raise LogicError("Please pass only one of '_service' and "
                                                             "'_service_class'")
            if '_service' in kparams:
                _service_class = kparams.pop("_service")
            if '_service_class' in kparams:
                _service_class = kparams.pop("_service_class")

            _no_self = kparams.pop('_no_self', True)
            _event_managers = _get_event_managers(kparams)

            # mrpc-specific
            _self_ref_replacement = kwargs.pop('_self_ref_replacement', None)
            _default_on_null = kparams.pop('_default_on_null', False)
            _substitute_self_reference(params, kparams, _self_ref_replacement,
                                                                       _no_self)

            _faults = None
            if ('_faults' in kparams) and ('_throws' in kparams):
                raise ValueError("only one of '_throws ' or '_faults' arguments"
                                 "must be given -- they're synonyms.")

            elif '_faults' in kparams:
                _faults = kparams.pop('_faults')

            elif '_throws' in kparams:
                _faults = kparams.pop('_throws')

            _is_in_message_name_overridden = not ('_in_message_name' in kparams)
            _in_message_name = kparams.pop('_in_message_name', function_name)

            if _no_self is False and _is_in_message_name_overridden:
                _in_message_name = '%s.%s' % \
                       (_self_ref_replacement.get_type_name(), _in_message_name)

            _operation_name = kparams.pop('_operation_name', function_name)

            if _operation_name != function_name and \
                                              _in_message_name != function_name:
                raise ValueError(
                    "only one of '_operation_name' and '_in_message_name' "
                    "arguments should be given")

            if _in_message_name == function_name:
                _in_message_name = add_request_suffix(_operation_name)

            if '_in_arg_names' in kparams and '_in_variable_names' in kparams:
                raise LogicError("Use either '_in_arg_names' or "
                                              "'_in_variable_names', not both.")
            elif '_in_arg_names' in kparams:
                _in_arg_names = kparams.pop('_in_arg_names')

            elif '_in_variable_names' in kparams:
                _in_arg_names = kparams.pop('_in_variable_names')

            else:
                _in_arg_names = {}

            if '_udd' in kparams and '_udp' in kparams:
                raise LogicError("Use either '_udd' or '_udp', not both.")
            elif '_udd' in kparams:
                _udd = kparams.pop('_udd')

            elif '_udp' in kparams:
                _udd = kparams.pop('_udp')

            else:
                _udd = {}

            _wsdl_part_name = kparams.get('_wsdl_part_name', None)

            body_style = BODY_STYLE_WRAPPED
            body_style_str = _validate_body_style(kparams)
            if body_style_str.endswith('bare'):
                if body_style_str == 'out_bare':
                    body_style = BODY_STYLE_OUT_BARE
                else:
                    body_style = BODY_STYLE_BARE

            in_message = _produce_input_message(f, params,
                    _in_message_name, _in_arg_names, _no_ctx, _no_self,
                                   _args, body_style_str, _self_ref_replacement,
                                   _wsdl_part_name)

            out_message = _produce_output_message(function_name,
                       body_style_str, _self_ref_replacement, _no_self, kparams)

            if _logged != True:
                in_message.Attributes.logged = _logged
                out_message.Attributes.logged = _logged

            doc = getattr(f, '__doc__')

            if _pattern is not None and _patterns != []:
                raise ValueError("only one of '_pattern' and '_patterns' "
                                 "arguments should be given")

            if _pattern is not None:
                _patterns = [_pattern]

            if body_style_str.endswith('bare'):
                from spyne.model import ComplexModelBase

                ti = in_message
                to = out_message
                if issubclass(ti, ComplexModelBase) and len(ti._type_info) == 0:
                    if not issubclass(to, ComplexModelBase) or \
                                                         len(to._type_info) > 0:
                        body_style = BODY_STYLE_EMPTY_OUT_BARE
                    else:
                        body_style = BODY_STYLE_EMPTY

            assert _in_header is None or isinstance(_in_header, tuple)
            retval = MethodDescriptor(f,
                in_message, out_message, doc,
                is_callback=_is_callback, is_async=_is_async, mtom=_mtom,
                in_header=_in_header, out_header=_out_header, faults=_faults,
                parent_class=_self_ref_replacement,
                port_type=_port_type, no_ctx=_no_ctx, udd=_udd,
                class_key=function_name, aux=_aux, patterns=_patterns,
                body_style=body_style, args=_args,
                operation_name=_operation_name, no_self=_no_self,
                translations=_translations,
                when=_when, static_when=_static_when,
                service_class=_service_class, href=_href,
                internal_key_suffix=_internal_key_suffix,
                default_on_null=_default_on_null,
                event_managers=_event_managers,
                logged=_logged,
            )

            if _patterns is not None and _no_self:
                for p in _patterns:
                    p.hello(retval)

            if len(kparams) > 0:
                raise ValueError("Unknown kwarg(s) %r passed.", kparams)
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
