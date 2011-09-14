
#
# rpclib - Copyright (C) Rpclib contributors.
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

"""This module defines the Fault class."""

from rpclib.model import ModelBase

class Fault(ModelBase, Exception):
    """Use this class as a base for public exceptions."""

    __type_name__ = "Fault"

    def __init__(self, faultcode='Server', faultstring="", faultactor="",
                                                                   detail=None):
        self.faultcode = faultcode
        self.faultstring = faultstring or self.get_type_name()
        self.faultactor = faultactor
        self.detail = detail

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return "Fault(%s: %r)" % (self.faultcode, self.faultstring)

    @classmethod
    def to_string_iterable(cls, value):
        return [value.faultcode, '\n\n', value.faultstring]
