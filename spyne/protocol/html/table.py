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
from spyne.protocol.html._base import NS_HTML
from spyne.util import coroutine, Break
from spyne.util.cdict import cdict


def HtmlTable(app=None, ignore_uncap=False, ignore_wrappers=True,
                     produce_header=True, table_name_attr='class',
                     field_name_attr='class', border=0, fields_as='columns',
                     row_class=None, cell_class=None, header_cell_class=None):
    """Protocol that returns the response object as a html table.

    The simple flavour is like the HtmlMicroFormatprotocol, but returns data
    as a html table using the <table> tag.

    :param app: A spyne.application.Application instance.
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
        return HtmlColumnTable(app, ignore_uncap, ignore_wrappers,
                    produce_header, table_name_attr, field_name_attr, border,
                                    row_class, cell_class, header_cell_class)
    elif fields_as == 'rows':
        return HtmlRowTable(app, ignore_uncap, ignore_wrappers,
                    produce_header, table_name_attr, field_name_attr, border,
                                    row_class, cell_class, header_cell_class)

    else:
        raise ValueError(fields_as)

class HtmlTableBase(HtmlBase):
    def __init__(self, app=None, ignore_uncap=False, ignore_wrappers=True,
                       cloth=None, attr_name='spyne_id', root_attr_name='spyne',
                                                              cloth_parser=None,
                             produce_header=True, table_name_attr='class',
                            field_name_attr='class', border=0, row_class=None,
                                cell_class=None, header_cell_class=None):

        super(HtmlTableBase, self).__init__(app=app,
                     ignore_uncap=ignore_uncap, ignore_wrappers=ignore_wrappers,
                cloth=cloth, attr_name=attr_name, root_attr_name=root_attr_name,
                                                      cloth_parser=cloth_parser)

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

    def model_base_to_parent(self, ctx, cls, inst, parent, name,  **kwargs):
        parent.write(self.to_string(cls, inst))

    def null_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        pass

class HtmlColumnTable(HtmlTableBase):
    def __init__(self, *args, **kwargs):
        super(HtmlColumnTable, self).__init__(*args, **kwargs)

        self.serialization_handlers = cdict({
            ModelBase: self.model_base_to_parent,
            AnyUri: self.anyuri_to_parent,
            ImageUri: self.imageuri_to_parent,
            ByteArray: self.not_supported,
            Attachment: self.not_supported,
            ComplexModelBase: self.complex_model_to_parent,
            Array: self.array_to_parent,
        })

    def model_base_to_parent(self, ctx, cls, inst, parent, name,
                                                      from_arr=False, **kwargs):
        if from_arr:
            td_attrs = {}
            #if self.field_name_attr:
            #    td_attrs[self.field_name_attr] = name
            parent.write(E.tr(
                E.td(
                    self.to_string(cls, inst),
                    **td_attrs
                )
            ))

        else:
            parent.write(self.to_string(cls, inst))

    @coroutine
    def _gen_row(self, ctx, cls, inst, parent, name, array_index=None, **kwargs):
        print "ROWWW"

        with parent.element('tr'):
            for k, v in cls.get_flat_type_info(cls).items():
                # FIXME: To be fixed to work with prot_attrs and renamed to exc
                if getattr(v.Attributes, 'exc_html', False) == True:
                    continue
                if getattr(v.Attributes, 'read', True) == False:
                    continue

                try:
                    sub_value = getattr(inst, k, None)
                except: # to guard against e.g. SQLAlchemy throwing NoSuchColumnError
                    sub_value = None

                sub_name = v.Attributes.sub_name
                if sub_name is None:
                    sub_name = k

                td_attrs = {}
                if self.field_name_attr is not None:
                    td_attrs[self.field_name_attr] = sub_name

                with parent.element('td', td_attrs):
                    ret = self.to_parent(ctx, v, sub_value, parent, sub_name,
                                              array_index=array_index, **kwargs)
                    if isgenerator(ret):
                        try:
                            while True:
                                sv2 = (yield)
                                ret.send(sv2)
                        except Break as b:
                            try:
                                ret.throw(b)
                            except StopIteration:
                                pass

            self.extend_data_row(ctx, cls, inst, parent, name, **kwargs)

    def _gen_header(self, ctx, cls, name, parent):
        with parent.element('thead'):
            with parent.element('tr'):
                th = {}
                if self.field_name_attr is not None:
                    th[self.field_name_attr] = name

                # fti is none when the type inside Array is not a ComplexModel.
                if issubclass(cls, ComplexModelBase):
                    fti = cls.get_flat_type_info(cls)
                    if self.field_name_attr is None:
                        for k, v in fti.items():
                            if getattr(v.Attributes, 'exc_html', None):
                                continue
                            header_name = self.translate(v, ctx.locale, k)
                            parent.write(E.th(header_name, **th))
                    else:
                        for k, v in fti.items():
                            if getattr(v.Attributes, 'exc_html', None):
                                continue
                            th[self.field_name_attr] = k
                            header_name = self.translate(v, ctx.locale, k)
                            parent.write(E.th(header_name, **th))

                else:
                    if self.field_name_attr is not None:
                        th[self.field_name_attr] = name
                    header_name = self.translate(cls, ctx.locale, name)
                    parent.write(E.th(header_name, **th))

                self.extend_header_row(ctx, cls, name, parent)

    @coroutine
    def _gen_table(self, ctx, cls, inst, parent, name, gen_rows, **kwargs):
        attrs = {}
        if self.table_name_attr is not None:
            attrs[self.table_name_attr] = cls.get_type_name()

        with parent.element('table', attrs):
            if self.produce_header:
                self._gen_header(ctx, cls, name, parent)

            with parent.element('tbody'):
                ret = gen_rows(ctx, cls, inst, parent, name, **kwargs)
                if isgenerator(ret):
                    try:
                        while True:
                            sv2 = (yield)
                            ret.send(sv2)
                    except Break as b:
                        try:
                            ret.throw(b)
                        except StopIteration:
                            pass

                ret = self.extend_table(ctx, cls, parent, name, **kwargs)
                if isgenerator(ret):
                    try:
                        while True:
                            sv2 = (yield)
                            ret.send(sv2)
                    except Break as b:
                        try:
                            ret.throw(b)
                        except StopIteration:
                            pass

    def complex_model_to_parent(self, ctx, cls, inst, parent, name,
                                                      from_arr=False, **kwargs):
        # If this is direct child of an array, table is already set up in the
        # array_to_parent.
        if from_arr:
            return self._gen_row(ctx, cls, inst, parent, name, **kwargs)
        else:
            return self._gen_table(ctx, cls, inst, parent, name, self._gen_row,
                                                                       **kwargs)

    def array_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        return self._gen_table(ctx, cls, inst, parent, name,
                         super(HtmlColumnTable, self).array_to_parent, **kwargs)

    def extend_table(self, ctx, cls, parent, name, **kwargs):
        pass

    def extend_data_row(self, ctx, cls, inst, parent, name, **kwargs):
        pass

    def extend_header_row(self, ctx, cls, parent, name, **kwargs):
        pass


class HtmlRowTable(HtmlTableBase):
    def __init__(self, *args, **kwargs):
        super(HtmlRowTable, self).__init__(*args, **kwargs)

        self.serialization_handlers = cdict({
            ModelBase: self.model_base_to_parent,
            AnyUri: self.anyuri_to_parent,
            ImageUri: self.imageuri_to_parent,
            ByteArray: self.not_supported,
            Attachment: self.not_supported,
            ComplexModelBase: self.complex_model_to_parent,
            Array: self.array_to_parent,
        })

    def model_base_to_parent(self, ctx, cls, inst, parent, name, from_arr=False, **kwargs):
        if from_arr:
            td_attrs = {}
            if False and self.field_name_attr:
                td_attrs[self.field_name_attr] = name

            parent.write(E.tr(E.td(self.to_string(cls, inst), **td_attrs)))
        else:
            parent.write(self.to_string(cls, inst))

    @coroutine
    def complex_model_to_parent(self, ctx, cls, inst, parent, name,
                                                      from_arr=False, **kwargs):
        attrs = {}
        if self.table_name_attr is not None:
            attrs[self.table_name_attr] = cls.get_type_name()

        with parent.element('table', attrs):
            with parent.element('tbody'):
                for k, v in cls.get_flat_type_info(cls).items():
                    try:
                        sub_value = getattr(inst, k, None)
                    except: # to guard against e.g. SQLAlchemy throwing NoSuchColumnError
                        sub_value = None

                    sub_name = v.Attributes.sub_name
                    if sub_name is None:
                        sub_name = k

                    with parent.element('tr'):
                        if self.produce_header:
                            parent.write(E.th(
                                self.translate(v, ctx.locale, sub_name),
                                **{self.field_name_attr: sub_name}
                            ))

                        td_attrs = {}
                        if self.field_name_attr is not None:
                            td_attrs[self.field_name_attr] = sub_name
                        with parent.element('td', td_attrs):
                            ret = self.to_parent(ctx, v, sub_value, parent,
                                                            sub_name, **kwargs)
                            if isgenerator(ret):
                                try:
                                    while True:
                                        sv2 = (yield)
                                        ret.send(sv2)
                                except Break as b:
                                    try:
                                        ret.throw(b)
                                    except StopIteration:
                                        pass

    @coroutine
    def array_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        with parent.element('div'):
            if issubclass(cls, ComplexModelBase):
                ret = super(HtmlRowTable, self).array_to_parent(
                                         ctx, cls, inst, parent, name, **kwargs)
                if isgenerator(ret):
                    try:
                        while True:
                            sv2 = (yield)
                            ret.send(sv2)
                    except Break as b:
                        try:
                            ret.throw(b)
                        except StopIteration:
                            pass
            else:
                table_attrs = {}
                if self.table_name_attr:
                    table_attrs = {self.table_name_attr: name}

                with parent.element('table', table_attrs):
                    with parent.element('tr'):
                        if self.produce_header:
                            parent.write(E.th(self.translate(cls, ctx.locale,
                                                          cls.get_type_name())))
                        with parent.element('td'):
                            with parent.element('table'):
                                ret = super(HtmlRowTable, self) \
                                    .array_to_parent(ctx, cls, inst, parent,
                                                                 name, **kwargs)
                                if isgenerator(ret):
                                    try:
                                        while True:
                                            sv2 = (yield)
                                            ret.send(sv2)
                                    except Break as b:
                                        try:
                                            ret.throw(b)
                                        except StopIteration:
                                            pass
