
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

"""The ``spyne.protocol`` package contains the
:class:`spyne.protocol.ProtocolBase`` abstract base class. Every protocol
implementation is a subclass of ``ProtocolBase``.
"""

from spyne.protocol._base import ProtocolMixin
from spyne.protocol._inbase import InProtocolBase
from spyne.protocol._outbase import OutProtocolBase


class ProtocolBase(InProtocolBase, OutProtocolBase):
    def __init__(self, app=None, validator=None, mime_type=None,
           ignore_uncap=False, ignore_wrappers=False, binary_encoding=None,
                                                        string_encoding='utf8'):

        InProtocolBase.__init__(self, app=app, validator=validator,
                          mime_type=mime_type, ignore_wrappers=ignore_wrappers,
                                                binary_encoding=binary_encoding)

        OutProtocolBase.__init__(self, app=app, mime_type=mime_type,
                     ignore_wrappers=ignore_wrappers, ignore_uncap=ignore_uncap,
                                                binary_encoding=binary_encoding)

        self.default_string_encoding = string_encoding
        self.ignore_empty_faultactor = True
