
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


class InvalidCredentialsError(Fault):
    """Raised when requested resource is forbidden."""

    STR = "You do not have permission to access this resource"

    def __init__(self, fault_string=STR, fault_object=None):
        super(InvalidCredentialsError, self).__init__(
            'Client.InvalidCredentialsError', fault_string, detail=fault_object)


class RequestTooLongError(Fault):
    """Raised when request is too long."""

    def __init__(self, faultstring="Request too long"):
        super(RequestTooLongError, self).__init__('Client.RequestTooLong', faultstring)


class RequestNotAllowed(Fault):
    """Raised when request is incomplete."""

    def __init__(self, faultstring=""):
        super(RequestNotAllowed, self).__init__('Client.RequestNotAllowed', faultstring)


class ArgumentError(Fault):
    """Raised when there is a general problem with input data."""

    def __init__(self, faultstring=""):
        super(ArgumentError, self).__init__('Client.ArgumentError', faultstring)


class InvalidInputError(Fault):
    """Raised when there is a general problem with input data."""

    def __init__(self, faultstring="", data=""):
        super(InvalidInputError, self).__init__('Client.InvalidInput', repr((faultstring, data)))

InvalidRequestError = InvalidInputError

class ValidationError(Fault):
    """Raised when the input stream does not adhere to type constraints."""

    def __init__(self, obj, custom_msg='The value %r could not be validated.'):
        s = repr(obj)

        if len(s) > MAX_STRING_FIELD_LENGTH:
            s = s[:MAX_STRING_FIELD_LENGTH] + "(...)"
        try:
            msg = custom_msg % s
        except TypeError:
            msg = custom_msg

        super(ValidationError, self).__init__('Client.ValidationError', msg)


class InternalError(Fault):
    """Raised to communicate server-side errors."""
    def __init__(self, error):
        super(InternalError, self).__init__('Server',
                                 "InternalError: An unknown error has occured.")


class ResourceNotFoundError(Fault):
    """Raised when requested resource is not found."""

    def __init__(self, fault_object,
                 fault_string="Requested resource %r not found"):
        super(ResourceNotFoundError, self).__init__(
            'Client.ResourceNotFound', fault_string % (fault_object,))


class RespawnError(ResourceNotFoundError):
    pass


class ResourceAlreadyExistsError(Fault):
    """Raised when requested resource already exists on server side."""

    def __init__(self, fault_object,
                 fault_string="Resource %r already exists"):
        super(ResourceAlreadyExistsError,
              self).__init__('Client.ResourceAlreadyExists', fault_string %
                             fault_object)


class Redirect(Fault):
    def __init__(self, ctx, location, orig_exc=None):
        super(Redirect, self).__init__('Client.MustBeRedirected',
                                                           faultstring=location)
        self.ctx = ctx
        self.location= location
        self.orig_exc = orig_exc

    def do_redirect(self):
        raise NotImplementedError()
