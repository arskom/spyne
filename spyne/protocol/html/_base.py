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

from lxml.builder import ElementMaker

from spyne.protocol.cloth import XmlCloth
NS_HTML = "http://www.w3.org/1999/xhtml"
NSMAP = {None: NS_HTML}

E = ElementMaker(namespace=NS_HTML)


class HtmlBase(XmlCloth):
    mime_type = 'application/xhtml+xml'

    def __init__(self, *args, **kwargs):
        super(HtmlBase, self).__init__(*args, **kwargs)

        if self._cloth is not None:
            if not self._cloth.tag.endswith('html'):
                self._cloth = E.html(self._cloth)

            if self._cloth.tag != '{%s}html' % NS_HTML:
                for elt in self._cloth.xpath("//*"):
                    elt.tag = "{%s}%s" %(NS_HTML, elt.tag)
