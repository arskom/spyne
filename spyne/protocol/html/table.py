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

from inspect import isgenerator

from lxml.html.builder import E

from spyne.model import ModelBase
from spyne.model import ByteArray
from spyne.model import ComplexModelBase
from spyne.model import Array
from spyne.model import AnyUri
from spyne.model import ImageUri
from spyne.model.binary import Attachment
from spyne.protocol.html import HtmlBase
from spyne.util import coroutine
from spyne.util.cdict import cdict


def HtmlTable(app=None, validator=None, produce_header=True,
                    ignore_uncap=False, ignore_wrappers=True,
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
        return _HtmlColumnTable(app, validator,
                                    ignore_uncap, ignore_wrappers,
                                    produce_header,
                                    table_name_attr, field_name_attr, border,
                                    row_class, cell_class, header_cell_class)
    elif fields_as == 'rows':
        return _HtmlRowTable(app, validator,
                                    ignore_uncap, ignore_wrappers,
                                    produce_header,
                                    table_name_attr, field_name_attr, border,
                                    row_class, cell_class, header_cell_class)

    else:
        raise ValueError(fields_as)

class _HtmlTableBase(HtmlBase):
    mime_type = 'text/html'

    def __init__(self, app, validator,
            ignore_uncap, ignore_wrappers,
            produce_header, table_name_attr,
            field_name_attr, border, row_class, cell_class, header_cell_class):

        super(_HtmlTableBase, self).__init__(app, validator, None,
                                                  ignore_uncap, ignore_wrappers)

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

    def anyuri_to_parent(self, ctx, cls, inst, parent, name, locale, **kwargs):
        attrs = {}
        if self.table_name_attr is not None:
            attrs[self.table_name_attr] = name
        with parent.element('td', attrs):
            super(_HtmlTableBase, self).anyuri_to_parent(ctx, cls, inst,
                                                 parent, name, locale, **kwargs)

    def imageuri_to_parent(self, ctx, cls, inst, parent, name, locale, **kwargs):
        attrs = {}
        if self.table_name_attr is not None:
            attrs[self.table_name_attr] = name
        with parent.element('td', attrs):
            super(_HtmlTableBase, self).imageuri_to_parent(ctx, cls, inst,
                                                parent, name, locale, **kwargs)

class _HtmlColumnTable(_HtmlTableBase):
    def __init__(self, *args, **kwargs):
        super(_HtmlColumnTable, self).__init__(*args, **kwargs)

        self.serialization_handlers = cdict({
            ModelBase: self.model_base_to_parent,
            AnyUri: self.anyuri_to_parent,
            ImageUri: self.imageuri_to_parent,
            ByteArray: self.not_supported,
            Attachment: self.not_supported,
            ComplexModelBase: self.complex_model_to_parent,
            Array: self.array_to_parent,
        })

    def model_base_to_parent(self, ctx, cls, inst, parent, name, locale, tr_child=False, **kwargs):
        attrs = {}
        if self.field_name_attr is not None:
            attrs = {self.field_name_attr: name}
        retval = E.td(self.to_string(cls, inst), **attrs)
        if not tr_child:
            retval = E.tr(retval)
        parent.write(retval)

    @coroutine
    def subserialize(self, ctx, cls, inst, parent, ns=None, name=None):
        attrs = {}
        if self.table_name_attr is not None:
            attrs[self.table_name_attr] = name

        locale =ctx.locale
        with parent.element('table', attrs):
            fti = None
            if issubclass(cls, ComplexModelBase):
                fti = cls.get_flat_type_info(cls)
            if self.produce_header:
                with parent.element('thead'):
                    header_row = E.tr()

                    th = {}
                    if self.header_cell_class is not None:
                        th['class'] = self.header_cell_class

                    # fti is none when the type inside Array is not a ComplexModel.
                    if fti is None:
                        if self.field_name_attr is not None:
                            th[self.field_name_attr] = name
                        header_name = self.translate(cls, locale, name)
                        header_row.append(E.th(header_name, **th))

                    else:
                        if self.field_name_attr is None:
                            for k, v in fti.items():
                                header_name = self.translate(v, locale, k)
                                header_row.append(E.th(header_name, **th))

                        else:
                            for k, v in fti.items():
                                th[self.field_name_attr] = k
                                header_name = self.translate(v, locale, k)
                                header_row.append(E.th(header_name, **th))

                    parent.write(header_row)

            with parent.element('tbody'):
                if cls.Attributes.max_occurs > 1:
                    ret = self.array_to_parent(ctx, cls, inst, parent, name,
                                                                     ctx.locale)

                    if isgenerator(ret):
                        while True:
                            y = (yield)
                            ret.send(y)

                else:
                    with parent.element('tr'):
                        ret = self.to_parent(ctx, cls, inst, parent, name,
                                                                         locale)
                        if isgenerator(ret):
                            while True:
                                y = (yield)
                                ret.send(y)

    @coroutine
    def complex_model_to_parent(self, ctx, cls, inst, parent, name, locale,
                                                      tr_child=False, **kwargs):
        attrs = {}
        if tr_child is False:
            with parent.element('tr', attrs):
                ret = self._get_members(ctx, cls, inst, parent, locale,
                                                    tr_child=True, **kwargs)
                if isgenerator(ret):
                    while True:
                        y = (yield)
                        ret.send(y)

        else:
            if self.table_name_attr is not None:
                attrs[self.table_name_attr] = name
            with parent.element('td', attrs):
                ret = self.subserialize(ctx, cls, inst, parent, None, name)
                if isgenerator(ret):
                    while True:
                        y = (yield)
                        ret.send(y)


class _HtmlRowTable(_HtmlTableBase):
    def __init__(self, *args, **kwargs):
        super(_HtmlRowTable, self).__init__(*args, **kwargs)

        self.serialization_handlers = cdict({
            ModelBase: self.model_base_to_parent,
            AnyUri: self.anyuri_to_parent,
            ImageUri: self.imageuri_to_parent,
            ByteArray: self.not_supported,
            Attachment: self.not_supported,
            ComplexModelBase: self.complex_model_to_parent,
            Array: self.array_to_parent,
        })

    @coroutine
    def subserialize(self, ctx, cls, inst, parent, ns=None, name=None):
        attrs = {}
        if self.table_name_attr is not None:
            attrs[self.table_name_attr] = name

        locale =ctx.locale
        with parent.element('table', attrs):
            with parent.element('tbody'):
                if cls.Attributes.max_occurs > 1:
                    ret = self.array_to_parent(ctx, cls, inst, parent, name,
                                                                     ctx.locale)

                    if isgenerator(ret):
                        while True:
                            y = (yield)
                            ret.send(y)

                else:
                    with parent.element('tr'):
                        ret = self.to_parent(ctx, cls, inst, parent, name,
                                                                     locale)

                        if isgenerator(ret):
                            while True:
                                y = (yield)
                                ret.send(y)

    @coroutine
    def complex_model_to_parent(self, ctx, cls, inst, parent, name, locale,
                                                    tr_child=False, **kwargs):
        attrs = {}
        if tr_child is False:
            ret = self._get_members(ctx, cls, inst, parent, locale,
                                                tr_child=True, **kwargs)
            if isgenerator(ret):
                while True:
                    y = (yield)
                    ret.send(y)

        else:
            if self.table_name_attr is not None:
                attrs[self.table_name_attr] = name
            with parent.element('tr', attrs):
                if self.produce_header:
                    parent.write(E.th(self.translate(cls, locale, name),
                                                **{self.field_name_attr: name}))
                with parent.element('td', attrs):
                    ret = self.subserialize(ctx, cls, inst, parent, None, name)
                    if isgenerator(ret):
                        while True:
                            y = (yield)
                            ret.send(y)

    def model_base_to_parent(self, ctx, cls, inst, parent, name, locale,
                                                                      **kwargs):
        retval = E.tr()
        attr = {}
        if self.field_name_attr is not None:
            attr = {self.field_name_attr: name}

        if self.produce_header:
            retval.append(E.th(self.translate(cls, locale, name), **attr))

        retval.append(E.td(self.to_string(cls, inst), **attr))
        parent.write(retval)
