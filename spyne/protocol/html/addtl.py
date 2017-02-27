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

from lxml.builder import E
from pprint import pformat

from spyne import Boolean
from spyne.protocol.html import HtmlBase


class PrettyFormat(HtmlBase):
    def to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        parent.write(E.pre(pformat(inst)))


class BooleanListProtocol(HtmlBase):
    def __init__(self, nothing=None):
        super(BooleanListProtocol, self).__init__()

        self.nothing = nothing

    def to_parent(self, ctx, cls, inst, parent, name, nosubprot=False, **kwargs):
        if inst is None:
            return

        wrote_nothing = True
        for k, v in cls.get_flat_type_info(cls).items():
            if not issubclass(v, Boolean):
                continue

            if getattr(inst, k, False):
                parent.write(E.p(self.trc(cls, ctx.locale, k)))
                wrote_nothing = False

        if wrote_nothing and self.nothing is not None:
            parent.write(E.p(self.nothing))
