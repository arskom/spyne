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


from spyne.protocol.html import HtmlBase


class HtmlTableBase(HtmlBase):
    def __init__(self, app=None, ignore_uncap=False, ignore_wrappers=True,
            cloth=None, cloth_parser=None, header=True, table_name_attr='class',
            table_name=None, table_class=None, border=0, row_class=None,
            field_name_attr='class', field_type_name_attr='class',
            cell_class=None, header_cell_class=None, polymorphic=True,
            hier_delim='.', doctype=None, link_gen=None, mrpc_delim_text='|',
                                                              table_width=None):

        super(HtmlTableBase, self).__init__(app=app,
                     ignore_uncap=ignore_uncap, ignore_wrappers=ignore_wrappers,
                cloth=cloth, cloth_parser=cloth_parser, polymorphic=polymorphic,
                                         hier_delim=hier_delim, doctype=doctype)

        self.header = header
        self.table_name_attr = table_name_attr
        self.table_name = table_name
        self.field_name_attr = field_name_attr
        self.field_type_name_attr = field_type_name_attr
        self.border = border
        self.row_class = row_class
        self.cell_class = cell_class
        self.header_cell_class = header_cell_class
        self.link_gen = link_gen
        self.table_class = table_class
        self.table_width = table_width
        self.mrpc_delim_text = mrpc_delim_text

    def null_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        pass

    def add_field_attrs(self, attr_dict, name, cls):
        if self.field_name_attr:
            self.add_html_attr(self.field_name_attr, attr_dict, name)

        if self.field_type_name_attr:
            types = set()
            c = cls
            while c is not None:
                if c.Attributes._explicit_type_name or c.__extends__ is None:
                    types.add(c.get_type_name())

                c = c.__extends__

            self.add_html_attr(self.field_type_name_attr, attr_dict,
                                                                ' '.join(types))
