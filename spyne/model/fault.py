
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

from warnings import warn
from collections import defaultdict

import spyne.const

from spyne.model.primitive import Any

from spyne.util.six import add_metaclass

from spyne.model.complex import ComplexModelMeta
from spyne.model.complex import ComplexModelBase


class FaultMeta(ComplexModelMeta):
    def __init__(self, cls_name, cls_bases, cls_dict):
        super(FaultMeta, self).__init__(cls_name, cls_bases, cls_dict)

        code = cls_dict.get('CODE', None)

        if code is not None:
            target = Fault.REGISTERED[code]
            target.add(self)
            if spyne.const.WARN_ON_DUPLICATE_FAULTCODE and len(target) > 1:
                warn("Duplicate faultcode {} detected for classes {}"
                                                          .format(code, target))


@add_metaclass(FaultMeta)
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
    :param lang: Language code corresponding to the language of faultstring.
    """

    REGISTERED = defaultdict(set)
    """Class-level variable that holds a multimap of all fault codes and the
    associated classes."""

    __type_name__ = "Fault"

    CODE = None

    def __init__(self, faultcode='Server', faultstring="", faultactor="",
                                      detail=None, lang=spyne.DEFAULT_LANGUAGE):
        self.faultcode = faultcode
        self.faultstring = faultstring or self.get_type_name()
        self.faultactor = faultactor
        self.detail = detail
        self.lang = lang

    def __len__(self):
        return 1

    def __str__(self):
        return repr(self)

    def __repr__(self):
        if self.detail is None:
            return "%s(%s: %r)" % (self.__class__.__name__,
                                               self.faultcode, self.faultstring)

        return "%s(%s: %r detail: %r)" % (self.__class__.__name__,
                                  self.faultcode, self.faultstring, self.detail)

    @staticmethod
    def to_dict(cls, value, prot):
        if not issubclass(cls, Fault):
            return {
                "faultcode": "Server.Unknown",
                "faultstring": cls.__name__,
                "detail": str(value),
            }

        retval =  {
            "faultcode": value.faultcode,
            "faultstring": value.faultstring,
        }

        if value.faultactor is not None:
            if len(value.faultactor) > 0 or (not prot.ignore_empty_faultactor):
                retval["faultactor"] = value.faultactor

        if value.detail is not None:
            retval["detail"] = value.detail_to_doc(prot)

        return retval

    #
    # From http://schemas.xmlsoap.org/soap/envelope/
    #
    # <xs:element name="faultcode" type="xs:QName"/>
    # <xs:element name="faultstring" type="xs:string"/>
    # <xs:element name="faultactor" type="xs:anyURI" minOccurs="0"/>
    # <xs:element name="detail" type="tns:detail" minOccurs="0"/>
    #
    @staticmethod
    def to_list(cls, value, prot=None):
        if not issubclass(cls, Fault):
            return [
                "Server.Unknown",  # faultcode
                cls.__name__,      # faultstring
                "",                # faultactor
                str(value),        # detail
            ]

        retval = [
            value.faultcode,
            value.faultstring,
        ]

        if value.faultactor is not None:
            retval.append(value.faultactor)
        else:
            retval.append("")

        if value.detail is not None:
            retval.append(value.detail_to_doc(prot))
        else:
            retval.append("")

        return retval

    @classmethod
    def to_bytes_iterable(cls, value):
        return [
            value.faultcode.encode('utf8'),
            b'\n\n',
            value.faultstring.encode('utf8'),
        ]

    def detail_to_doc(self, prot):
        return self.detail

    def detail_from_doc(self, prot, doc):
        self.detail = doc
