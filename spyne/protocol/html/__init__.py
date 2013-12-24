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

"""The ``spyne.protocol.html`` package contains various EXPERIMENTAL protocols
for generating server-side Html. It seeks to eliminate the need for html
templates by:
    #. Implementing standard ways of serializing Python objects to Html
        documents
    #. Implementing a very basic html node manipulation api in python instead
        of having to have pseudocode intertwined within Html. (à la PHP)

As you can probably tell, not everything is figured out yet :)

Initially released in 2.8.0-rc.

This module is EXPERIMENTAL. You may not recognize the code here next time you
look at it.
"""

from spyne.protocol.html._base import HtmlBase
from spyne.protocol.html.table import HtmlTable
from spyne.protocol.html.microformat import HtmlMicroFormat
from spyne.protocol.html.template import HtmlPage
