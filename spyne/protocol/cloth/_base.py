# encoding: utf8
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

from __future__ import print_function

import logging
logger = logging.getLogger(__name__)

from inspect import isgenerator

from lxml import etree
from lxml.etree import LxmlSyntaxError
from lxml.builder import E

from spyne import ProtocolContext, BODY_STYLE_WRAPPED
from spyne.util import Break, coroutine

from spyne.protocol.cloth.to_parent import ToParentMixin
from spyne.protocol.cloth.to_cloth import ToClothMixin
from spyne.util.six import StringIO


class XmlClothProtocolContext(ProtocolContext):
    def __init__(self, parent, transport, type=None):
        super(XmlClothProtocolContext, self).__init__(parent, transport, type)

        self.inst_stack = []
        self.prot_stack = []
        self.doctype_written = False
        self.close_until = None


class XmlCloth(ToParentMixin, ToClothMixin):
    mime_type = 'text/xml'
    HtmlMicroFormat = None

    def __init__(self, app=None, mime_type=None, ignore_uncap=False,
                                              ignore_wrappers=False, cloth=None,
                                           cloth_parser=None, polymorphic=True):

        super(XmlCloth, self).__init__(app=app, mime_type=mime_type,
                     ignore_uncap=ignore_uncap, ignore_wrappers=ignore_wrappers,
                                                        polymorphic=polymorphic)

        self._init_cloth(cloth, cloth_parser)

    def get_context(self, parent, transport):
        return XmlClothProtocolContext(parent, transport)

    def serialize(self, ctx, message):
        """Uses ``ctx.out_object``, ``ctx.out_header`` or ``ctx.out_error`` to
        set ``ctx.out_body_doc``, ``ctx.out_header_doc`` and
        ``ctx.out_document`` as an ``lxml.etree._Element instance``.

        Not meant to be overridden.
        """

        assert message in (self.REQUEST, self.RESPONSE)

        self.event_manager.fire_event('before_serialize', ctx)

        if ctx.out_stream is None:
            ctx.out_stream = StringIO()
            logger.debug("%r %d", ctx.out_stream, id(ctx.out_stream))

        if ctx.out_error is not None:
            # All errors at this point must be Fault subclasses.
            inst = ctx.out_error
            cls = inst.__class__
            name = cls.get_type_name()

            ctx.out_document = E.div()
            with self.docfile(ctx.out_stream) as xf:
                # as XmlDocument is not push-ready yet, this is what we do.
                # this is an ugly hack, bear with me.
                retval = XmlCloth.HtmlMicroFormat() \
                                            .to_parent(ctx, cls, inst, xf, name)

        else:
            assert message is self.RESPONSE
            result_message_class = ctx.descriptor.out_message

            name = result_message_class.get_type_name()
            if ctx.descriptor.body_style == BODY_STYLE_WRAPPED:
                if self.ignore_wrappers:
                    result_message = ctx.out_object[0]
                    while result_message_class.Attributes._wrapper and \
                                      len(result_message_class._type_info) == 1:
                        result_message_class, = \
                                        result_message_class._type_info.values()

                else:
                    result_message = result_message_class()

                    for i, attr_name in enumerate(
                                        result_message_class._type_info.keys()):
                        setattr(result_message, attr_name, ctx.out_object[i])

            else:
                result_message, = ctx.out_object

            retval = self.incgen(ctx, result_message_class, result_message, name)

        self.event_manager.fire_event('after_serialize', ctx)

        return retval

    def create_out_string(self, ctx, charset=None):
        """Sets an iterable of string fragments to ctx.out_string if the output
        is a StringIO object, which means we're run by a sync framework. Async
        frameworks have the out_stream write directly to the output stream so
        out_string should not be used.
        """

        if isinstance(ctx.out_stream, StringIO):
            ctx.out_string = [ctx.out_stream.getvalue()]

    @coroutine
    def incgen(self, ctx, cls, inst, name):
        if name is None:
            name = cls.get_type_name()

        try:
            with self.docfile(ctx.out_stream) as xf:
                ctx.protocol.doctype_written = False
                ctx.protocol.prot_stack = []
                ret = self.subserialize(ctx, cls, inst, xf, name)
                if isgenerator(ret):  # Poor man's yield from
                    try:
                        while True:
                            sv2 = (yield)
                            ret.send(sv2)

                    except Break as b:
                        try:
                            ret.throw(b)
                        except StopIteration:
                            pass

        except LxmlSyntaxError as e:
            if e.msg == 'no content written':
                pass
            else:
                raise

    def docfile(self, *args, **kwargs):
        return etree.xmlfile(*args, **kwargs)

    def write_doctype(self, ctx, parent, cloth=None):
        pass  # FIXME: write it

    @staticmethod
    def get_class_cloth(cls):
        return cls.Attributes._xml_cloth

    @staticmethod
    def get_class_root_cloth(cls):
        return cls.Attributes._xml_root_cloth

    def check_class_cloths(self, ctx, cls, inst, parent, name, **kwargs):
        c = self.get_class_root_cloth(cls)
        eltstack = getattr(ctx.protocol, 'eltstack', [])
        if c is not None and len(eltstack) == 0 and not (eltstack[-1] is c):
            if not ctx.protocol.doctype_written:
                self.write_doctype(ctx, parent, c)

            logger.debug("to object root cloth")
            return True, self.to_root_cloth(ctx, cls, inst, c, parent, name,
                                                                       **kwargs)
        c = self.get_class_cloth(cls)
        if c is not None:
            if not ctx.protocol.doctype_written:
                self.write_doctype(ctx, parent, c)

            logger.debug("to object cloth")
            return True, self.to_parent_cloth(ctx, cls, inst, c, parent, name,
                                                                       **kwargs)
        return False, None

    def subserialize(self, ctx, cls, inst, parent, name='', **kwargs):
        pstack = ctx.protocol.prot_stack
        pstack.append(self)
        logger.debug("push prot %r. newlen: %d", self, len(pstack))

        if self._root_cloth is not None:
            logger.debug("to root cloth")
            retval = self.to_root_cloth(ctx, cls, inst, self._root_cloth,
                                                                   parent, name)

        elif self._cloth is not None:
            logger.debug("to parent cloth")
            retval = self.to_parent_cloth(ctx, cls, inst, self._cloth, parent,
                                                                           name)
        else:
            logger.debug("to parent")
            retval = self.start_to_parent(ctx, cls, inst, parent, name, **kwargs)

        # FIXME: if retval is a coroutine handle, this will be inconsistent
        pstack.pop()
        logger.debug("pop prot  %r. newlen: %d", self, len(pstack))

        return retval

    def decompose_incoming_envelope(self, ctx, message):
        raise NotImplementedError("This is an output-only protocol.")
