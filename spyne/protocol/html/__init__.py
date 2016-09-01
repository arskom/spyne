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

"""
This package contains some basic html output protocols.
"""

from spyne.protocol.html._base import HtmlBase
from spyne.protocol.html._base import HtmlCloth
from spyne.protocol.html._base import parse_html_fragment_file
from spyne.protocol.html.table import HtmlColumnTable
from spyne.protocol.html.table import HtmlRowTable
from spyne.protocol.html.microformat import HtmlMicroFormat
from spyne.protocol.html.addtl import PrettyFormat
from spyne.protocol.html.addtl import BooleanListProtocol


# FIXME: REMOVE ME
def translate(cls, locale, default):
    retval = None
    if cls.Attributes.translations is not None:
        retval = cls.Attributes.translations.get(locale, None)
    if retval is None:
        return default
    return retval
