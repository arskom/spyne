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

from lxml import html
from lxml.html.builder import E

from spyne import ModelBase, ByteArray, ComplexModelBase, Array, AnyUri, \
    ImageUri
from spyne.protocol.html import HtmlBase
from spyne.util import coroutine, Break
from spyne.util.oset import oset
from spyne.util.cdict import cdict
from spyne.util.six.moves.urllib.parse import urlencode, quote


class HtmlTableBase(HtmlBase):
    def __init__(self, app=None, ignore_uncap=False, ignore_wrappers=True,
            cloth=None, cloth_parser=None, header=True, table_name_attr='class',
                     table_name=None, table_class=None, field_name_attr='class',
              border=0, row_class=None, cell_class=None, header_cell_class=None,
                 polymorphic=True, hier_delim='.', doctype=None, link_gen=None,
                 mrpc_delim_text='|', table_width=None):

        super(HtmlTableBase, self).__init__(app=app,
                     ignore_uncap=ignore_uncap, ignore_wrappers=ignore_wrappers,
                cloth=cloth, cloth_parser=cloth_parser, polymorphic=polymorphic,
                                         hier_delim=hier_delim, doctype=doctype)

        self.header = header
        self.table_name_attr = table_name_attr
        self.table_name = table_name
        self.field_name_attr = field_name_attr
        self.border = border
        self.row_class = row_class
        self.cell_class = cell_class
        self.header_cell_class = header_cell_class
        self.link_gen = link_gen
        self.table_class = table_class
        self.table_width = table_width
        self.mrpc_delim_text = mrpc_delim_text

        if self.cell_class is not None and field_name_attr == 'class':
            raise Exception("Either 'cell_class' should be None or "
                            "field_name_attr should be != 'class'")

        if self.header_cell_class is not None and field_name_attr == 'class':
            raise Exception("Either 'header_cell_class' should be None or "
                            "field_name_attr should be != 'class'")

    def model_base_to_parent(self, ctx, cls, inst, parent, name,  **kwargs):
        parent.write(self.to_unicode(cls, inst))

    def null_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        pass


class HtmlColumnTable(HtmlTableBase):
    """Protocol that returns the response object as a html table.

    Returns one record per table row in a table that has as many columns as
    field names, just like a regular spreadsheet.

    The simple flavour is like the HtmlMicroFormatprotocol, but returns data
    as a html table using the <table> tag.

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
    :param mrpc_delim_text: The text that goes between mrpc calls.
    """

    def __init__(self, *args, **kwargs):
        super(HtmlColumnTable, self).__init__(*args, **kwargs)

        self.serialization_handlers.update({
            ModelBase: self.model_base_to_parent,
            ComplexModelBase: self.complex_model_to_parent,
            Array: self.array_to_parent,
        })

    def model_base_to_parent(self, ctx, cls, inst, parent, name,
                                                      from_arr=False, **kwargs):
        inst_str = ''
        if inst is not None:
            inst_str = self.to_unicode(cls, inst)

        if from_arr:
            td_attrs = {}
            #if self.field_name_attr:
            #    td_attrs[self.field_name_attr] = name
            parent.write(E.tr(
                E.td(
                    inst_str,
                    **td_attrs
                )
            ))

        else:
            parent.write(inst_str)

    @coroutine
    def _gen_row(self, ctx, cls, inst, parent, name, from_arr=False,
                                                    array_index=None, **kwargs):

        # because HtmlForm* protocols don't use the global null handler, it's
        # possible for null values to reach here.
        if inst is None:
            return

        logger.debug("Generate row for %r", cls)

        mrpc_delim_elt = ''
        if self.mrpc_delim_text is not None:
            mrpc_delim_elt = E.span(self.mrpc_delim_text,
                                      **{'class': 'mrpc-delimiter'})
            mrpc_delim_elt.tail = ' '

        with parent.element('tr'):
            for k, v in self.sort_fields(cls):
                attr = self.get_cls_attrs(v)
                if attr.exc:
                    logger.debug("\tExclude table cell %r type %r for %r",
                                                                      k, v, cls)
                    continue

                try:
                    sub_value = getattr(inst, k, None)
                except:  # e.g. SQLAlchemy could throw NoSuchColumnError
                    sub_value = None

                sub_name = attr.sub_name
                if sub_name is None:
                    sub_name = k

                if self.hier_delim is not None:
                    if array_index is None:
                        sub_name = "%s%s%s" % (name, self.hier_delim, sub_name)
                    else:
                        sub_name = "%s[%d]%s%s" % (name, array_index,
                                                     self.hier_delim, sub_name)

                logger.debug("\tGenerate table cell %r type %r for %r",
                                                               sub_name, v, cls)

                td_attrs = {}
                if self.field_name_attr is not None:
                    td_attrs[self.field_name_attr] = attr.sub_name or k
                if attr.hidden:
                    td_attrs['style'] = 'display:None'

                with parent.element('td', td_attrs):
                    ret = self.to_parent(ctx, v, sub_value, parent,
                                              sub_name, from_arr=from_arr,
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

            m = cls.Attributes.methods
            if m is not None and len(m) > 0:
                td_attrs = {'class': 'mrpc-cell'}

                with parent.element('td', td_attrs):
                    first = True

                    for mn, md in self._methods(cls, inst):
                        if first:
                            first = False
                        elif mrpc_delim_elt is not None:
                            parent.write(" ")
                            parent.write(mrpc_delim_elt)

                        pd = { }
                        for k, v in self.sort_fields(cls):
                            if getattr(v.Attributes, 'primary_key', None):
                                r = self.to_unicode(v, getattr(inst, k, None))
                                if r is not None:
                                    pd[k] = r

                        params = urlencode(pd)

                        mdid2key = ctx.app.interface.method_descriptor_id_to_key
                        href = mdid2key[id(md)].rsplit("}", 1)[-1]
                        text = md.translate(ctx.locale,
                                                  md.in_message.get_type_name())
                        parent.write(E.a(
                            text,
                            href="%s?%s" % (href, params),
                            **{'class': 'mrpc-operation'}
                        ))

            logger.debug("Generate row for %r done.", cls)
            self.extend_data_row(ctx, cls, inst, parent, name,
                                              array_index=array_index, **kwargs)

    def _gen_thead(self, ctx, cls, name, parent):
        logger.debug("Generate header for %r", cls)

        with parent.element('thead'):
            with parent.element('tr'):
                if issubclass(cls, ComplexModelBase):
                    fti = self.sort_fields(cls)
                    for k, v in fti:
                        attr = self.get_cls_attrs(v)
                        if attr.exc:
                            continue

                        th_attrs = {}
                        if self.field_name_attr is not None:
                            th_attrs[self.field_name_attr] = k
                        if attr.hidden:
                            th_attrs['style'] = 'display:None'

                        header_name = self.trc(v, ctx.locale, k)
                        parent.write(E.th(header_name, **th_attrs))

                    m = cls.Attributes.methods
                    if m is not None and len(m) > 0:
                        parent.write(E.th())

                else:
                    th_attrs = {}
                    if self.field_name_attr is not None:
                        th_attrs[self.field_name_attr] = name
                    header_name = self.trc(cls, ctx.locale, name)
                    parent.write(E.th(header_name, **th_attrs))

                self.extend_header_row(ctx, cls, parent, name)

    @coroutine
    def _gen_table(self, ctx, cls, inst, parent, name, gen_rows, **kwargs):
        logger.debug("Generate table for %r", cls)

        attrib = {}
        table_class = oset()
        if self.table_class is not None:
            table_class.add(self.table_class)

        if self.table_name_attr is not None:
            tn = (self.table_name
                        if self.table_name is not None else cls.get_type_name())

            if self.table_name_attr == 'class':
                table_class.add(tn)
            else:
                attrib[self.table_name_attr] = tn

        attrib['class'] = ' '.join(table_class)
        if self.table_width is not None:
            attrib['width'] = self.table_width

        self.event_manager.fire_event('before_table', ctx, cls, inst, parent,
                                                                 name, **kwargs)

        with parent.element('table', attrib):
            if self.header:
                self._gen_thead(ctx, cls, name, parent)

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

                self.extend_table(ctx, cls, parent, name, **kwargs)

    def complex_model_to_parent(self, ctx, cls, inst, parent, name,
                                                      from_arr=False, **kwargs):
        # If this is direct child of an array, table is already set up in
        # array_to_parent.
        if from_arr:
            return self._gen_row(ctx, cls, inst, parent, name, **kwargs)
        else:
            return self.wrap_table(ctx, cls, inst, parent, name, self._gen_row,
                                                                       **kwargs)

    def array_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        return self.wrap_table(ctx, cls, inst, parent, name,
                         super(HtmlColumnTable, self).array_to_parent, **kwargs)

    def wrap_table(self, ctx, cls, inst, parent, name, gen_rows, **kwargs):
        return self._gen_table(ctx, cls, inst, parent, name, gen_rows, **kwargs)

    # FIXME: These three should be events as well.
    def extend_table(self, ctx, cls, parent, name, **kwargs):
        pass

    def extend_data_row(self, ctx, cls, inst, parent, name, **kwargs):
        pass

    def extend_header_row(self, ctx, cls, parent, name, **kwargs):
        pass


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
            AnyUri: self.anyuri_to_parent,
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
                    try:
                        sub_value = getattr(inst, k, None)
                    except:  # e.g. SQLAlchemy could throw NoSuchColumnError
                        sub_value = None

                    sub_name = v.Attributes.sub_name
                    if sub_name is None:
                        sub_name = k

                    if sub_value is None and cls.Attributes.min_occurs == 0:
                        self.null_to_parent(ctx, cls, sub_value, parent,
                                                             sub_name, **kwargs)
                        continue

                    tr_attrib = {}
                    if self.row_class is not None:
                        tr_attrib['class'] = self.row_class
                    with parent.element('tr', tr_attrib):
                        th_attrib = {}
                        if self.header_cell_class is not None:
                            th_attrib['class'] = self.header_cell_class
                        if self.field_name_attr is not None:
                            th_attrib[self.field_name_attr] = sub_name
                        if sub_attrs.hidden:
                            th_attrib['style'] = 'display:None'
                        if self.header:
                            parent.write(E.th(
                                self.trc(v, ctx.locale, sub_name),
                                **th_attrib
                            ))

                        td_attrib = {}
                        if self.cell_class is not None:
                            td_attrib['class'] = self.cell_class
                        if self.field_name_attr is not None:
                            td_attrib[self.field_name_attr] = sub_name
                        if sub_attrs.hidden:
                            td_attrib['style'] = 'display:None'

                        with parent.element('td', td_attrib):
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
                        td_attrib = {}
                        cls_attrs = self.get_cls_attrs(cls)
                        if self.cell_class is not None:
                            td_attrib['class'] = self.cell_class
                        if cls_attrs.hidden:
                            td_attrib['style'] = 'display:None'

                        with parent.element('td', td_attrib):
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
