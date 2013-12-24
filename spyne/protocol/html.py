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

from spyne.util import six, coroutine, Break

from itertools import chain
from inspect import isgenerator

from lxml import html
from lxml.html.builder import E

from spyne.util.six import StringIO

from spyne import BODY_STYLE_WRAPPED
from spyne.model import ModelBase, PushBase
from spyne.model.binary import ByteArray
from spyne.model.binary import Attachment
from spyne.model.complex import Array
from spyne.model.complex import ComplexModelBase
from spyne.model.primitive import AnyHtml
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


def _not_supported(prot, cls, *args, **kwargs):
    raise Exception("Serializing %r Not Supported!" % cls)


class HtmlBase(ProtocolBase):
    def serialize_class(self, cls, value, locale, name):
        handler = self.serialization_handlers[cls]
        return handler(cls, value, locale, name)

    def serialize(self, ctx, message):
        """Uses ``ctx.out_object``, ``ctx.out_header`` or ``ctx.out_error`` to
        set ``ctx.out_body_doc``, ``ctx.out_header_doc`` and
        ``ctx.out_document`` as an ``lxml.etree._Element instance``.

        Not meant to be overridden.
        """

        assert message in (self.REQUEST, self.RESPONSE)

        self.event_manager.fire_event('before_serialize', ctx)

        if ctx.out_error is not None:
            # All errors at this point must be Fault subclasses.
            cls = ctx.out_error.__class__
            tns = self.app.interface.get_tns()

            if ctx.out_stream is None:
                ctx.out_stream = StringIO()

            ctx.out_document = E.div()
            from lxml import etree
            with etree.xmlfile(ctx.out_stream) as xf:
                retval = HtmlMicroFormat().to_parent(ctx,
                    ctx.out_error.__class__, ctx.out_error, xf,
                    ctx.out_error.get_type_name(), ctx.locale)

        else:
            assert message is self.RESPONSE
            result_message_class = ctx.descriptor.out_message

            # assign raw result to its wrapper, result_message
            if ctx.descriptor.body_style == BODY_STYLE_WRAPPED:
                result_message = result_message_class()

                for i, attr_name in enumerate(
                                        result_message_class._type_info.keys()):
                    setattr(result_message, attr_name, ctx.out_object[i])

            else:
                result_message = ctx.out_object

            if ctx.out_stream is None:
                ctx.out_stream = StringIO()

            name = result_message.get_type_name()
            retval = self.incgen(ctx, result_message_class, result_message,
                                                               name, ctx.locale)

        self.event_manager.fire_event('after_serialize', ctx)

        return retval

    @coroutine
    def incgen(self, ctx, cls, inst, name, locale):
        if name is None:
            name = cls.get_type_name()

        from lxml import etree
        # FIXME: html.htmlfile olmali
        with etree.xmlfile(ctx.out_stream) as xf:
            ret = self.to_parent(ctx, cls, inst, xf, name, locale)

            if isgenerator(ret):
                try:
                    while True:
                        y = (yield) # may throw Break
                        ret.send(y)

                except Break:
                    try:
                        ret.throw(Break())
                    except StopIteration:
                        pass

        if hasattr(ctx.out_stream, 'finish'):
            ctx.out_stream.finish()

    def create_out_string(self, ctx, charset=None):
        """Sets an iterable of string fragments to ctx.out_string"""

        if charset is None:
            charset = 'UTF-8'

        ctx.out_string = [ctx.out_stream.getvalue()]

    def subserialize(self, ctx, cls, inst, parent, ns=None, name=None):
        if name is None:
            name = cls.get_type_name()
        return self.to_parent(ctx, cls, inst, parent, name, ctx.locale)

    def decompose_incoming_envelope(self, ctx, message):
        raise NotImplementedError("This is an output-only protocol.")

    def to_parent(self, ctx, cls, inst, parent, locale, name):
        raise NotImplementedError("This must be implemented in a subclass.")


class HtmlMicroFormat(HtmlBase):
    mime_type = 'text/html'

    def __init__(self, app=None, validator=None, root_tag='div',
                 child_tag='div', field_name_attr='class', 
                 field_name_tag=None, field_name_class='field_name'):
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
        """

        super(HtmlMicroFormat, self).__init__(app, validator)

        assert root_tag in ('div', 'span')
        assert child_tag in ('div', 'span')
        assert field_name_attr in ('class', 'id')
        assert field_name_tag in (None, 'span', 'div')

        self.root_tag = root_tag
        self.child_tag = child_tag
        self.field_name_attr = field_name_attr
        self.field_name_tag = field_name_tag
        if field_name_tag is not None:
            self.field_name_tag = getattr(E, field_name_tag)
        self._field_name_class = field_name_class

        self.serialization_handlers = cdict({
            ModelBase: self.serialize_model_base,
            ByteArray: _not_supported,
            Attachment: _not_supported,
            ComplexModelBase: self.serialize_complex_model,
            Array: self.serialize_array,
        })

    def serialize_model_base(self, ctx, cls, inst, parent, name, locale):
        retval = E(self.child_tag, **{self.field_name_attr: name})
        data_str = self.to_string(cls, inst)

        if self.field_name_tag is not None:
            field_name = cls.Attributes.translations.get(locale, name)
            field_name_tag = self.field_name_tag(field_name,
                                             **{'class':self._field_name_class})
            field_name_tag.tail = data_str
            retval.append(field_name_tag)

        else:
            retval.text = data_str

        parent.write(retval)

    def to_parent(self, ctx, cls, inst, parent, name, locale):
        subprot = getattr(cls.Attributes, 'prot', None)
        if subprot is not None:
            return subprot.subserialize(ctx, cls, inst, parent, None, name)

        handler = self.serialization_handlers[cls]
        if inst is None:
            if cls.Attributes.default is None:
                return self.serialize_null(ctx, cls, inst, parent, name, locale)
            return handler(ctx, cls, cls.Attributes.default, parent, name, locale)
        return handler(ctx, cls, inst, parent, name, locale)

    @coroutine
    def _get_members(self, ctx, cls, inst, parent, locale):
        parent_cls = getattr(cls, '__extends__', None)
        if not (parent_cls is None):
            ret = self._get_members(ctx, parent_cls, inst, parent)
            if ret is not None:
                while True:
                    sv2 = (yield)
                    ret.send(sv2)

        for k, v in cls._type_info.items():
            try:
                subvalue = getattr(inst, k, None)
            except: # to guard against e.g. SqlAlchemy throwing NoSuchColumnError
                subvalue = None

            sub_name = v.Attributes.sub_name
            if sub_name is None:
                sub_name = k

            mo = v.Attributes.max_occurs
            if subvalue is not None and mo > 1:
                if isinstance(subvalue, PushBase):
                    while True:
                        sv = (yield)
                        ret = self.to_parent(ctx, v, sv, parent, sub_name, locale)
                        if ret is not None:
                            while True:
                                sv2 = (yield)
                                ret.send(sv2)

                else:
                    for sv in subvalue:
                        ret = self.to_parent(ctx, v, sv, parent, sub_name, locale)

                        if ret is not None:
                            while True:
                                sv2 = (yield)
                                ret.send(sv2)

            # Don't include empty values for non-nillable optional attributes.
            elif subvalue is not None or v.Attributes.min_occurs > 0:
                ret = self.to_parent(ctx, v, subvalue, parent, sub_name, locale)
                if ret is not None:
                    while True:
                        sv2 = (yield)
                        ret.send(sv2)

    @coroutine
    def serialize_complex_model(self, ctx, cls, inst, parent, name, locale):
        attrs = {self.field_name_attr: name}
        with parent.element(self.root_tag, attrs):
            ret = self._get_members(ctx, cls, inst, parent, locale)
            if isgenerator(ret):
                try:
                    while True:
                        y = (yield) # Break could be thrown here
                        ret.send(y)

                except Break:
                    try:
                        ret.throw(Break())
                    except StopIteration:
                        pass

    @coroutine
    def serialize_array(self, ctx, cls, inst, parent, name, locale):
        attrs = {self.field_name_attr: name}

        if issubclass(cls, Array):
            cls, = cls._type_info.values()

        name = cls.get_type_name()
        with parent.element(self.root_tag, attrs):
            if isinstance(inst, PushBase):
                while True:
                    sv = (yield)
                    ret = self.to_parent(ctx, cls, sv, parent, name, locale)
                    if ret is not None:
                        while True:
                            sv2 = (yield)
                            ret.send(sv2)

            else:
                for sv in inst:
                    ret = self.to_parent(ctx, cls, sv, parent, name, locale)
                    if isgenerator(ret):
                        try:
                            while True:
                                y = (yield) # Break could be thrown here
                                ret.send(y)

                        except Break:
                            try:
                                ret.throw(Break())
                            except StopIteration:
                                pass

    def serialize_null(self, ctx, cls, inst, parent, name, locale):
        return [ E(self.child_tag, **{self.field_name_attr: name}) ]


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
    :param row_class: value that goes inside the <tr class="">
    :param cell_class: value that goes inside the <td class="">
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

        super(_HtmlTableBase, self).__init__(app, validator)

        assert table_name_attr in (None, 'class', 'id')
        assert field_name_attr in (None, 'class', 'id')

        self.produce_header = produce_header
        self.table_name_attr = table_name_attr
        self.field_name_attr = field_name_attr
        self.border = border
        self.row_class = row_class
        self.cell_class = cell_class
        self.header_cell_class = header_cell_class

        if self.cell_class is not None and field_name_attr == 'class':
            raise Exception("Either 'cell_class' should be None or "
                            "field_name_attr should be != 'class'")
        if self.header_cell_class is not None and field_name_attr == 'class':
            raise Exception("Either 'header_cell_class' should be None or "
                            "field_name_attr should be != 'class'")

    def serialize_impl(self, cls, inst, locale):
        name = cls.get_type_name()

        if self.table_name_attr is None:
            out_body_doc_header = ['<table>']
        else:
            out_body_doc_header = ['<table %s="%s">' % (self.table_name_attr,
                                                                          name)]

        out_body_doc = self.serialize_complex_model(cls, inst, locale)

        out_body_doc_footer = ['</table>']

        return chain(
                out_body_doc_header,
                out_body_doc,
                out_body_doc_footer,
            )

    def serialize_complex_model(self, cls, inst, locale):
        raise NotImplementedError()

class _HtmlColumnTable(_HtmlTableBase):
    def serialize_complex_model(self, cls, value, locale):
        fti = cls.get_flat_type_info(cls)
        if cls.Attributes._wrapper and not issubclass(cls, Array):
            if len(fti) > 1:
                raise NotImplementedError("Can only serialize one array at a time")
            cls, = cls._type_info.values()
            value, = value

        fti = cls.get_flat_type_info(cls)
        first_child = next(iter(fti.values()))
        if not issubclass(cls, Array):
            raise NotImplementedError("Can only serialize Array(...) types")

        sti = None
        if issubclass(first_child, ComplexModelBase):
            sti = first_child.get_simple_type_info(first_child)

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

            # sti is none when the type inside Array is not a ComplexModel.
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

        if value is None:
            raise StopIteration()

        if sti is None:
            if self.field_name_attr is None:
                for val in value:
                    yield E.tr(E.td(self.to_string(first_child, val),**td),**tr)

            else:
                for val in value:
                    td[self.field_name_attr] = class_name
                    yield E.tr(E.td(self.to_string(first_child, val),**td),**tr)

        else:
            for val in value:
                row = E.tr()
                for k, v in sti.items():
                    subvalue = val
                    for p in v.path:
                        subvalue = getattr(subvalue, p, None)

                    if subvalue is None:
                        subvalue = ""
                    else:
                        subvalue = _subvalue_to_html(self, v, subvalue)

                    if self.field_name_attr is None:
                        row.append(E.td(subvalue, **td))
                    else:
                        td[self.field_name_attr] = k
                        row.append(E.td(subvalue, **td))

                yield row


def _subvalue_to_html(prot, cls, value):
    if issubclass(cls.type, AnyHtml):
        retval = value

    elif issubclass(cls.type, AnyUri):
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
        retval = prot.to_string(cls.type, value)

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
                raise NotImplementedError(
                                     "Can only serialize complex return types")

            first_child_2 = next(iter(fti.values()))

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
                    yield E.tr(E.td(self.to_string(first_child_2, val), **td),
                                                                        **tr)
            else:
                yield E.tr(E.td(self.to_string(first_child_2, value), **td),
                                                                        **tr)

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
                    subvalue = _subvalue_to_html(self, v, subvalue)

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

    reserved = ('html', 'file_name')

    def __init__(self, file_name):
        self.__frozen = False
        self.__file_name = file_name
        self.__html = html.fromstring(open(file_name, 'r').read())

        self.__ids = {}
        for elt in self.__html.xpath('//*[@id]'):
            key = elt.attrib['id']
            if key in self.__ids:
                raise ValueError("Don't use duplicate values in id attributes "
                                 "of the tags in template documents. "
                                 "id=%r appears more than once." % key)
            if key in HtmlPage.reserved:
                raise ValueError("id attribute values %r are reserved." %
                                                              HtmlPage.reserved)

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

            # set it in.
            if isinstance(value, six.string_types):
                elt.text = value
            else:
                elt.addnext(value)
                parent = elt.getparent()
                parent.remove(elt)
                self.__ids[key] = value
