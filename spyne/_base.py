
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

import logging
logger = logging.getLogger('spyne')

from collections import namedtuple

# When spyne.server.twisted gets imported, this type gets a static method named
# `from_twisted_address`. Dark magic.
Address = namedtuple("Address", ["type", "host", "port"])


class _add_address_types():
    Address.TCP4 = 'TCP4'
    Address.TCP6 = 'TCP6'
    Address.UDP4 = 'UDP4'
    Address.UDP6 = 'UDP6'

    def address_str(self):
        return ":".join((self.type, self.host, str(self.port)))

    Address.__str__ = address_str

    # this gets overwritten once spyne.server.twisted is imported
    @staticmethod
    def _fta(*a, **kw):
        from spyne.server.twisted._base import _address_from_twisted_address
        return _address_from_twisted_address(*a, **kw)

    Address.from_twisted_address = _fta
