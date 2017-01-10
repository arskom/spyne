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

from __future__ import print_function

import logging
logger = logging.getLogger(__name__)

from inspect import isgenerator

from lxml.html.builder import E

from spyne import ModelBase, ByteArray, ComplexModelBase, Array, AnyUri, \
    ImageUri
from spyne.util import coroutine, Break
from spyne.util.cdict import cdict
from spyne.protocol.html.table import HtmlTableBase


class HtmlRowTable(HtmlTableBase):
    """Protocol that returns the response object as a html table.

    The simple flavour is like the HtmlMicroFormatprotocol, but returns data
    as a html table using the <table> tag.

    Returns one record per table in a table with two columns.

    :param app: A spyne.application.Application instance.
    :param header: Boolean value to determine whether to show field
        names in the beginning of the table or not. Defaults to True. Set to
        False to skip headers.
    :param table_name_attr: The name of the attribute that will contain the
        response name of the complex object in the table tag. Set to None to
        disable.
    :param table_name: When not none, overrides what goes in `table_name_attr`.
    :param table_class: When not none, specifies what goes in `class` attribute
        in the `<table>` tag. Table name gets appended when
        `table_name_attr == 'class'`
    :param field_name_attr: The name of the attribute that will contain the
        field names of the complex object children for every table cell. Set
        to None to disable.
    :param row_class: value that goes inside the <tr class="">
    :param cell_class: value that goes inside the <td class="">
    :param header_cell_class: value that goes inside the <th class="">
    """

    def __init__(self, *args, **kwargs):
        super(HtmlRowTable, self).__init__(*args, **kwargs)

        self.serialization_handlers = cdict({
            ModelBase: self.model_base_to_parent,
            AnyUri: self.any_uri_to_parent,
            ImageUri: self.imageuri_to_parent,
            ByteArray: self.not_supported,
            ComplexModelBase: self.complex_model_to_parent,
            Array: self.array_to_parent,
        })

    def model_base_to_parent(self, ctx, cls, inst, parent, name, from_arr=False,
                                                                      **kwargs):
        if from_arr:
            td_attrib = {}
            if False and self.field_name_attr:
                td_attrib[self.field_name_attr] = name

            parent.write(E.tr(E.td(self.to_unicode(cls, inst), **td_attrib)))
        else:
            parent.write(self.to_unicode(cls, inst))

    @coroutine
    def complex_model_to_parent(self, ctx, cls, inst, parent, name,
                                                      from_arr=False, **kwargs):
        attrib = {}
        if self.table_name_attr is not None:
            attrib[self.table_name_attr] = cls.get_type_name()
        if self.table_width is not None:
            attrib['width'] = self.table_width

        with parent.element('table', attrib):
            with parent.element('tbody'):
                for k, v in self.sort_fields(cls):
                    sub_attrs = self.get_cls_attrs(v)
                    if sub_attrs.exc:
                        logger.debug("\tExclude table cell %r type %r for %r",
                                                                      k, v, cls)
                        continue
                    try:
                        sub_value = getattr(inst, k, None)
                    except:  # e.g. SQLAlchemy could throw NoSuchColumnError
                        sub_value = None

                    sub_name = v.Attributes.sub_name
                    if sub_name is None:
                        sub_name = k

                    tr_attrs = {}
                    if self.row_class is not None:
                        self.add_html_attr('class', tr_attrs, self.row_class)

                    with parent.element('tr', tr_attrs):
                        th_attrs = {}

                        if self.header_cell_class is not None:
                            self.add_html_attr('class', th_attrs,
                                                         self.header_cell_class)

                        self.add_field_attrs(th_attrs, sub_name, v)

                        if sub_attrs.hidden:
                            self.add_style(th_attrs, 'display:None')

                        if self.header:
                            parent.write(E.th(
                                self.trc(v, ctx.locale, sub_name),
                                **th_attrs
                            ))

                        td_attrs = {}
                        if self.cell_class is not None:
                            self.add_html_attr('class', td_attrs,
                                                                self.cell_class)

                        self.add_field_attrs(td_attrs, sub_name, v)

                        if sub_attrs.hidden:
                            self.add_style(td_attrs, 'display:None')

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
                table_attrib = {}
                if self.table_name_attr:
                    table_attrib = {self.table_name_attr: name}
                if self.table_width is not None:
                    table_attrib['width'] = self.table_width

                with parent.element('table', table_attrib):
                    tr_attrib = {}
                    if self.row_class is not None:
                        tr_attrib['class'] = self.row_class
                    with parent.element('tr', tr_attrib):
                        if self.header:
                            parent.write(E.th(self.trc(cls, ctx.locale,
                                                          cls.get_type_name())))
                        td_attrs = {}

                        if self.cell_class is not None:
                            self.add_html_attr('class', td_attrs,
                                                                self.cell_class)

                        self.add_field_attrs(td_attrs, name, cls)

                        cls_attrs = self.get_cls_attrs(cls)

                        if cls_attrs.hidden:
                            self.add_style(td_attrs, 'display:None')

                        with parent.element('td', td_attrs):
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
