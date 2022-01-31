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

from spyne import ModelBase, ComplexModelBase, Array
from spyne.util import coroutine, Break, urlencode
from spyne.util.oset import oset
from spyne.protocol.html.table import HtmlTableBase


class HtmlColumnTableRowProtocol(object):
    def column_table_gen_header(self, ctx, cls, parent, name, **kwargs):
        return False

    def column_table_before_row(self, ctx, cls, inst, parent, name, **kwargs):
        pass

    def column_table_after_row(self, ctx, cls, inst, parent, name, **kwargs):
        pass



class HtmlColumnTable(HtmlTableBase, HtmlColumnTableRowProtocol):
    """Protocol that returns the response object as a html table.

    Returns one record per table row in a table that has as many columns as
    field names, just like a regular spreadsheet.

    This is not quite unlike the HtmlMicroFormatprotocol, but returns data
    as a html table using the <table> tag.

    Generally used to serialize Array()'s of ComplexModel objects. If an
    array has prot=HtmlColumnTable, its serializer (what's inside the Array( ))
    must implement HtmlColumnTableRowProtocol interface.

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
    :param mrpc_delim_text: The text that goes between mrpc sessions.
    """

    def __init__(self, *args, **kwargs):
        before_table = kwargs.pop('before_table', None)

        super(HtmlColumnTable, self).__init__(*args, **kwargs)

        self.serialization_handlers.update({
            ModelBase: self.model_base_to_parent,
            ComplexModelBase: self.complex_model_to_parent,
            Array: self.array_to_parent,
        })

        if before_table is not None:
            self.event_manager.add_listener("before_table", before_table)

    def model_base_to_parent(self, ctx, cls, inst, parent, name,
                                                      from_arr=False, **kwargs):
        inst_str = ''
        if inst is not None:
            inst_str = self.to_unicode(cls, inst)

        if from_arr:
            td_attrs = {}

            self.add_field_attrs(td_attrs, name, cls)

            parent.write(E.tr(E.td(inst_str, **td_attrs)))

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
                cls_attr = self.get_cls_attrs(v)
                if cls_attr.exc:
                    logger.debug("\tExclude table cell %r type %r for %r",
                                                                      k, v, cls)
                    continue

                try:
                    sub_value = getattr(inst, k, None)
                except:  # e.g. SQLAlchemy could throw NoSuchColumnError
                    sub_value = None

                sub_name = cls_attr.sub_name
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

                self.add_field_attrs(td_attrs, cls_attr.sub_name or k, v)

                if cls_attr.hidden:
                    self.add_style(td_attrs, 'display:None')

                with parent.element('td', td_attrs):
                    ret = self.to_parent(ctx, v, sub_value, parent, sub_name,
                           from_arr=from_arr, array_index=array_index, **kwargs)

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

                    for mn, md in self._methods(ctx, cls, inst):
                        if first:
                            first = False
                        elif mrpc_delim_elt is not None:
                            parent.write(" ")
                            parent.write(mrpc_delim_elt)

                        pd = {}
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

    def _gen_thead(self, ctx, cls, parent, name):
        logger.debug("Generate header for %r", cls)

        with parent.element('thead'):
            with parent.element('tr'):
                if issubclass(cls, ComplexModelBase):
                    fti = self.sort_fields(cls)
                    for k, v in fti:
                        cls_attr = self.get_cls_attrs(v)
                        if cls_attr.exc:
                            continue

                        th_attrs = {}
                        self.add_field_attrs(th_attrs, k, cls)

                        if cls_attr.hidden:
                            self.add_style(th_attrs, 'display:None')

                        header_name = self.trc(v, ctx.locale, k)
                        parent.write(E.th(header_name, **th_attrs))

                    m = cls.Attributes.methods
                    if m is not None and len(m) > 0:
                        th_attrs = {'class': 'mrpc-cell'}
                        parent.write(E.th(**th_attrs))

                else:
                    th_attrs = {}
                    self.add_field_attrs(th_attrs, name, cls)

                    header_name = self.trc(cls, ctx.locale, name)

                    parent.write(E.th(header_name, **th_attrs))

                self.extend_header_row(ctx, cls, parent, name)

    @coroutine
    def _gen_table(self, ctx, cls, inst, parent, name, gen_rows, **kwargs):
        logger.debug("Generate table for %r", cls)
        cls_attrs = self.get_cls_attrs(cls)

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
                                                      name, prot=self, **kwargs)

        with parent.element('table', attrib):
            write_header = self.header
            if cls_attrs.header is False:
                write_header = cls_attrs.header

            if write_header:
                ret = False

                subprot = self.get_subprot(ctx, cls_attrs)
                if subprot is not None:
                    ret = subprot.column_table_gen_header(ctx, cls, parent,
                                                                           name)
                if not ret:
                    self._gen_thead(ctx, cls, parent, name)

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

    def extend_table(self, ctx, cls, parent, name, **kwargs):
        """This is called as the last operation during the table body generation
        after all the <tr> tags are generated before exiting the <table> tag
        which in turn is inside a <tbody> tag."""

    def extend_data_row(self, ctx, cls, inst, parent, name, **kwargs):
        """This is called as the last operation during the row generation
        after all the <td> tags are generated before exiting the <tr> tag which
        in turn is inside a <tbody> tag."""

    def extend_header_row(self, ctx, cls, parent, name, **kwargs):
        """This is called once as the last operation during the table header
        generation after all the <th> tags are generated before exiting the <tr>
        tag which in turn is inside a <thead> tag."""
