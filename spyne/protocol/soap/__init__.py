
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

"""The ``spyne.protocol.soap`` package contains an implementation of a subset
of the Soap 1.1 standard and awaits for volunteers for implementing the
brand new Soap 1.2 standard.

Patches are welcome.
"""

from spyne.protocol.soap.soap11 import Soap11
from spyne.protocol.soap.soap11 import _from_soap
from spyne.protocol.soap.soap11 import _parse_xml_string
