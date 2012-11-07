# encoding: utf8
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

"""The ``spyne.protocol.html`` module contains various EXPERIMENTAL protocols
for generating server-side Html. It seeks to eliminate the need for html
templates by:
    #. Implementing standard ways of serializing Python objects to Html
        documents
    #. Implementing a very basic html node manipulation api in python instead
        of having to have pseudocode intertwined within Html. (à la PHP)

As you can probably tell, not everything is figured out yet :)

Initially released in 2.8.0-rc.

This module is EXPERIMENTAL. You may not recognize the code here next time you
look at it.
"""

import logging
logger = logging.getLogger(__name__)

from itertools import chain

from lxml import html
from lxml.html.builder import E

from spyne.model import ModelBase
from spyne.model.binary import ByteArray
from spyne.model.binary import Attachment
from spyne.model.complex import Array
from spyne.model.complex import ComplexModelBase
from spyne.model.primitive import AnyUri
from spyne.model.primitive import ImageUri
from spyne.protocol import ProtocolBase
from spyne.util.cdict import cdict

def translate(cls, locale, default):
    retval = None
    if cls.Attributes.translations is not None:
        retval = cls.Attributes.translations.get(locale, None)
    if retval is None:
        return default
    return retval

def serialize_null(prot, cls, locale, name):
    return [ E(prot.child_tag, **{prot.field_name_attr: name}) ]

def nillable_value(func):
    def wrapper(prot, cls, value, locale, name):
        if value is None:
            if cls.Attributes.default is None:
                return serialize_null(prot, cls, locale, name)
            else:
                return func(prot, cls, cls.Attributes.default, locale, name)
        else:
            return func(prot, cls, value, locale, name)

    return wrapper

def not_supported(prot, cls, *args, **kwargs):
    raise Exception("Serializing %r Not Supported!" % cls)

class HtmlBase(ProtocolBase):
    def __init__(self, app=None, validator=None, skip_depth=0):
        """Protocol that returns the response object as a html microformat. See
        https://en.wikipedia.org/wiki/Microformats for more info.

        The simple flavour is like the XmlDocument protocol, but returns data in
        <div> or <span> tags.

        :param app: A spyne.application.Application instance.
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

    def serialize_class(self, cls, value, locale, name):
        handler = self.serialization_handlers[cls]
        return handler(cls, value, locale, name)

    def serialize(self, ctx, message):
        """Uses ctx.out_object, ctx.out_header or ctx.out_error to set
        ctx.out_body_doc, ctx.out_header_doc and ctx.out_document.
        """

        assert message in (self.RESPONSE, )

        self.event_manager.fire_event('before_serialize', ctx)

        if ctx.out_error is not None:
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
                                                result_message, ctx.locale)

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

        The simple flavour is like the XmlDocument protocol, but returns data in
        <div> or <span> tags.

        :param app: A spyne.application.Application instance.
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

        assert root_tag in ('div', 'span')
        assert child_tag in ('div', 'span')
        assert field_name_attr in ('class', 'id')

        self.__root_tag = root_tag
        self.__child_tag = child_tag
        self.__field_name_attr = field_name_attr

        self.serialization_handlers = cdict({
            ModelBase: self.serialize_model_base,
            ByteArray: not_supported,
            Attachment: not_supported,
            ComplexModelBase: self.serialize_complex_model,
            Array: self.serialize_array,
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
    def serialize_model_base(self, cls, value, locale, name):
        return [ E(self.child_tag, cls.to_string(value),
                                                **{self.field_name_attr: name}) ]

    def serialize_impl(self, cls, value, locale):
        return self.serialize_class(cls, value, locale, cls.get_type_name())

    @nillable_value
    def serialize_array(self, cls, value, locale, name):
        yield '<%s %s="%s">' % (self.root_tag, self.field_name_attr, name)

        (k,v), = cls._type_info.items()
        for subval in value:
            for val in self.serialize_class(cls=v,
                            value=subval, locale=locale, name=k):
                yield val

        yield '</%s>' % self.root_tag

    @nillable_value
    def serialize_complex_model(self, cls, value, locale, name):
        yield '<%s %s="%s">' % (self.root_tag, self.field_name_attr, name)

        if name is None:
            name = cls.get_type_name()

        inst = cls.get_serialization_instance(value)

        for k, v in cls.get_flat_type_info(cls).items():
            for val in self.serialize_class(cls=v,
                            value=getattr(inst, k, None), locale=locale, name=k):
                yield val

        yield '</%s>' % self.root_tag


def HtmlTable(app=None, validator=None, produce_header=True,
                    table_name_attr='class', field_name_attr=None, border=0,
                        fields_as='columns', row_class=None, cell_class=None,
                                                        header_cell_class=None):
    """Protocol that returns the response object as a html table.

    The simple flavour is like the HtmlMicroFormatprotocol, but returns data
    as a html table using the <table> tag.

    :param app: A spyne.application.Application instance.
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
    :param row_cell_class: value that goes inside the <tr class="">
    :param cell_cell_class: value that goes inside the <td class="">
    :param header_cell_class: value that goes inside the <th class="">

    "Fields as rows" returns one record per table in a table with two
    columns.

    "Fields as columns" returns one record per table row in a table that
    has as many columns as field names, just like a regular spreadsheet.
    """

    if fields_as == 'columns':
        return _HtmlColumnTable(app, validator, produce_header,
                                    table_name_attr, field_name_attr, border,
                                        row_class, cell_class, header_cell_class)
    elif fields_as == 'rows':
        return _HtmlRowTable(app, validator, produce_header,
                                 table_name_attr, field_name_attr, border,
                                        row_class, cell_class, header_cell_class)

    else:
        raise ValueError(fields_as)


class _HtmlTableBase(HtmlBase):
    mime_type = 'text/html'

    def __init__(self, app, validator, produce_header, table_name_attr,
                 field_name_attr, border, row_class, cell_class, header_cell_class):

        HtmlBase.__init__(self, app, validator)

        assert table_name_attr in (None, 'class', 'id')
        assert field_name_attr in (None, 'class', 'id')

        self.__produce_header = produce_header
        self.__table_name_attr = table_name_attr
        self.__field_name_attr = field_name_attr
        self.__border = border
        self.row_class = row_class
        self.cell_class = cell_class
        self.header_cell_class = header_cell_class

        if self.cell_class is not None and field_name_attr == 'class':
            raise Exception("Either 'cell_class' should be None or "
                            "field_name_attr should be != 'class'")
        if self.header_cell_class is not None and field_name_attr == 'class':
            raise Exception("Either 'header_cell_class' should be None or "
                            "field_name_attr should be != 'class'")

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

    def serialize_impl(self, cls, inst, locale):
        name = cls.get_type_name()

        if self.table_name_attr is None:
            out_body_doc_header = ['<table>']
        else:
            out_body_doc_header = ['<table %s="%s">' % (self.table_name_attr, name)]

        out_body_doc = self.serialize_complex_model(cls, inst, locale)

        out_body_doc_footer = ['</table>']

        return chain(
                out_body_doc_header,
                out_body_doc,
                out_body_doc_footer,
            )


class _HtmlColumnTable(_HtmlTableBase):
    def serialize_complex_model(self, cls, value, locale):
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

        # Here, sti can be None when the return type does not have _type_info
        # attribute
        tr = {}
        if self.row_class is not None:
            tr['class'] = self.row_class

        td = {}
        if self.cell_class is not None:
            td['class'] = self.cell_class

        class_name = first_child.get_type_name()
        if self.produce_header:
            header_row = E.tr(**tr)

            th = {}
            if self.header_cell_class is not None:
                th['class'] = self.header_cell_class

            if sti is None:
                header_row.append(E.th(class_name, **th))

            else:
                if self.field_name_attr is None:
                    for k, v in sti.items():
                        header_name = translate(v.type, locale, k)
                        header_row.append(E.th(header_name, **th))

                else:
                    for k, v in sti.items():
                        th[self.field_name_attr] = k
                        header_name = translate(v.type, locale, k)
                        header_row.append(E.th(header_name, **th))

            yield header_row

        if sti is None:
            if self.field_name_attr is None:
                for val in value:
                    yield E.tr(E.td(first_child.to_string(val), **td), **tr)

            else:
                for val in value:
                    td[self.field_name_attr] = class_name
                    yield E.tr(E.td(first_child.to_string(val), **td), **tr)

        else:
            for val in value:
                row = E.tr()
                for k, v in sti.items():
                    subvalue = val
                    for p in v.path:
                        subvalue = getattr(subvalue, p, None)

                    if subvalue is None:
                        if v.type.Attributes.min_occurs == 0:
                            continue
                        else:
                            subvalue = ""
                    else:
                        subvalue = _subvalue_to_html(v, subvalue)

                    if self.field_name_attr is None:
                        row.append(E.td(subvalue, **td))
                    else:
                        td[self.field_name_attr] = k
                        row.append(E.td(subvalue, **td))

                yield row


def _subvalue_to_html(cls, value):
    if issubclass(cls.type, AnyUri):
        href = getattr(value, 'href', None)
        if href is None: # this is not a AnyUri.Value instance.
            href = value
            text = getattr(cls.type.Attributes, 'text', None)
            content = None

        else:
            text = getattr(value, 'text', None)
            if text is None:
                text = getattr(cls.type.Attributes, 'text', None)

            content = getattr(value, 'content', None)

        if issubclass(cls.type, ImageUri):
            retval = E.img(src=href)

            if text is not None:
                retval.attrib['alt'] = text
            # content is ignored with ImageUri.

        else:
            retval = E.a(href=href)
            retval.text = text
            if content is not None:
                retval.append(content)

    else:
        retval = cls.type.to_string(value)

    return retval

class _HtmlRowTable(_HtmlTableBase):
    def serialize_complex_model(self, cls, value, locale):
        sti = None
        fti = cls.get_flat_type_info(cls)
        is_array = False

        if len(fti) == 1:
            first_child, = fti.values()

            try:
                fti = first_child.get_flat_type_info(first_child)
            except AttributeError:
                raise NotImplementedError("Can only serialize complex return types")

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

        tr = {}
        if self.row_class is not None:
            tr['class'] = self.row_class

        td = {}
        if self.cell_class is not None:
            td['class'] = self.cell_class

        th = {}
        if self.header_cell_class is not None:
            th['class'] = self.header_cell_class

        class_name = first_child.get_type_name()
        if sti is None:
            if self.field_name_attr is not None:
                td[self.field_name_attr] = class_name

            if is_array:
                for val in value:
                    yield E.tr(E.td(first_child_2.to_string(val), **td), **tr)
            else:
                yield E.tr(E.td(first_child_2.to_string(value), **td), **tr)

        else:
            for k, v in sti.items():
                row = E.tr(**tr)
                subvalue = value
                for p in v.path:
                    subvalue = getattr(subvalue, p, None)
                    if subvalue is None:
                        break

                if subvalue is None:
                    if v.type.Attributes.min_occurs == 0:
                        continue
                    else:
                        subvalue = ""
                else:
                    subvalue = _subvalue_to_html(v, subvalue)

                if self.produce_header:
                    header_text = translate(v.type, locale, k)
                    if self.field_name_attr is None:
                        row.append(E.th(header_text, **th))
                    else:
                        th[self.field_name_attr] = k
                        row.append(E.th(header_text, **th))

                if self.field_name_attr is None:
                    row.append(E.td(subvalue, **td))

                else:
                    td[self.field_name_attr] = k
                    row.append(E.td(subvalue, **td))

                yield row


class HtmlPage(object):
    """An EXPERIMENTAL protocol-ish that parses and generates a template for
    a html file.

    >>> open('temp.html', 'w').write('<html><body><div id="some_div" /></body></html>')
    >>> t = HtmlPage('temp.html')
    >>> t.some_div = "some_text"
    >>> from lxml import html
    >>> print html.tostring(t.html)
    <html><body><div id="some_div">some_text</div></body></html>
    """

    def __init__(self, file_name):
        self.__frozen = False
        self.__file_name = file_name
        self.__html = html.fromstring(open(file_name, 'r').read())

        self.__ids = {}
        for elt in self.__html.xpath('//*[@id]'):
            key = elt.attrib['id']
            if key in self.__ids:
                raise ValueError("Don't use duplicate values in id attributes in"
                                 "template documents.")
            self.__ids[key] = elt
            s = "%r -> %r" % (key, elt)
            logger.debug(s)

        self.__frozen = True

    @property
    def file_name(self):
        return self.__file_name

    @property
    def html(self):
        return self.__html

    def __getattr__(self, key):
        try:
            return object.__getattr__(self, key)

        except AttributeError:
            try:
                return self.__ids[key]
            except KeyError:
                raise AttributeError(key)

    def __setattr__(self, key, value):
        if key.endswith('__frozen') or not self.__frozen:
            object.__setattr__(self, key, value)

        else:
            elt = self.__ids.get(key, None)
            if elt is None:
                raise AttributeError(key)

            # poor man's elt.clear() version that keeps the attributes
            children = list(elt)
            for c in children:
                elt.remove(c)
            elt.text = None
            elt.tail = None

            # set it in.
            if isinstance(value, basestring):
                elt.text = value
            else:
                elt.append(value)
