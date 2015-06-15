
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
logger = logging.getLogger(__name__)

import re
RE_HTTP_ARRAY_INDEX = re.compile("\\[([0-9]+)\\]")

from spyne.error import ValidationError

from spyne.model import Fault, Array, AnyXml, AnyHtml, Uuid, DateTime, Date, \
    Time, Duration

from spyne.protocol import ProtocolBase


class DictDocument(ProtocolBase):
    """An abstract protocol that can use hierarchical or flat dicts as input
    and output documents.

    Implement ``serialize()``, ``deserialize()``, ``create_in_document()`` and
    ``create_out_string()`` to use this.
    """

    # flags to be used in tests
    _decimal_as_string = False
    _huge_numbers_as_string = False

    def __init__(self, app=None, validator=None, mime_type=None,
            ignore_uncap=False, ignore_wrappers=True, complex_as=dict,
                                              ordered=False, polymorphic=False):
        super(DictDocument, self).__init__(app, validator, mime_type,
                                                  ignore_uncap, ignore_wrappers)

        self.polymorphic = polymorphic
        self.complex_as = complex_as
        self.ordered = ordered
        if ordered:
            raise NotImplementedError('ordered=True')

        self.stringified_types = (DateTime, Date, Time, Uuid, Duration,
                                                                AnyXml, AnyHtml)

    def set_validator(self, validator):
        """Sets the validator for the protocol.

        :param validator: one of ('soft', None)
        """

        if validator == 'soft' or validator is self.SOFT_VALIDATION:
            self.validator = self.SOFT_VALIDATION
        elif validator is None:
            self.validator = None
        else:
            raise ValueError(validator)

    def decompose_incoming_envelope(self, ctx, message):
        """Sets ``ctx.in_body_doc``, ``ctx.in_header_doc`` and
        ``ctx.method_request_string`` using ``ctx.in_document``.
        """

        assert message in (ProtocolBase.REQUEST, ProtocolBase.RESPONSE)

        # set ctx.in_header
        ctx.transport.in_header_doc = None # use an rpc protocol if you want headers.

        doc = ctx.in_document

        ctx.in_header_doc = None
        ctx.in_body_doc = doc

        if message is ProtocolBase.REQUEST:
            logger.debug('\theader : %r' % (ctx.in_header_doc))
            logger.debug('\tbody   : %r' % (ctx.in_body_doc))

            if not isinstance(doc, dict) or len(doc) != 1:
                raise ValidationError("Need a dictionary with exactly one key "
                                      "as method name.")
            if len(doc) == 0:
                raise Fault("Client", "Empty request")

            mrs, = doc.keys()
            ctx.method_request_string = '{%s}%s' % (self.app.interface.get_tns(),
                                                                            mrs)

    def deserialize(self, ctx, message):
        raise NotImplementedError()

    def serialize(self, ctx, message):
        raise NotImplementedError()

    def create_in_document(self, ctx, in_string_encoding=None):
        raise NotImplementedError()

    def create_out_string(self, ctx, out_string_encoding='utf8'):
        raise NotImplementedError()

    def _check_freq_dict(self, cls, d, fti=None):
        if fti is None:
            fti = cls.get_flat_type_info(cls)

        for k, v in fti.items():
            val = d[k]

            attrs = self.get_cls_attrs(v)
            min_o, max_o = attrs.min_occurs, attrs.max_occurs
            if issubclass(v, Array) and v.Attributes.max_occurs == 1:
                v, = v._type_info.values()
                attrs = self.get_cls_attrs(v)
                min_o, max_o = attrs.min_occurs, attrs.max_occurs

            if val < min_o:
                raise ValidationError("%r.%s" % (cls, k),
                             '%%s member must occur at least %d times.' % min_o)
            elif val > max_o:
                raise ValidationError("%r.%s" % (cls, k),
                             '%%s member must occur at most %d times.' % max_o)
