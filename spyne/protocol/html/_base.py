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

from lxml import etree, html

from spyne.protocol.cloth import XmlCloth


class HtmlBase(XmlCloth):
    mime_type = 'text/html'

    def __init__(self, app=None, mime_type=None, ignore_uncap=False,
                 ignore_wrappers=False, cloth=None, attr_name='spyne_id',
                 root_attr_name='spyne', cloth_parser=None, polymorphic=True,
                                                  hier_delim='.', doctype=None):
        super(HtmlBase, self).__init__(app=app, mime_type=mime_type,
            ignore_uncap=ignore_uncap, ignore_wrappers=ignore_wrappers,
            cloth=cloth, attr_name=attr_name, root_attr_name=root_attr_name,
            cloth_parser=cloth_parser, polymorphic=polymorphic)

        self.hier_delim = hier_delim
        self.doctype = doctype

    def _parse_file(self, file_name, cloth_parser):
        if cloth_parser is None:
            cloth_parser = html.HTMLParser(remove_comments=True)

        self._cloth = html.parse(self._cloth, parser=cloth_parser)
        self._cloth = self._cloth.getroot()

    def docfile(self, *args, **kwargs):
        return etree.htmlfile(*args, **kwargs)

    def write_doctype(self, xf):
        if self._root_cloth is not None:
            # FIXME: write the doctype of the cloth
            xf.write_doctype("<!DOCTYPE html>")
