
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

"""This module contains the ProtocolBase abstract base class for all
protocol implementations.
"""

import logging
logger = logging.getLogger(__name__)

import rpclib.const.xml_ns
from copy import copy

_ns_xsi = rpclib.const.xml_ns.xsi
_ns_xsd = rpclib.const.xml_ns.xsd

from rpclib._base import EventManager

from rpclib.const.http import HTTP_400
from rpclib.const.http import HTTP_404
from rpclib.const.http import HTTP_405
from rpclib.const.http import HTTP_413
from rpclib.const.http import HTTP_500

from rpclib.error import Fault
from rpclib.error import ResourceNotFoundError
from rpclib.error import RequestTooLongError
from rpclib.error import RequestNotAllowed
from rpclib.error import ValidationError

from rpclib.model.binary import File
from rpclib.model.binary import ByteArray


class ProtocolBase(object):
    """This is the abstract base class for all protocol implementations. Child
    classes can implement only the required subset of the public methods.

    The ProtocolBase class supports the following events:
    
    * ``before_deserialize``:
      Called before the deserialization operation is attempted.

    * ``after_deserialize``:
      Called after the deserialization operation is finished.

    * ``before_serialize``:
      Called before after the serialization operation is attempted.

    * ``after_serialize``:
      Called after the serialization operation is finished.
    """

    allowed_http_verbs = None
    mime_type = 'application/octet-stream'

    SOFT_VALIDATION = type("soft", (object,), {})
    REQUEST = type("request", (object,), {})
    RESPONSE = type("response", (object,), {})

    def __init__(self, app=None, validator=None, mime_type=None):
        """The arguments the constructor takes are as follows:

        :param app: The application this protocol belongs to.
        :param validator: The type of validation this protocol should do on
            incoming data.
        :param mime_type: The mime_type this protocol should set for transports
            that support this. This is a quick way to override the mime_type by
            default instead of subclassing the releavant protocol implementation.
        """

        self.__app = None
        self.validator = None

        self.set_app(app)
        self.event_manager = EventManager(self)
        self.set_validator(validator)
        if mime_type is not None:
            self.mime_type = mime_type

    @property
    def app(self):
        """The :class:`rpclib.application.Application` instance this protocol
        belongs to.
        """

        return self.__app

    def set_app(self, value):
        assert self.__app is None, "One protocol instance should belong to one " \
                                   "application instance."
        self.__app = value

    def create_in_document(self, ctx, in_string_encoding=None):
        """Uses ``ctx.in_string`` to set ``ctx.in_document``."""

    def decompose_incoming_envelope(self, ctx):
        """Sets the ``ctx.method_request_string``, ``ctx.in_body_doc``,
        ``ctx.in_header_doc`` and ``ctx.service`` properties of the ctx object,
        if applicable.
        """

    def deserialize(self, ctx):
        """Takes a MethodContext instance and a string containing ONE document
        instance in the ``ctx.in_string`` attribute.

        Returns the corresponding native python object in the ctx.in_object
        attribute.
        """

    def serialize(self, ctx):
        """Takes a MethodContext instance and the object to be serialized in the
        ctx.out_object attribute.

        Returns the corresponding document structure in the ctx.out_document
        attribute.
        """

    def create_out_string(self, ctx, out_string_encoding=None):
        """Uses ctx.out_document to set ctx.out_string"""

    def validate_document(self, payload):
        """Method to be overriden to perform any sort of custom input
        validation on the parsed input document.
        """

    def set_method_descriptor(self, ctx):
        """DEPRECATED! Use :func:`generate_method_contexts` instead.

        Method to be overriden to perform any sort of custom matching between
        the method_request_string and the methods.
        """

        name = ctx.method_request_string
        if not name.startswith("{"):
            name = '{%s}%s' % (self.app.interface.get_tns(), name)

        ctx.service_class = self.app.interface.service_mapping.get(name, None)
        if ctx.service_class is None:
            raise ResourceNotFoundError('Method %r not bound to a service class.'
                                                                        % name)

        ctx.descriptor = ctx.app.interface.method_mapping.get(name, None)
        if ctx.descriptor is None:
            raise ResourceNotFoundError('Method %r not found.' % name)

    def generate_method_contexts(self, ctx):
        call_handles = self.get_call_handles(ctx)
        if len(call_handles) == 0:
            raise ResourceNotFoundError('Method %r not found.' % ctx.method_request_string)

        retval = []
        for sc, d in call_handles:
            c = copy(ctx)

            assert d != None

            c.descriptor = d
            c.service_class = sc

            retval.append(c)

        return retval

    def get_call_handles(self, ctx):
        """Method to be overriden to perform any sort of custom method mapping
        using any data in the method context. Returns a list of contexts.
        Can return multiple contexts if a method_request_string matches more
        than one function. (This is called the fanout mode.)
        """

        name = ctx.method_request_string
        if not name.startswith("{"):
            name = '{%s}%s' % (self.app.interface.get_tns(), name)

        call_handles = self.app.interface.service_method_map.get(name, [])

        return call_handles

    def fault_to_http_response_code(self, fault):
        if isinstance(fault, RequestTooLongError):
            return HTTP_413
        if isinstance(fault, ResourceNotFoundError):
            return HTTP_404
        if isinstance(fault, RequestNotAllowed):
            return HTTP_405
        if isinstance(fault, Fault) and (fault.faultcode.startswith('Client.')
                                                or fault.faultcode == 'Client'):
            return HTTP_400
        else:
            return HTTP_500

    def set_validator(self, validator):
        """You must override this function if your protocol supports validation.
        """

        assert validator is None

        self.validator = None

    def flat_dict_to_object(self, doc, inst_class):
        simple_type_info = inst_class.get_simple_type_info(inst_class)
        inst = inst_class.get_deserialization_instance()

        # this is for validating cls.Attributes.{min,max}_occurs
        frequencies = {}

        for k, v in doc.items():
            member = simple_type_info.get(k, None)
            if member is None:
                logger.debug("discarding field %r" % k)
                continue

            mo = member.type.Attributes.max_occurs
            value = getattr(inst, k, None)
            if value is None:
                value = []

            # extract native values from the list of strings that comes from the
            # http dict.
            for v2 in v:
                if (self.validator is self.SOFT_VALIDATION and not
                            member.type.validate_string(member.type, v2)):
                    raise ValidationError(v2)

                if member.type is File or member.type is ByteArray or \
                        getattr(member.type, '_is_clone_of', None) is File or \
                        getattr(member.type, '_is_clone_of', None) is ByteArray:
                    if isinstance(v2, str) or isinstance(v2, unicode):
                        native_v2 = member.type.from_string(v2)
                    else:
                        native_v2 = v2
                else:
                    native_v2 = member.type.from_string(v2)

                if (self.validator is self.SOFT_VALIDATION and not
                            member.type.validate_native(member.type, native_v2)):
                    raise ValidationError(v2)

                value.append(native_v2)

                # set frequencies of parents.
                if not (member.path[:-1] in frequencies):
                    for i in range(1,len(member.path)):
                        logger.debug("\tset freq %r = 1" % (member.path[:i],))
                        frequencies[member.path[:i]] = 1

                freq = frequencies.get(member.path, 0)
                freq += 1
                frequencies[member.path] = freq
                logger.debug("\tset freq %r = %d" % (member.path, freq))

            if mo == 1:
                value = value[0]

            # assign the native value to the relevant class in the nested object
            # structure.
            cinst = inst
            ctype_info = inst_class.get_flat_type_info(inst_class)
            pkey = member.path[0]
            for i in range(len(member.path) - 1):
                pkey = member.path[i]
                if not (ctype_info[pkey].Attributes.max_occurs in (0,1)):
                    raise Exception("HttpRpc deserializer does not support "
                                    "non-primitives with max_occurs > 1")

                ninst = getattr(cinst, pkey, None)
                if ninst is None:
                    ninst = ctype_info[pkey].get_deserialization_instance()
                    setattr(cinst, pkey, ninst)
                cinst = ninst

                ctype_info = ctype_info[pkey]._type_info

            if isinstance(cinst, list):
                cinst.extend(value)
                logger.debug("\tset array   %r(%r) = %r" %
                                                    (member.path, pkey, value))
            else:
                setattr(cinst, member.path[-1], value)
                logger.debug("\tset default %r(%r) = %r" %
                                                    (member.path, pkey, value))

        if self.validator is self.SOFT_VALIDATION:
            sti = simple_type_info.values()
            sti.sort(key=lambda x: (len(x.path), x.path))
            pfrag = None
            for s in sti:
                if len(s.path) > 1 and pfrag != s.path[:-1]:
                    pfrag = s.path[:-1]
                    ctype_info = inst_class.get_flat_type_info(inst_class)
                    for i in range(len(pfrag)):
                        f = pfrag[i]
                        ntype_info = ctype_info[f]

                        min_o = ctype_info[f].Attributes.min_occurs
                        max_o = ctype_info[f].Attributes.max_occurs
                        val = frequencies.get(pfrag[:i+1], 0)
                        if val < min_o:
                            raise Fault('Client.ValidationError',
                                '"%s" member must occur at least %d times'
                                              % ('_'.join(pfrag[:i+1]), min_o))

                        if val > max_o:
                            raise Fault('Client.ValidationError',
                                '"%s" member must occur at most %d times'
                                              % ('_'.join(pfrag[:i+1]), max_o))

                        ctype_info = ntype_info.get_flat_type_info(ntype_info)

                val = frequencies.get(s.path, 0)
                min_o = s.type.Attributes.min_occurs
                max_o = s.type.Attributes.max_occurs
                if val < min_o:
                    raise Fault('Client.ValidationError',
                                '"%s" member must occur at least %d times'
                                                    % ('_'.join(s.path), min_o))
                if val > max_o:
                    raise Fault('Client.ValidationError',
                                '"%s" member must occur at most %d times'
                                                    % ('_'.join(s.path), max_o))

        return inst


    def object_to_flat_dict(self, inst_cls, value, hier_delim="_", retval=None,
                                                    prefix=None, parent=None):
        if retval is None:
            retval = {}
        if prefix is None:
            prefix = []

        fti = inst_cls.get_flat_type_info(inst_cls)
        for k, v in fti.items():
            new_prefix = list(prefix)
            new_prefix.append(k)
            subvalue = getattr(value, k, None)
            if getattr(v, 'get_flat_type_info', None) is None: # Not a ComplexModel
                key = hier_delim.join(new_prefix)

                if retval.get(key, None) is not None:
                    raise ValueError("%r.%s conflicts with previous value %r" %
                                                        (inst_cls, k, retval[key]))

                try:
                    retval[key] = subvalue
                except:
                    retval[key] = None

            else:
                self.object_to_flat_dict(fti[k], subvalue, hier_delim,
                                             retval, new_prefix, parent=inst_cls)

        return retval