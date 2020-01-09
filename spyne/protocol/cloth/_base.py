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

from spyne import ProtocolContext, BODY_STYLE_WRAPPED, ByteArray, File, Array
from spyne.util import Break, coroutine
from spyne.protocol import ProtocolMixin

from spyne.protocol.cloth.to_parent import ToParentMixin
from spyne.protocol.cloth.to_cloth import ToClothMixin
from spyne.util.six import BytesIO
from spyne.util.color import R, B
from spyne.util.tlist import tlist


class XmlClothProtocolContext(ProtocolContext):
    def __init__(self, parent, transport, type=None):
        super(XmlClothProtocolContext, self).__init__(parent, transport, type)

        self.inst_stack = tlist([], tuple)
        self.prot_stack = tlist([], ProtocolMixin)
        self.doctype_written = False


class XmlCloth(ToParentMixin, ToClothMixin):
    mime_type = 'text/xml'
    HtmlMicroFormat = None

    def __init__(self, app=None, encoding='utf8', doctype=None,
                      mime_type=None, ignore_uncap=False, ignore_wrappers=False,
                                cloth=None, cloth_parser=None, polymorphic=True,
                         strip_comments=True, use_ns=None, skip_root_tag=False):

        super(XmlCloth, self).__init__(app=app, mime_type=mime_type,
                     ignore_uncap=ignore_uncap, ignore_wrappers=ignore_wrappers,
                                                        polymorphic=polymorphic)

        self._init_cloth(cloth, cloth_parser, strip_comments)
        self.developer_mode = False
        self.encoding = encoding
        self.default_method = 'xml'
        self.doctype = doctype
        self.use_ns = use_ns
        self.skip_root_tag = skip_root_tag

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
            ctx.out_stream = BytesIO()
            logger.debug("%r %d", ctx.out_stream, id(ctx.out_stream))

        if ctx.out_error is not None:
            # All errors at this point must be Fault subclasses.
            inst = ctx.out_error
            cls = inst.__class__
            name = cls.get_type_name()

            if self.developer_mode:
                # FIXME: the eff is this?
                ctx.out_object = (inst,)

                retval = self._incgen(ctx, cls, inst, name)
            else:
                with self.docfile(ctx.out_stream, encoding=self.encoding) as xf:
                    retval = self.to_parent(ctx, cls, inst, xf, name)

        else:
            assert message is self.RESPONSE
            result_class = ctx.descriptor.out_message

            name = result_class.get_type_name()
            if ctx.descriptor.body_style == BODY_STYLE_WRAPPED:
                if self.ignore_wrappers:
                    result_inst = ctx.out_object[0]
                    while result_class.Attributes._wrapper and \
                                              len(result_class._type_info) == 1:
                        result_class, = result_class._type_info.values()

                else:
                    result_inst = result_class()

                    for i, attr_name in enumerate(
                                        result_class._type_info.keys()):
                        setattr(result_inst, attr_name, ctx.out_object[i])

            else:
                result_inst, = ctx.out_object

            retval = self._incgen(ctx, result_class, result_inst, name)

        self.event_manager.fire_event('after_serialize', ctx)

        return retval

    def create_out_string(self, ctx, charset=None):
        """Sets an iterable of string fragments to ctx.out_string if the output
        is a StringIO object, which means we're run by a sync framework. Async
        frameworks have the out_stream write directly to the output stream so
        out_string should not be used.
        """

        if isinstance(ctx.out_stream, BytesIO):
            ctx.out_string = [ctx.out_stream.getvalue()]

    @coroutine
    def _incgen(self, ctx, cls, inst, name):
        """Entry point to the (stack of) XmlCloth-based protocols.

        Not supposed to be overridden.
        """

        if name is None:
            name = cls.get_type_name()

        try:
            with self.docfile(ctx.out_stream, encoding=self.encoding) as xf:
                ctx.outprot_ctx.doctype_written = False
                ctx.protocol.prot_stack = tlist([], ProtocolMixin)
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
        logger.debug("Starting file with %r %r", args, kwargs)
        return etree.xmlfile(*args, **kwargs)

    def _get_doctype(self, cloth):
        if self.doctype is not None:
            return self.doctype

        if cloth is not None:
            return cloth.getroottree().docinfo.doctype

        if self._root_cloth is not None:
            return self._root_cloth.getroottree().docinfo.doctype

        if self._cloth is not None:
            return self._cloth.getroottree().docinfo.doctype

    def write_doctype(self, ctx, parent, cloth=None):
        dt = self._get_doctype(cloth)
        if dt is None:
            return

        parent.write_doctype(dt)
        ctx.outprot_ctx.doctype_written = True
        logger.debug("Doctype written as: '%s'", dt)

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
            if not ctx.outprot_ctx.doctype_written:
                self.write_doctype(ctx, parent, c)

            logger.debug("to object root cloth")
            return True, self.to_root_cloth(ctx, cls, inst, c, parent, name,
                                                                       **kwargs)
        c = self.get_class_cloth(cls)
        if c is not None:
            if not ctx.outprot_ctx.doctype_written:
                self.write_doctype(ctx, parent, c)

            logger.debug("to object cloth")
            return True, self.to_parent_cloth(ctx, cls, inst, c, parent, name,
                                                                       **kwargs)
        return False, None

    @coroutine
    def subserialize(self, ctx, cls, inst, parent, name='', **kwargs):
        """Bridge between multiple XmlCloth-based protocols.

        Not supposed to be overridden.
        """

        pstack = ctx.protocol.prot_stack
        pstack.append(self)
        logger.debug("%s push prot %r. newlen: %d", R("%"), self, len(pstack))

        have_cloth = False

        cls_cloth = self.get_class_cloth(cls)
        if cls_cloth is not None:
            logger.debug("to object cloth for %s", cls.get_type_name())
            ret = self.to_parent_cloth(ctx, cls, inst, cls_cloth, parent, name)

        elif self._root_cloth is not None:
            logger.debug("to root cloth for %s", cls.get_type_name())
            ret = self.to_root_cloth(ctx, cls, inst, self._root_cloth,
                                                                   parent, name)
            have_cloth = True

        elif self._cloth is not None:
            logger.debug("to parent protocol cloth for %s", cls.get_type_name())
            ret = self.to_parent_cloth(ctx, cls, inst, self._cloth, parent,
                                                                           name)
            have_cloth = True

        else:
            logger.debug("to parent for %s", cls.get_type_name())
            ret = self.start_to_parent(ctx, cls, inst, parent, name, **kwargs)

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
                finally:
                    self._finalize_protocol(ctx, parent, have_cloth)
        else:
            self._finalize_protocol(ctx, parent, have_cloth)

        pstack.pop()
        logger.debug("%s pop prot  %r. newlen: %d", B("%"), self, len(pstack))

    def _finalize_protocol(self, ctx, parent, have_cloth):
        if have_cloth:
            self._close_cloth(ctx, parent)
            return

        if len(ctx.protocol.prot_stack) == 1 and len(ctx.protocol.eltstack) > 0:
            self._close_cloth(ctx, parent)
            return

    @staticmethod
    def _gen_tagname(ns, name):
        if ns is not None:
            name = "{%s}%s" % (ns, name)
        return name

    def _gen_attrib_dict(self, inst, fti):
        attrs = {}

        for field_name, field_type in fti.attrs.items():
            ns = field_type._ns
            if ns is None:
                ns = field_type.Attributes.sub_ns

            sub_name = field_type.Attributes.sub_name
            if sub_name is None:
                sub_name = field_name

            val = getattr(inst, field_name, None)
            sub_name = self._gen_tagname(ns, sub_name)

            if issubclass(field_type.type, (ByteArray, File)):
                valstr = self.to_unicode(field_type.type, val,
                                                       self.binary_encoding)
            else:
                valstr = self.to_unicode(field_type.type, val)

            if valstr is not None:
                attrs[sub_name] = valstr

        return attrs

    def decompose_incoming_envelope(self, ctx, message):
        raise NotImplementedError("This is an output-only protocol.")
