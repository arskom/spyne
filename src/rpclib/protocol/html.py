
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
It seeks to eliminate the need for html templates.
"""

import logging
logger = logging.getLogger(__name__)

from itertools import chain

from lxml import html
from lxml.html.builder import E

from rpclib.model import ModelBase
from rpclib.model.binary import ByteArray
from rpclib.model.binary import Attachment
from rpclib.model.complex import ComplexModelBase
from rpclib.protocol import ProtocolBase
from rpclib.util.cdict import cdict

def serialize_null(prot, cls, name):
    return [ E(prot.child_tag, **{prot.field_name_attr: name}) ]

def nillable_value(func):
    def wrapper(prot, cls, value, name=None):
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

class HtmlBase(ProtocolBase):
    def __init__(self, app=None, validator=None, skip_depth=0):
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
        :param skip_depth: Number of wrapper classes to ignore. This is
        typically one of (0, 1, 2) but higher numbers may also work for your
        case.
        """

        ProtocolBase.__init__(self, app, validator, skip_depth=skip_depth)

    def serialize_class(self, cls, value, name):
        handler = self.serialization_handlers[cls]
        return handler(cls, value, name)

    def serialize(self, ctx, message):
        """Uses ctx.out_object, ctx.out_header or ctx.out_error to set
        ctx.out_body_doc, ctx.out_header_doc and ctx.out_document.
        """

        assert message in (self.RESPONSE,)

        self.event_manager.fire_event('before_serialize', ctx)

        if ctx.out_error is not None:
            # FIXME: There's no way to alter soap response headers for the user.
            ctx.out_document = [ctx.out_error.to_string(ctx.out_error)]

        else:
            # instantiate the result message
            result_message_class = ctx.descriptor.out_message
            result_message = result_message_class()

            # assign raw result to its wrapper, result_message
            out_type_info = result_message_class._type_info

            for i in range(len(out_type_info)):
                attr_name = result_message_class._type_info.keys()[i]
                setattr(result_message, attr_name, ctx.out_object[i])

            ctx.out_header_doc = None
            ctx.out_body_doc = self.serialize_impl(result_message_class,
                                                                 result_message)

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
        raise NotImplementedError("This is an output-only protocol.")


class HtmlMicroFormat(HtmlBase):
    mime_type = 'text/html'

    def __init__(self, app=None, validator=None, root_tag='div',
            child_tag='div', field_name_attr='class', skip_depth=0):
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

        HtmlBase.__init__(self, app, validator, skip_depth)

        assert root_tag in ('div','span')
        assert child_tag in ('div','span')
        assert field_name_attr in ('class','id')

        self.__root_tag = root_tag
        self.__child_tag = child_tag
        self.__field_name_attr = field_name_attr

        self.serialization_handlers = cdict({
            ModelBase: self.serialize_model_base,
            ByteArray: not_supported,
            Attachment: not_supported,
            ComplexModelBase: self.serialize_complex_model,
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

    @nillable_value
    def serialize_model_base(self, cls, value, name='retval'):
        return [ E(self.child_tag, cls.to_string(value), **{self.field_name_attr: name}) ]

    def serialize_impl(self, cls, value):
        return self.serialize_complex_model(cls, value, cls.get_type_name())

    @nillable_value
    def serialize_complex_model(self, cls, value, name='retval'):
        yield '<%s %s="%s">' % (self.root_tag, self.field_name_attr, name)

        if name is None:
            name = cls.get_type_name()

        inst = cls.get_serialization_instance(value)

        for k, v in cls.get_flat_type_info(cls).items():
            for val in self.serialize_class(v, getattr(inst, k, None), k):
                yield val

        yield '</%s>' % self.root_tag


def HtmlTable(app=None, validator=None, produce_header=True,
            table_name_attr='class', field_name_attr=None, border=0,
            fields_as='columns'):
    """Protocol that returns the response object as a html table.

    The simple flavour is like the HtmlMicroFormatprotocol, but returns data
    as a html table using the <table> tag.

    :param app: A rpclib.application.Application instance.
    :param validator: The validator to use. Ignored.
    :param produce_header: Boolean value to determine whether to show field
        names in the beginning of the table or not. Defaults to True. Set to
        False to skip headers.
    :param table_name_attr: The name of the attribute that will contain the
        response name of the complex object in the table tag. Set to None to
        disable.
    :param field_name_attr: The name of the attribute that will contain the
        field names of the complex object children for every table cell. Set
        to None to disable.
    :param fields_as: One of 'columns', 'rows'.

        "Fields as rows" returns one record per table in a table with two
        columns.

        "Fields as columns" returns one record per table row in a table that
        has as many columns as field names, just like a regular spreadsheet.
    """

    if fields_as == 'columns':
        return _HtmlColumnTable(app, validator, produce_header,
                                       table_name_attr, field_name_attr, border)
    elif fields_as == 'rows':
        return _HtmlRowTable(app, validator, produce_header,
                                       table_name_attr, field_name_attr, border)

    else:
        raise ValueError(fields_as)

class _HtmlTableBase(HtmlBase):
    mime_type = 'text/html'

    def __init__(self, app, validator, produce_header, table_name_attr,
                                                       field_name_attr, border):

        HtmlBase.__init__(self, app, validator)

        assert table_name_attr in (None, 'class','id')
        assert field_name_attr in (None, 'class','id')

        self.__produce_header = produce_header
        self.__table_name_attr = table_name_attr
        self.__field_name_attr = field_name_attr
        self.__border = border

    @property
    def border(self):
        return self.__border

    @property
    def produce_header(self):
        return self.__produce_header

    @property
    def table_name_attr(self):
        return self.__table_name_attr

    @property
    def field_name_attr(self):
        return self.__field_name_attr

    def serialize_impl(self, cls, inst):
        name = cls.get_type_name()

        if self.table_name_attr is None:
            out_body_doc_header = ['<table>']
        else:
            out_body_doc_header = ['<table %s="%s">' % (self.table_name_attr, name)]

        out_body_doc = self.serialize_complex_model(cls, inst)

        out_body_doc_footer = ['</table>']

        return chain(
                out_body_doc_header,
                out_body_doc,
                out_body_doc_footer,
            )


class _HtmlColumnTable(_HtmlTableBase):
    def serialize_complex_model(self, cls, value):
        sti = None
        fti = cls.get_flat_type_info(cls)

        first_child = iter(fti.values()).next()
        if len(fti) == 1:
            fti = first_child.get_flat_type_info(first_child)
            first_child = iter(fti.values()).next()

            if len(fti) == 1 and first_child.Attributes.max_occurs > 1:
                if issubclass(first_child, ComplexModelBase):
                    sti = first_child.get_simple_type_info(first_child)

            else:
                raise NotImplementedError("Can only serialize Array(...) types")
            
            value = value[0]

        else:
            raise NotImplementedError("Can only serialize single Array(...) return types")

        class_name = first_child.get_type_name()
        if self.produce_header:
            header_row = E.tr()

            if sti is None:
                header_row.append(E.th(class_name))

            else:
                if self.field_name_attr is None:
                    for k, v in sti.items():
                        header_row.append(E.th(k))

                else:
                    for k, v in sti.items():
                        header_row.append(E.th(k, **{self.field_name_attr: k}))

            yield header_row

        if sti is None:
            if self.field_name_attr is None:
                for val in value:
                    yield E.tr(E.td(first_child.to_string(val)), )
            else:
                for val in value:
                    yield E.tr(E.td(first_child.to_string(val)),
                                           **{self.field_name_attr: class_name})

        else:
            for val in value:
                row = E.tr()
                for k, v in sti.items():
                    subvalue = val
                    for p in v.path:
                        subvalue = getattr(subvalue, p, "`%s`" % k)
                    if self.field_name_attr is None:
                        row.append(E.td(v.type.to_string(subvalue)))
                    else:
                        row.append(E.td(v.type.to_string(subvalue),
                                                   **{self.field_name_attr: k}))
                yield row


class _HtmlRowTable(_HtmlTableBase):
    def serialize_complex_model(self, cls, value):
        sti = None
        fti = cls.get_flat_type_info(cls)
        is_array = False

        first_child = iter(fti.values()).next()
        if len(fti) == 1:
            fti = first_child.get_flat_type_info(first_child)
            first_child_2 = iter(fti.values()).next()

            if len(fti) == 1 and first_child_2.Attributes.max_occurs > 1:
                if issubclass(first_child_2, ComplexModelBase):
                    sti = first_child_2.get_simple_type_info(first_child_2)
                is_array = True

            else:
                if issubclass(first_child, ComplexModelBase):
                    sti = first_child.get_simple_type_info(first_child)
            
            value = value[0]

        else:
            raise NotImplementedError("Can only serialize single return types")

        class_name = first_child.get_type_name()
        if sti is None:
            if self.field_name_attr is None:
                if is_array:
                    for val in value:
                        yield E.tr(E.td(first_child_2.to_string(val)), )
                else:
                    yield E.tr(E.td(first_child_2.to_string(value)), )

            else:
                if is_array:
                    for val in value:
                        yield E.tr(E.td(first_child_2.to_string(val)),
                                           **{self.field_name_attr: class_name})
                else:
                    yield E.tr(E.td(first_child_2.to_string(value)),
                                           **{self.field_name_attr: class_name})

        else:
            for k, v in sti.items():
                row = E.tr()
                subvalue = value
                for p in v.path:
                    subvalue = getattr(subvalue, p, "`%s`" % k)

                if self.produce_header:
                    if self.field_name_attr is None:
                        row.append(E.th(k))
                    else:
                        row.append(E.th(k, **{self.field_name_attr: k}))

                if self.field_name_attr is None:
                    row.append(E.td(v.type.to_string(subvalue)))

                else:
                    row.append(E.td(v.type.to_string(subvalue),
                                               **{self.field_name_attr: k}))

                yield row
