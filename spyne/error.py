
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

"""The ``spyne.error`` module contains various common exceptions that the user
code can throw.
"""

from spyne.model.fault import Fault
from spyne.const import MAX_STRING_FIELD_LENGTH

class ResourceNotFoundError(Fault):
    """Raised when requested resource is not found."""
    def __init__(self, faultstring="Requested resource not found"):
        Fault.__init__(self, 'Client.ResourceNotFound', faultstring)


class RequestTooLongError(Fault):
    """Raised when request is too long."""
    def __init__(self, faultstring=""):
        Fault.__init__(self, 'Client.RequestTooLong', faultstring)


class RequestNotAllowed(Fault):
    """Raised when request is incomplete."""
    def __init__(self, faultstring=""):
        Fault.__init__(self, 'Client.RequestNotAllowed', faultstring)


class ArgumentError(Fault):
    """Raised when there is a general problem with input data."""
    def __init__(self, faultstring=""):
        Fault.__init__(self, 'Client.ArgumentError', faultstring)


class ValidationError(Fault):
    """Raised when the input stream does not adhere to type constraints."""
    def __init__(self, faultstring = '', values = None):
        if values:
            if not isinstance(values, list):
                values = [repr(values)]

            if not isinstance(values, dict):
                tmp = dict(zip(range(len(values)), values))
            else:
                tmp = values
            for k, v in tmp.iteritems():
                if isinstance(v, (str, unicode)) and len(v) > MAX_STRING_FIELD_LENGTH:
                    v = v[:MAX_STRING_FIELD_LENGTH] + '(...)'
                    values[k] = v

            if isinstance(values, dict):
                faultstring %= values
            else:
                faultstring %= tuple(values)

        Fault.__init__(self, 'Client.ValidationError', faultstring)
