
from rpclib.model.fault import Fault

class ResourceNotFoundError(Fault):
    """Raised when the requested resource was not found."""
    def __init__(self, faultstring="Requested resource not found"):
        Fault.__init__(self, 'Client.ResourceNotFound', faultstring)

class RequestTooLongError(Fault):
    """Raised when the request is too long."""
    def __init__(self, faultstring):
        Fault.__init__(self, 'Client.RequestTooLong', faultstring)

class ArgumentError(Fault):
    """Raised when there is a general problem with input data."""
    def __init__(self, faultstring):
        Fault.__init__(self, 'Client.ArgumentError', faultstring)

class ValidationError(Fault):
    """Raised when the input stream did not adhere to type constraints."""
    def __init__(self, faultstring):
        Fault.__init__(self, 'Client.ValidationError',
                        'The string %r could not be validated.' % faultstring)
