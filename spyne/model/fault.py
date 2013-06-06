
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


from spyne.const import TYPE_SUFFIX
from spyne.model.complex import ComplexModelMeta
from spyne.model.complex import ComplexModelBase


class Fault(ComplexModelBase, Exception):
    """Use this class as a base for all public exceptions.
    The Fault object adheres to the
    `SOAP 1.1 Fault definition <http://www.w3.org/TR/2000/NOTE-SOAP-20000508/#_Toc478383507>`_,

    which has three main attributes:

    :param faultcode: It's a dot-delimited string whose first fragment is
        either 'Client' or 'Server'. Just like HTTP 4xx and 5xx codes,
        'Client' indicates that something was wrong with the input, and 'Server'
        indicates something went wrong during the processing of an otherwise
        legitimate request.

        Protocol implementors should heed the values in ``faultcode`` to set
        proper return codes in the protocol level when necessary. E.g. HttpRpc
        protocol will return a HTTP 404 error when a
        :class:`spyne.error.ResourceNotFound` is raised, and a general HTTP 400
        when the ``faultcode`` starts with ``'Client.'`` or is ``'Client'``.

        Soap would return Http 500 for any kind of exception, and denote the
        nature of the exception in the Soap response body. (because that's what
        the standard says... Yes, soap is famous for a reason :))
    :param faultstring: It's the human-readable explanation of the exception.
    :param detail: Additional information dict.
    """

    __metaclass__ = ComplexModelMeta
    __type_name__ = "Fault"

    def __init__(self, faultcode='Server', faultstring="", faultactor="",
                                                                   detail=None):
        self.faultcode = faultcode
        self.faultstring = faultstring or self.get_type_name()
        self.faultactor = faultactor
        self.detail = detail

    def __len__(self):
        return 1

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return "Fault(%s: %r)" % (self.faultcode, self.faultstring)

    @staticmethod
    def to_dict(cls, value):
        if issubclass(cls, Fault):
            return {
                "faultcode": value.faultcode,
                "faultstring": value.faultstring,
                "detail": value.detail,
            }

        else:
            return {
                "faultcode": str(cls),
                "faultstring": cls.__class__.__name__,
                "detail": str(value),
            }

    @classmethod
    def to_string_iterable(cls, value):
        return [value.faultcode, '\n\n', value.faultstring]

    @staticmethod
    def resolve_namespace(cls, default_ns):
        if getattr(cls, '__extends__', None) != None:
            cls.__extends__.resolve_namespace(cls.__extends__, default_ns)

        ComplexModelBase.resolve_namespace(cls, default_ns)

        for k, v in cls._type_info.items():
            if v.__type_name__ is ComplexModelBase.Empty:
                v.__namespace__ = cls.get_namespace()
                v.__type_name__ = "%s_%s%s" % (cls.get_type_name(), k, TYPE_SUFFIX)

            if not issubclass(v, cls):
                v.resolve_namespace(v, default_ns)

        if cls._force_own_namespace is not None:
            for c in cls._force_own_namespace:
                c.__namespace__ = cls.get_namespace()
                Fault.resolve_namespace(c, cls.get_namespace())
