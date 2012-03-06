
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

"""This module contains the EXPERIMENTAL Html protocol implementation.
It seeks to eliminate the need for templates.
"""

import logging
logger = logging.getLogger(__name__)

from lxml import html
from lxml.html.builder import E

from rpclib.model import ModelBase
from rpclib.model.binary import ByteArray
from rpclib.model.binary import Attachment
from rpclib.model.complex import Array
from rpclib.model.complex import Iterable
from rpclib.model.complex import ComplexModelBase
from rpclib.model.enum import EnumBase
from rpclib.model.fault import Fault
from rpclib.model.primitive import AnyXml
from rpclib.model.primitive import AnyDict
from rpclib.protocol import ProtocolBase
from rpclib.util.cdict import cdict

def serialize_null(prot, cls, name):
    return [ E(prot.child_tag, **{prot.field_name_attr: name}) ]

def nillable_value(func):
    def wrapper(prot, cls, value, name):
        if value is None:
            if cls.Attributes.default is None:
                return serialize_null(prot, cls, name)
            else:
                return func(prot, cls, cls.Attributes.default, name)
        else:
            return func(prot, cls, value, name)

    return wrapper

def not_supported(prot, cls, *args, **kwargs):
    raise Exception("Serializing %r Not Supported!" % cls)

@nillable_value
def serialize_model_base(prot, cls, value, name='retval'):
    return [ E(prot.child_tag, cls.to_string(value), **{prot.field_name_attr: name}) ]

@nillable_value
def serialize_complex_model(prot, cls, value, name='retval'):
    yield '<%s %s="%s">' % (prot.root_tag, prot.field_name_attr, name)

    if name is None:
        name = cls.get_type_name()

    inst = cls.get_serialization_instance(value)

    for k, v in cls.get_flat_type_info(cls).items():
        for val in prot.serialize_class(v, getattr(inst, k, None), k):
            yield val

    yield '</%s>' % prot.root_tag


class HtmlMicroFormat(ProtocolBase):
    mime_type = 'text/html'

    def __init__(self, app=None, validator=None, root_tag='div',
            child_tag='div', field_name_attr='class'):
        """Protocol that returns the response object as a html microformat. See
        https://en.wikipedia.org/wiki/Microformats for more info.

        The simple flavour is like the XmlObject protocol, but returns data in
        <div> or <span> tags.

        :param app: A rpclib.application.Application instance.
        :param validator: The validator to use. Ignored.
        :param root_tag: The type of the root tag that encapsulates the return
            data.
        :param child_tag: The type of the tag that encapsulates the fields of
            the returned object.
        :param field_name_attr: The name of the attribute that will contain the
            field names of the complex object children.
        :param field_type_attr: The name of the attribute that will contain the
            type names of the complex object children.
        """

        ProtocolBase.__init__(self, app, validator)

        assert root_tag in ('div','span')
        assert child_tag in ('div','span')
        assert field_name_attr in ('class','id')

        self.__root_tag = root_tag
        self.__child_tag = child_tag
        self.__field_name_attr = field_name_attr

        self.__serialization_handlers = cdict({
            ModelBase: serialize_model_base,
            ByteArray: not_supported,
            Attachment: not_supported,
            ComplexModelBase: serialize_complex_model,
        })

    @property
    def root_tag(self):
        return self.__root_tag

    @property
    def child_tag(self):
        return self.__child_tag

    @property
    def field_name_attr(self):
        return self.__field_name_attr

    def serialize_class(self, cls, value, name):
        handler = self.__serialization_handlers[cls]
        return handler(self, cls, value, name)

    def serialize(self, ctx, message):
        """Uses ctx.out_object, ctx.out_header or ctx.out_error to set
        ctx.out_body_doc, ctx.out_header_doc and ctx.out_document.
        """

        assert message in (self.RESPONSE,)

        self.event_manager.fire_event('before_serialize', ctx)

        # instantiate the result message
        result_message_class = ctx.descriptor.out_message
        result_message = result_message_class()

        # assign raw result to its wrapper, result_message
        out_type_info = result_message_class._type_info

        for i in range(len(out_type_info)):
            attr_name = result_message_class._type_info.keys()[i]
            setattr(result_message, attr_name, ctx.out_object[i])

        ctx.out_header_doc = None
        ctx.out_body_doc = serialize_complex_model(self, result_message_class,
                         result_message, result_message_class.get_type_name())

        ctx.out_document = ctx.out_body_doc

        self.event_manager.fire_event('after_serialize', ctx)

    def __generate_out_string(self, ctx, charset):
        for d in ctx.out_document:
            if d is None:
                continue
            elif isinstance(d, str):
                yield d
            else:
                yield html.tostring(d, encoding=charset)

    def create_out_string(self, ctx, charset=None):
        """Sets an iterable of string fragments to ctx.out_string"""

        if charset is None:
            charset = 'UTF-8'

        ctx.out_string = self.__generate_out_string(ctx, charset)

    def decompose_incoming_envelope(self, ctx, message):
        raise NotImplementedError("This is currently an output-only protocol.")
